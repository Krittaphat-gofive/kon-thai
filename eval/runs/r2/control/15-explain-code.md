โค้ดนี้เป็น action method ของ ASP.NET Core ที่ดึงข้อมูลพนักงานตาม `id` โดยมี in-memory cache คั่นหน้า repository

## แยกทีละส่วน

**1. Expression-bodied async method** — ทั้งเมธอดคือ expression เดียว ไม่มี `{ }` body

**2. `_cache.GetOrCreateAsync($"emp:{id}", ...)`** — extension method ของ `IMemoryCache` ทำงานแบบ:
- ถ้ามี key `emp:5` ใน cache อยู่แล้ว → คืนค่าจาก cache ทันที ไม่เรียก factory
- ถ้าไม่มี → เรียก factory lambda เพื่อสร้างค่า แล้วเก็บลง cache

**3. Factory lambda** — พารามิเตอร์ `e` คือ `ICacheEntry` ใช้ตั้งค่า entry นั้น ตรงนี้กำหนด `AbsoluteExpirationRelativeToNow = 5 นาที` คือหมดอายุแบบตายตัว 5 นาทีหลังถูกเก็บ (ไม่ใช่ sliding — เข้าถึงบ่อยแค่ไหนก็ไม่ยืดอายุ) จากนั้น `_repo.FindAsync(id)` ไปดึงจากฐานข้อมูลจริง

**4. `is { } emp ? Ok(emp) : NotFound()`** — `is { }` คือ property pattern ที่ match ค่าอะไรก็ได้ที่ไม่ใช่ null (เทียบเท่า `is not null`) พร้อมผูกค่าเข้าตัวแปร `emp` ถ้าเจอข้อมูลก็คืน 200 พร้อม body ถ้าเป็น null ก็คืน 404

สรุปคือ: **เช็ค cache ก่อน ถ้าไม่มีค่อยยิง DB แล้ว cache ไว้ 5 นาที เจอ → 200, ไม่เจอ → 404**

## จุดที่ควรรู้

**Negative caching** — ถ้า `FindAsync` คืน `null` ตัว `GetOrCreateAsync` ก็ยัง `entry.Value = null` และเก็บลง cache อยู่ดี แปลว่า 404 ถูก cache ไว้ 5 นาทีด้วย ถ้ามีการสร้างพนักงาน id นั้นขึ้นมาระหว่างนั้น API จะยังตอบ 404 ต่ออีกจนกว่าจะหมดอายุ ถ้าไม่ต้องการพฤติกรรมนี้ต้องเช็ค null แล้วค่อยตัดสินใจ cache เอง

**Cache stampede** — `GetOrCreateAsync` ไม่มี lock ถ้ามี request พร้อมกัน 50 ตัวตอน cache miss จะยิง `FindAsync` ทั้ง 50 ตัว ถ้าเป็นปัญหา ใน .NET 9 ขึ้นไปมี `HybridCache` ที่จัดการ stampede protection ให้

**ไม่มี `CancellationToken`** — client ตัดการเชื่อมต่อแล้ว query ยังวิ่งต่อ

**กรณี factory throw** — ตั้งแต่ .NET 7 เป็นต้นไป entry จะไม่ถูก commit (เพราะ `entry.Value` ยังไม่เคยถูก set) exception จะ propagate ออกมาตรงๆ ซึ่งเป็นพฤติกรรมที่ถูกต้อง
