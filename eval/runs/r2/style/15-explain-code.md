โค้ดนี้คือ GET endpoint ที่ดึงข้อมูลพนักงานตาม id โดยอ่านผ่าน cache ก่อนครับ ถ้าไม่มีใน cache ค่อยไป database แล้วเก็บผลไว้ 5 นาที หาไม่เจอก็คืน 404

ไล่ทีละส่วน

- `_cache.GetOrCreateAsync($"emp:{id}", ...)` หาใน memory cache ด้วย key แบบ `emp:5` ถ้ามีอยู่แล้วคืนค่าเลย ไม่แตะ database
- ถ้าไม่มี ก็รัน factory ข้างใน ตั้งอายุ entry 5 นาทีนับจากตอนสร้าง แล้วดึงจาก `_repo.FindAsync(id)` ค่าที่ได้จะลง cache ให้อัตโนมัติ
- `is { } emp` เป็น pattern ที่แมตช์ค่าที่ไม่ใช่ null พูดง่าย ๆ คือเช็ก null แล้วผูกค่าเข้าตัวแปร `emp` ในบรรทัดเดียว
- เจอ ก็ `Ok(emp)` ไม่เจอ ก็ `NotFound()`

## จุดที่ต้องระวัง

**1. null ก็เข้า cache ด้วย** `GetOrCreateAsync` เซ็ต `entry.Value` เสมอ ไม่ว่า factory จะคืนอะไรกลับมา ดังนั้นถ้ายิง id ที่ไม่มีจริง จะได้ entry ที่เก็บ null ค้างไว้ 5 นาที ถ้าระหว่างนั้นมีคนสร้างพนักงาน id นั้นขึ้นมา ก็ยังได้ 404 จนครบเวลา บางทีมตั้งใจทำแบบนี้เพื่อกัน DB โดนยิงรัว ๆ ด้วย id มั่ว แต่ถ้าตั้งใจ ควรแยกอายุให้สั้นกว่า เช่น 30 วินาที

**2. ไม่มีกัน cache stampede** ถ้ามี 50 request เข้ามาพร้อมกันตอน cache miss ทุกตัววิ่งไป DB หมด เพราะ `GetOrCreateAsync` ไม่ได้ล็อกอะไรไว้ ถ้า endpoint นี้โดนหนัก ให้ดู `HybridCache` ใน .NET 9 ที่กันให้แล้ว หรือทำ `SemaphoreSlim` แยกราย key เอง

**3. `IMemoryCache` อยู่ใน process เดียว** deploy หลาย instance เมื่อไหร่ แต่ละเครื่องจะมี cache ของตัวเอง ข้อมูลไม่ตรงกันได้นานถึง 5 นาที

**4. ไม่มีการล้าง cache ตอนแก้ข้อมูล** ถ้ามี endpoint update พนักงาน ต้องเรียก `_cache.Remove($"emp:{id}")` ด้วย ไม่งั้นแก้เสร็จแล้วยังเห็นของเก่า

**5. object ที่คืนไปเป็นตัวเดียวกับที่อยู่ใน cache** ทุก request ได้ reference เดียวกัน ถ้ามีโค้ดไหนไปแก้ field ของ entity ตัวนี้ ก็เท่ากับแก้ค่าใน cache ให้คนอื่นไปด้วย

## เขียนใหม่ให้ไม่ cache null

```csharp
public async Task<IActionResult> Get(int id)
{
    var key = $"emp:{id}";

    if (!_cache.TryGetValue(key, out Employee? emp))
    {
        emp = await _repo.FindAsync(id);
        if (emp is not null)
            _cache.Set(key, emp, TimeSpan.FromMinutes(5));
    }

    return emp is not null ? Ok(emp) : NotFound();
}
```

ยาวกว่าเดิมไม่กี่บรรทัด แต่ชัดเจนว่าอะไรลง cache อะไรไม่ลง

ถ้าบอกมาว่า service นี้รันกี่ instance และมี endpoint update ด้วยไหม เดี๋ยวแนะนำต่อได้ว่าควรอยู่กับ `IMemoryCache` หรือย้ายไป distributed cache ครับ
