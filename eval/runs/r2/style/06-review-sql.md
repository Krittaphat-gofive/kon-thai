ตัวการหลักคือ `YEAR(e.StartDate)` ครับ พอเอาคอลัมน์ไปห่อด้วยฟังก์ชัน แบบนี้ทำให้ query ใช้ index ไม่ได้ SQL Server ต้องคำนวณ `YEAR()` ทีละแถวให้ครบ 2 ล้านแถวก่อน ถึงจะรู้ว่าแถวไหนผ่าน สุดท้ายเลยลงเอยที่ clustered index scan ทุกรอบ

## จุดที่ช้า เรียงตามน้ำหนัก

**1. เงื่อนไขปี ไม่ SARGable**

เขียนเป็นช่วงวันแทน optimizer จะ seek ได้ทันที

```sql
AND e.StartDate >= '2026-01-01'
AND e.StartDate <  '2027-01-01'
```

ใช้ `<` วันที่ 1 ม.ค. ปีถัดไป ไม่ใช่ `<= '2026-12-31'` เพราะถ้าคอลัมน์เป็น `datetime` แถวที่เวลา 2026-12-31 08:30 จะหลุดหายไป

**2. น่าจะไม่มี index ที่ครอบเงื่อนไขนี้**

ต่อให้แก้ข้อ 1 แล้ว ถ้าไม่มี index รองรับก็ยัง scan อยู่ดี ตัวที่ควรมีคือ

```sql
CREATE NONCLUSTERED INDEX IX_Employee_CompanyId_StartDate
ON dbo.Employee (CompanyId, StartDate)
INCLUDE (FirstName, LastName, /* คอลัมน์ที่ใช้จริง */);
```

เอา `CompanyId` ไว้หน้าเพราะเป็นเงื่อนไขแบบ equality แล้วค่อยตามด้วย `StartDate` ที่เป็น range ถ้าสลับลำดับ index จะช่วยได้ไม่เต็มที่

**3. `SELECT *` กินแรงสองต่อ**

ต่อให้สร้าง nonclustered index แล้ว การดึงทุกคอลัมน์บังคับให้ต้องวิ่ง key lookup กลับไปที่ clustered index ทีละแถว พอจำนวนแถวเยอะพอ optimizer จะมองว่า scan ทั้งตารางถูกกว่า แล้วทิ้ง index ที่เพิ่งสร้างไปเฉย ๆ

อีกต่อคือ sort ข้อถัดไปจะต้องแบกข้อมูลทุกคอลัมน์ไปด้วย เสี่ยง spill ลง tempdb

ให้ระบุเฉพาะคอลัมน์ที่ใช้จริง แล้วเอาคอลัมน์พวกนั้นไปใส่ `INCLUDE` ให้ index ครอบคลุม จะได้ไม่ต้อง lookup เลย

**4. `ORDER BY FirstName` กับการไม่มี paging**

ถ้าผลลัพธ์หลังกรองเหลือหลักพัน sort ก็ไม่หนักเท่าไหร่ แต่ถ้าเหลือหลักแสนแล้วส่งกลับหมด ตรงนี้จะกลายเป็นคอขวดแทน

## query หลังแก้

```sql
SELECT e.EmployeeId, e.FirstName, e.LastName, e.StartDate   -- เอาเท่าที่ใช้
FROM dbo.Employee e
WHERE e.CompanyId = @CompanyId
  AND e.StartDate >= @YearStart      -- DATE/DATETIME ให้ตรง type กับคอลัมน์
  AND e.StartDate <  @NextYearStart
ORDER BY e.FirstName
OFFSET @Skip ROWS FETCH NEXT @Take ROWS ONLY;
```

## สองเรื่องที่อยากให้เช็กเพิ่ม

**type ของ `@CompanyId`** ถ้า declare ไม่ตรงกับคอลัมน์ เช่นคอลัมน์เป็น `int` แต่ส่ง `nvarchar` มา หรือคอลัมน์เป็น `varchar` แล้วส่ง `nvarchar` (EF Core ชอบทำแบบนี้) จะเกิด implicit conversion แล้ว index seek หายไปทันที ดูในแผนจะเห็น warning `CONVERT_IMPLICIT`

**ถ้ามี paging และต้องการเลี่ยง sort** ลองอีกแบบคือ index `(CompanyId, FirstName) INCLUDE (StartDate, ...)` แบบนี้อ่านตามลำดับ `FirstName` ได้เลย ไม่ต้อง sort แล้วกรองปีเป็น residual predicate เหมาะกับกรณีดึงแค่ 50 แถวแรก แต่ถ้าดึงทั้งชุด ตัวแรกจะดีกว่า

ลองรันพร้อม actual execution plan แล้วส่งมาดูได้ครับ จะได้ยืนยันว่าติดที่ scan จริงหรือมีอย่างอื่นแทรกอยู่
