## สาเหตุของ error นี้

`DbContext` ของ EF Core **ไม่ thread-safe และรองรับได้แค่ 1 operation ต่อครั้ง** (มี internal lock ตัวหนึ่งคอยกัน) ตัว instance หนึ่งจะทำ query/SaveChanges ได้ทีละอันเท่านั้น ถ้ามี operation ที่ 2 เข้ามาตอนที่อันแรกยังไม่จบ → โยน `InvalidOperationException` ตัวนี้ทันที แล้ว API เลยกลายเป็น 500

ประเด็นคือ "operation แรกยังไม่จบ" ไม่ได้แปลว่าต้องมีหลาย thread จริง ๆ เสมอไป — แค่ `Task` ที่ยัง pending อยู่ก็นับแล้ว

## สาเหตุที่พบบ่อย เรียงจากเจอมากสุด

**1. ลืม `await`** (เจอบ่อยที่สุด)

```csharp
// ผิด - method ส่ง Task กลับไปโดยยังทำงานไม่เสร็จ
_db.SaveChangesAsync();              // ลืม await
var user = GetUserAsync(id);         // ลืม await แล้วเอาไปใช้ต่อ

// ผิด - fire and forget
_ = Task.Run(() => _logService.WriteAsync(...));  // ใช้ DbContext ตัวเดียวกับ request
```
ลองไล่ดู warning **CS4014** ใน build output ก่อนเลย ปกติมันฟ้องไว้แล้ว

**2. ยิง query พร้อมกันด้วย `Task.WhenAll`**

```csharp
// ผิด - ทุก task ใช้ _db ตัวเดียวกัน
var results = await Task.WhenAll(
    _db.Orders.CountAsync(),
    _db.Customers.CountAsync(),
    _db.Products.CountAsync());

// ผิดแบบเดียวกัน
var tasks = ids.Select(id => _db.Items.FirstOrDefaultAsync(x => x.Id == id));
await Task.WhenAll(tasks);
```

**3. `Parallel.ForEach` / `Task.Run` หลายตัว ที่แชร์ DbContext เดียวกัน**

**4. DbContext ถูกลงทะเบียนเป็น Singleton หรือโดน singleton ถือไว้ (captive dependency)**

```csharp
// ผิด
services.AddDbContext<AppDbContext>(opt => ..., ServiceLifetime.Singleton);
```
หรือ service ที่เป็น Singleton / `BackgroundService` ไป inject `AppDbContext` ตรง ๆ แล้วใช้ร่วมกันทุก request → 2 request พร้อมกันเมื่อไหร่ก็พัง (อาการคลาสสิกคือ "เทสคนเดียวไม่เป็น พอขึ้น prod คนใช้เยอะแล้วเป็น")

**5. ยิง query ซ้อนตอนกำลัง stream ผลลัพธ์อยู่**

```csharp
// ผิด - query นอกยังไม่ปิด reader แล้วยิงอันในเข้าไป
foreach (var order in _db.Orders.Where(x => x.IsActive))   // ยังไม่ได้ ToList
{
    order.Customer = await _db.Customers.FindAsync(order.CustomerId);
}
```
รวมถึง **lazy loading** (`UseLazyLoadingProxies`) ที่เผลอ trigger navigation property ระหว่าง loop ลักษณะนี้

**6. Blazor Server / SignalR** — scope มีอายุยาวเท่า circuit แล้ว event หลายตัวยิงพร้อมกัน

## วิธีแก้

| กรณี | วิธีแก้ |
|---|---|
| ลืม await | ใส่ `await` ให้ครบ, เปิด warning CS4014 เป็น error |
| ต้องยิงขนาน | ใช้ `IDbContextFactory<T>` สร้าง context แยกต่อ task |
| Background job | `using var scope = _scopeFactory.CreateScope();` แล้ว resolve DbContext ในนั้น |
| Singleton | เปลี่ยนเป็น Scoped (default ของ `AddDbContext` อยู่แล้ว) |
| query ซ้อน loop | `ToListAsync()` ให้จบก่อนเข้า loop หรือใช้ `Include()` |

ตัวอย่างแบบ factory:

```csharp
// Program.cs
builder.Services.AddDbContextFactory<AppDbContext>(opt =>
    opt.UseSqlServer(conn));

// ใช้งาน
var tasks = ids.Select(async id =>
{
    await using var db = await _factory.CreateDbContextAsync();
    return await db.Items.FirstOrDefaultAsync(x => x.Id == id);
});
var items = await Task.WhenAll(tasks);
```

ถ้ายังแยกขนานไม่ได้จริง ๆ ก็เปลี่ยนเป็น sequential ไปก่อน แล้วค่อย optimize ทีหลัง — ปลอดภัยกว่า

## วิธีหาจุดเกิดเหตุ

ดู **stack trace เต็ม ๆ** จะเห็น frame ของ method ตัวเองที่เรียก query — ไล่ย้อนจากตรงนั้นว่าใครเรียกซ้อน ถ้าแปะ stack trace กับโค้ด method นั้นมา ช่วยชี้จุดให้ได้ตรงกว่านี้ครับ

อีกจุดที่ควรเช็ก: อาการ "เป็นบ้างไม่เป็นบ้าง" + เกิดตอนคนใช้เยอะ มักชี้ไปที่ข้อ 4 (lifetime ผิด) มากกว่าข้อ 1
