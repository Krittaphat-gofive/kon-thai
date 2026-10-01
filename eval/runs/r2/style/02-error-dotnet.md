เกิดจากการเอา DbContext ตัวเดียวไปยิง query พร้อมกันสองงานครับ

ตัว DbContext ออกแบบมาให้ทำงานทีละอย่าง ไม่ได้ thread-safe พอมี operation ที่สองเริ่มตอนที่ตัวแรกยังไม่เสร็จ EF Core ก็โยน exception ตัวนี้ออกมาเลย แล้ว API ก็ตอบ 500

## เคสที่เจอบ่อย

**1. ลืม await**

```csharp
_context.Orders.ToListAsync();                      // ไม่มี await
var users = await _context.Users.ToListAsync();     // ชนกับตัวบน
```

**2. `Task.WhenAll` บน context เดียว**

```csharp
var t1 = _context.Orders.ToListAsync();
var t2 = _context.Users.ToListAsync();
await Task.WhenAll(t1, t2);
```

อ่านแล้วเหมือนจะเร็วขึ้น แต่จริง ๆ พังเพราะสอง task แชร์ context ตัวเดียวกัน

**3. `Parallel.ForEach` หรือ `Task.Run` ที่ข้างในเรียก repository ตัวเดิม**

**4. DI lifetime ผิด**

ลงทะเบียน DbContext เป็น Singleton หรือ inject เข้าไปใน singleton service เช่น `BackgroundService` พอมีหลาย request เข้ามาพร้อมกัน ก็ใช้ instance เดียวกันหมด อาการของข้อนี้คือบางทีพัง บางทีไม่พัง ขึ้นกับจังหวะ traffic

**5. วน loop บน `IQueryable` ที่ยังไม่ materialize**

```csharp
foreach (var order in _context.Orders.Where(x => x.IsActive))   // ยัง stream อยู่
{
    var user = await _context.Users.FindAsync(order.UserId);    // ยิงซ้อนเข้าไป
}
```

## ไล่หาจุดที่พังยังไง

ดู stack trace ว่าหลุดมาจาก method ไหน แล้วไล่ขึ้นไปหา `Task.WhenAll`, `Parallel.`, `Task.Run` และ async call ที่ไม่มี `await` นำหน้า

ถ้าอยากกวาดทีเดียว ให้ปรับ warning CS4014 (call is not awaited) เป็น error ใน csproj จะเจอจุดที่ลืม await ครบทั้ง solution

## วิธีแก้

- ใส่ `await` ให้ครบทุก async call
- ถ้าต้องการยิงขนานจริง ๆ ให้แต่ละ task มี context ของตัวเอง ใช้ `IDbContextFactory`

```csharp
builder.Services.AddDbContextFactory<AppDbContext>(opt => ...);

await using var ctx = await _factory.CreateDbContextAsync();
```

- ใน background service ให้สร้าง scope เองทุกรอบ อย่าเก็บ DbContext ไว้เป็น field

```csharp
using var scope = _scopeFactory.CreateScope();
var ctx = scope.ServiceProvider.GetRequiredService<AppDbContext>();
```

- ปิด query ด้วย `ToListAsync()` ก่อน แล้วค่อยวน loop

อีกเรื่องที่ควรรู้คือปัญหานี้ reproduce ยากบนเครื่องตัวเอง เพราะยิงทีละ request พอขึ้น production ที่ request ชนกันถึงจะโผล่ ถ้าเจอเฉพาะบน production ให้สงสัยข้อ 4 ก่อนเลย

ถ้าแปะ stack trace กับโค้ดของ method ที่พังมา เดี๋ยวชี้บรรทัดให้ครับ
