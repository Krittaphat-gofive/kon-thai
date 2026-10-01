ดูจาก syntax แล้วน่าจะเป็น SQL Server ครับ — มีจุดที่น่าสงสัย 3 จุด เรียงตามผลกระทบ

## 1. `YEAR(e.StartDate) = 2026` ทำให้ใช้ index ไม่ได้ (ตัวหลัก)

พอเอาฟังก์ชันไปครอบคอลัมน์ มันจะกลายเป็น non-sargable คือ SQL Server ต้องคำนวณ `YEAR()` ทีละแถวครบทั้ง 2 ล้านแถวก่อน ถึงจะรู้ว่าแถวไหนผ่าน — ใช้ index seek ไม่ได้เลย ต้อง scan ทั้งตาราง

เขียนใหม่เป็น range แทน:

```sql
WHERE e.StartDate >= '2026-01-01'
  AND e.StartDate <  '2027-01-01'
```

ใช้แบบ half-open (`>=` กับ `<`) ไม่ใช้ `BETWEEN '2026-01-01' AND '2026-12-31'` เพราะถ้า `StartDate` เป็น `datetime`/`datetime2` แถวที่เป็นวันที่ 31 ธ.ค. เวลา 10:00 จะหลุดไป

## 2. ไม่มี composite index ที่ตรงกับ predicate

```sql
CREATE INDEX IX_Employee_CompanyId_StartDate
ON Employee (CompanyId, StartDate)
INCLUDE (FirstName, LastName, /* คอลัมน์อื่นที่ใช้จริง */);
```

เอา `CompanyId` ขึ้นก่อนเพราะเป็นเงื่อนไข equality ส่วน `StartDate` เป็น range ต้องตามหลัง (ถ้าสลับกัน จะ seek ได้แค่ช่วง StartDate แล้วต้องกรอง CompanyId ทีหลัง)

## 3. `SELECT *` ทำให้ index ที่สร้างมาอาจไม่ถูกใช้อยู่ดี

อันนี้คนมักมองข้าม — พอดึงทุกคอลัมน์ ต่อให้มี index ข้างบน optimizer ก็ยังต้องทำ key lookup กลับไปที่ clustered index ทีละแถวเพื่อเอาคอลัมน์ที่เหลือ ถ้าผลลัพธ์เกิน tipping point (ประมาณ 1-2% ของตาราง) มันจะตัดสินใจ scan ทั้งตารางแทนเลย คือ index ที่สร้างไว้เสียเปล่า

ให้ระบุเฉพาะคอลัมน์ที่ใช้จริง แล้วเอาคอลัมน์เหล่านั้นใส่ `INCLUDE` เพื่อให้เป็น covering index

## รวมเป็น

```sql
SELECT e.EmployeeId, e.FirstName, e.LastName, e.StartDate  -- เท่าที่ใช้จริง
FROM Employee e
WHERE e.CompanyId = @CompanyId
  AND e.StartDate >= '2026-01-01'
  AND e.StartDate <  '2027-01-01'
ORDER BY e.FirstName;
```

## จุดที่ควรเช็คเพิ่ม

**ชนิดข้อมูลของ `@CompanyId`** — ถ้าคอลัมน์เป็น `varchar` แต่ parameter ประกาศเป็น `nvarchar` (ตัวนี้เจอบ่อยมากเวลาเรียกผ่าน Entity Framework / Dapper) จะเกิด implicit conversion ฝั่งคอลัมน์ แล้วก็ non-sargable เหมือนข้อ 1 เลย ลองดูใน execution plan ว่ามี `CONVERT_IMPLICIT` ตรง predicate ไหม

**`ORDER BY e.FirstName`** — ตัวนี้ยังไงก็ต้องมี Sort operator เพราะ index เรียงตาม `StartDate` ไม่ได้เรียงตามชื่อ แต่ถ้าหลังกรองแล้วเหลือหลักพันแถวก็ไม่ใช่ปัญหา จะหนักก็ต่อเมื่อบริษัทนั้นมีพนักงานเข้าปี 2026 เยอะมากจริง ๆ

**มี pagination หรือยัง** — ถ้าหน้าจอแสดงแค่ 50 แถวแรก การดึงมาทั้งหมดแล้วค่อยตัดฝั่ง application เป็นต้นทุนที่เสียเปล่า ใช้ `OFFSET ... FETCH NEXT` แทน

ถ้าแก้ตามนี้แล้วยังช้า ขอ actual execution plan มาดูได้ครับ จะได้เห็นว่าติดที่ scan, sort หรือ key lookup กันแน่ และจำนวนแถวที่ประมาณไว้ (estimated) ต่างจากของจริง (actual) มากแค่ไหน — ถ้าต่างกันมากอาจเป็นเรื่อง statistics เก่าหรือ parameter sniffing ซึ่งแก้คนละแบบ
