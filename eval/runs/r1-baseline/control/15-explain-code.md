โค้ดนี้คือ **controller action ของ ASP.NET Core ที่ดึงข้อมูลพนักงานตาม id โดยมี in-memory cache คั่นหน้า repository**

## ทำงานทีละขั้น

1. `GetOrCreateAsync($"emp:{id}", ...)` — หา key `emp:123` ใน cache ถ้าเจอก็คืนค่าเลย ไม่แตะ DB
2. ถ้าไม่เจอ จะเรียก factory lambda: ตั้งอายุ entry เป็น **absolute 5 นาที** (นับจากตอนสร้าง ไม่ใช่ sliding) แล้วไปดึงจาก `_repo.FindAsync(id)`
3. `is { } emp` — pattern matching ที่มีความหมายเท่ากับ `!= null` พร้อม bind ค่าลงตัวแปร `emp`
4. ได้ค่า → `200 Ok(emp)`, เป็น null → `404 NotFound()`

ทั้งหมดเขียนเป็น expression-bodied method บรรทัดเดียว

## จุดที่ควรระวัง

**1. Negative caching โดยไม่ตั้งใจ** — อันนี้สำคัญสุด ถ้า `FindAsync` คืน `null`, `GetOrCreateAsync` จะยัง `entry.Value = null` แล้ว commit entry นั้นลง cache อยู่ดี ผลคือ **404 ถูก cache ไว้ 5 นาที** ถ้ามีคนสร้างพนักงาน id นี้ในวินาทีถัดมา API จะยังตอบ 404 ไปอีก ~5 นาที

ถ้าไม่ต้องการพฤติกรรมนี้ ต้องแยกเช็คก่อน แล้วค่อย set cache เฉพาะตอนเจอ:

```csharp
public async Task<IActionResult> Get(int id)
{
    if (!_cache.TryGetValue($"emp:{id}", out Employee? emp))
    {
        emp = await _repo.FindAsync(id);
        if (emp is null) return NotFound();
        _cache.Set($"emp:{id}", emp, TimeSpan.FromMinutes(5));
    }
    return Ok(emp);
}
```

(หรือถ้า *ตั้งใจ* กัน query ถล่ม DB ด้วย id มั่ว ก็เก็บไว้ได้ แต่ควรให้ TTL ของ null สั้นกว่ามาก เช่น 10 วินาที)

**2. Cache stampede** — ไม่มี lock ถ้า 100 requests ถาม id เดียวกันพร้อมกันตอน cache miss ทั้ง 100 จะวิ่งเข้า DB พร้อมกัน แก้ด้วย `SemaphoreSlim` ต่อ key หรือใช้ `HybridCache` (.NET 9+) ที่จัดการ stampede ให้ในตัว

**3. Cache entity ตรง ๆ = แชร์ reference เดียวกัน** — ทุก request ได้ object instance เดียวกัน ถ้ามีโค้ดตรงไหนไป mutate `emp` (เช่น model binding, mapping, lazy-load) จะทำให้ข้อมูลใน cache เพี้ยนไปด้วย ปลอดภัยกว่าถ้า cache เป็น DTO ที่ immutable

**4. ถ้า `MemoryCache` ตั้ง `SizeLimit` ไว้** — entry นี้ไม่ได้กำหนด `e.Size` จะ throw ทันที

**5. `IMemoryCache` เป็น per-process** — ถ้า deploy หลาย instance แต่ละเครื่องมี cache ของตัวเอง ข้อมูลเก่าใหม่ไม่ตรงกัน และ `PUT/DELETE` ที่ invalidate cache บนเครื่องหนึ่งจะไม่มีผลกับอีกเครื่อง กรณีนี้ต้องใช้ `IDistributedCache` / Redis
