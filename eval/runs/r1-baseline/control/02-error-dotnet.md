## สาเหตุหลัก

`DbContext` **ไม่ thread-safe** และรองรับได้แค่ **1 operation ต่อครั้ง** เท่านั้น ข้างในมันมี change tracker กับ state machine ของ connection ตัวเดียว EF Core เลยมี `ConcurrencyDetector` คอยเช็ค ถ้าเจอว่า operation ที่ 2 เริ่มทำงานตอนที่ตัวแรกยังไม่เสร็จ ก็จะโยน `InvalidOperationException` ตัวนี้ออกมาทันที → ASP.NET Core จับไม่ได้ → 500

คำถามจริง ๆ คือ "ทำไมถึงมี 2 operation ทับกัน" ซึ่งมักเกิดจาก 4 กลุ่มนี้:

### 1. ลืม `await` (เจอบ่อยที่สุด)

```csharp
// ผิด — ไม่ await ตัวแรกก็วิ่งไปตัวถัดไปแล้ว
_db.SaveChangesAsync();                 // fire-and-forget
var user = await _db.Users.FindAsync(id);
```

สังเกต warning **CS4014** ของ compiler ได้เลย ถ้าโปรเจกต์ปิด warning ไว้ก็จะเงียบสนิท อีกเคสคือ `async void` ใน event handler / middleware ที่ไม่มีใครรอ

### 2. ยิง query พร้อมกันบน context เดียว

```csharp
// ผิด — ทั้ง 3 ใช้ _db ตัวเดียวกัน
var (a, b, c) = await Task.WhenAll(
    _db.Orders.ToListAsync(),
    _db.Users.ToListAsync(),
    _db.Products.ToListAsync());

// ผิดเช่นกัน
await Parallel.ForEachAsync(ids, async (id, ct) =>
    await _db.Items.FindAsync(id));
```

### 3. DI lifetime ผิด / captive dependency

- ลงทะเบียน `DbContext` เป็น **Singleton**
- หรือ inject `DbContext` (scoped) เข้าไปใน service ที่เป็น **Singleton** → context ตัวเดียวถูกใช้ร่วมกันทุก request
- `IHostedService` / `BackgroundService` ที่ resolve DbContext จาก root provider แทนที่จะสร้าง scope เอง

กลุ่มนี้อาการเด่นคือ **error เป็นช่วง ๆ ตอนมี traffic เยอะ** ไม่ใช่พังทุกครั้ง

### 4. Query ซ้อนระหว่างที่ยัง stream ผลลัพธ์ไม่จบ

```csharp
// ผิด — foreach ยังอ่าน reader อยู่ แล้วไปยิง query ใหม่
foreach (var order in _db.Orders.Where(o => o.Active))
{
    order.Customer = await _db.Customers.FindAsync(order.CustomerId);
}
```

รวมถึง lazy loading ที่ trigger ตอน serialize response ด้วย

## วิธีไล่หาจุดเกิดเหตุ

1. ดู **stack trace เต็ม ๆ** บรรทัดแรก ๆ จะชี้ method ที่เป็นคนเรียก operation ที่ 2
2. grep หา `Async(` ที่ไม่มี `await` นำหน้า, `Task.WhenAll`, `Parallel.`, `.Result`, `.Wait()`
3. เช็ค `Program.cs` / `Startup.cs` ว่า `AddDbContext` ใช้ lifetime อะไร และมี Singleton ตัวไหน inject repository/DbContext เข้าไปไหม

## วิธีแก้

| เคส | วิธีแก้ |
|---|---|
| ลืม await | ใส่ `await` ให้ครบ ทำแบบ sequential |
| ต้องการ parallel จริง ๆ | ใช้ `AddDbContextFactory<T>()` แล้ว `await using var db = await _factory.CreateDbContextAsync();` แยก context ต่อ task |
| Background job | `using var scope = _scopeFactory.CreateScope();` แล้วค่อย resolve DbContext ข้างใน |
| Singleton ถือ DbContext | เปลี่ยนเป็น Scoped หรือ inject `IServiceScopeFactory` / `IDbContextFactory` แทน |
| Query ซ้อนตอน loop | `ToListAsync()` ให้จบก่อน แล้วค่อย loop หรือใช้ `.Include()` ดึงมาทีเดียว |

ถ้าส่ง stack trace เต็ม ๆ กับโค้ดของ endpoint ที่พัง (รวมถึงส่วนที่ register DI) มาให้ ผมช่วยชี้จุดที่เป็นต้นเหตุจริง ๆ ได้แม่นกว่านี้ครับ
