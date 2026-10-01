ตัวนี้คือ EF Core ฟ้องว่ามีสองงานใช้ DbContext instance เดียวกันพร้อมกันครับ

DbContext ออกแบบมาให้ทำงานทีละ operation และไม่ thread-safe พอมี query หรือ SaveChanges ตัวที่สองเข้ามาตอนตัวแรกยังไม่เสร็จ EF จะ throw ตัวนี้ออกมาทันที ไม่ใช่ปล่อยให้ข้อมูลพัง

## สาเหตุที่เจอบ่อย เรียงตามความถี่

**1. ลืม `await`**

```csharp
_db.SaveChangesAsync();                       // ไม่มี await
var list = await _db.Employees.ToListAsync(); // ตัวนี้เริ่มตอนตัวบนยังไม่จบ
```

เจอบ่อยที่สุด ดูง่าย ๆ คือหา call ที่ลงท้ายด้วย `Async` แล้วไม่มี `await` นำหน้า เปิด warning CS4014 ให้เป็น error ไปเลยจะกันได้ตั้งแต่ compile

**2. ยิง query ขนานด้วย `Task.WhenAll`**

```csharp
var tasks = ids.Select(id => _db.Employees.FirstOrDefaultAsync(e => e.Id == id));
await Task.WhenAll(tasks);   // พัง: ทุก task ใช้ _db ตัวเดียวกัน
```

`Parallel.ForEach` หรือ `Parallel.ForEachAsync` ที่เรียก DbContext ข้างในก็เข้าข่ายเดียวกัน

**3. DI lifetime ผิด**

`AddDbContext` ปกติเป็น Scoped อยู่แล้ว หนึ่ง request หนึ่ง context จึงไม่ค่อยพัง แต่จะพังเมื่อ
- register DbContext เป็น Singleton เอง
- service ที่ inject DbContext เข้าไปเป็น Singleton (captive dependency) ทำให้ context ตัวเดียวอยู่ยาวตลอดอายุแอป แล้วหลาย request มาใช้พร้อมกัน

ถ้าเป็นเคสนี้ error จะโผล่เฉพาะตอนมี traffic พร้อมกัน ทดสอบคนเดียวไม่เจอ

**4. fire and forget / background task**

```csharp
_ = ProcessInBackgroundAsync();  // ใช้ _db ตัวเดิมของ request
return Ok();
```

request จบไปแล้วแต่งานเบื้องหลังยังถือ context เดิมอยู่ บางทีได้ `ObjectDisposedException` แทน หรือชนกับ request ถัดไป ใน `IHostedService` ก็ต้องสร้าง scope ใหม่ทุกครั้งที่จะใช้ context

**5. อ่าน stream ค้างไว้แล้วยิง query ใหม่**

```csharp
await foreach (var emp in _db.Employees.AsAsyncEnumerable())
{
    var dept = await _db.Departments.FindAsync(emp.DeptId);  // reader ตัวแรกยังเปิดอยู่
}
```

## ทางแก้

เลือกตามเคส

- **ลืม await**: ใส่ `await` ให้ครบ
- **ต้องการขนานจริง ๆ**: ใช้ `IDbContextFactory<T>` แล้วสร้าง context ใหม่ต่อหนึ่ง task

```csharp
builder.Services.AddDbContextFactory<AppDbContext>(opt => ...);

var tasks = ids.Select(async id =>
{
    await using var db = await _factory.CreateDbContextAsync();
    return await db.Employees.FirstOrDefaultAsync(e => e.Id == id);
});
var results = await Task.WhenAll(tasks);
```

- **ไม่จำเป็นต้องขนาน**: รวมเป็น query เดียวจะเร็วกว่าด้วย เช่น `Where(e => ids.Contains(e.Id)).ToListAsync()`
- **background task**: inject `IServiceScopeFactory` แล้ว `CreateScope()` ข้างใน resolve context ออกมาใหม่
- **stream ค้าง**: `ToListAsync()` ให้จบก่อน หรือ `Include` department มาตั้งแต่ query แรก

## วิธีหาจุดที่พัง

ดู stack trace ตัวบนสุดที่เป็นโค้ดเราเอง จะได้ method ที่ยิง operation ตัวที่สอง จากนั้นไล่หา `await` ที่หาย หรือ `WhenAll`/`Parallel` ใน call path นั้น ถ้าหาไม่เจอในโค้ดตรง ๆ ให้สงสัย lifetime กับ background task ต่อ

ถ้าเอา stack trace เต็ม ๆ กับโค้ด method ที่พังมาให้ดู เดี๋ยวผมชี้บรรทัดต้นเหตุให้ครับ
