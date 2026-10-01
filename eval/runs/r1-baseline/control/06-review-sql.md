ปัญหาหลักอยู่ที่ `YEAR(e.StartDate) = 2026` ครับ — มันทำให้ query เป็น **non-SARGable**

## สาเหตุ เรียงตามน้ำหนัก

**1. `YEAR(e.StartDate)` ห่อคอลัมน์ด้วยฟังก์ชัน → ใช้ index seek ไม่ได้**

พอ SQL Server ต้องเรียก `YEAR()` ทีละแถวเพื่อเทียบค่า มันก็ต้องอ่าน `StartDate` ครบทุกแถว = scan 2 ล้าน row ต่อให้มี index บน `StartDate` อยู่ก็ไม่ถูกใช้ seek

**2. `SELECT *` → key lookup / ไม่มีทางทำ covering index**

ถึงจะแก้ข้อ 1 แล้ว ถ้า index ไม่ครอบทุกคอลัมน์ optimizer มักจะเลือก scan แทน seek+lookup อยู่ดี เพราะ lookup ต่อแถวแพงกว่า นอกจากนี้ถ้าตารางมี `nvarchar(max)` หรือคอลัมน์กว้าง ๆ ก็เปลืองทั้ง I/O และ network

**3. `ORDER BY e.FirstName` → Sort operator**

ถ้าผลลัพธ์ใหญ่และ memory grant ไม่พอ จะ spill ลง tempdb ซึ่งช้าขึ้นอีกเป็นเท่าตัว

## แก้ query

```sql
SELECT e.EmployeeId, e.FirstName, e.LastName, e.StartDate  -- ระบุเฉพาะที่ใช้จริง
FROM Employee e
WHERE e.CompanyId = @CompanyId
  AND e.StartDate >= '2026-01-01'
  AND e.StartDate <  '2027-01-01'
ORDER BY e.FirstName;
```

ใช้ `>= ... AND < ...` ไม่ใช่ `BETWEEN '2026-01-01' AND '2026-12-31'` — ถ้า `StartDate` เป็น `datetime`/`datetime2` แบบหลังจะตกข้อมูลของวันที่ 31 ธ.ค. ที่มีเวลาไม่ใช่ 00:00:00

## Index

เลือกตามรูปแบบการใช้งานจริง:

**ถ้าดึงผลลัพธ์ทั้งหมด / ผลลัพธ์ต่อ company ไม่เยอะ:**
```sql
CREATE INDEX IX_Employee_CompanyId_StartDate
ON Employee (CompanyId, StartDate)
INCLUDE (FirstName, LastName);  -- ใส่คอลัมน์ที่ SELECT จริง
```
`CompanyId` (equality) นำหน้า `StartDate` (range) เสมอ — seek ได้แคบที่สุด แล้วค่อย sort ผลลัพธ์ที่เหลือ

**ถ้าหน้าจอมี paging (`OFFSET/FETCH` หรือ `TOP n`):**
```sql
CREATE INDEX IX_Employee_CompanyId_FirstName
ON Employee (CompanyId, FirstName)
INCLUDE (StartDate, LastName);
```
แบบนี้ข้อมูลเรียงตาม `FirstName` มาแล้ว ไม่ต้อง sort เลย กรอง `StartDate` เป็น residual predicate — คุ้มมากเวลาเอาแค่ 50 แถวแรก แต่แย่กว่าถ้าต้องดึงครบทุกแถว

ถ้าหน้านี้ยังไม่มี paging แนะนำให้ใส่ด้วยครับ การส่ง 2 ล้านแถวกลับไป client เป็นคอขวดอีกตัวที่ index แก้ไม่ได้

## จุดที่ควรเช็กต่อ

- **ดู actual execution plan** — มองหา `Index Scan`/`Table Scan` บน Employee และ warning สีเหลืองที่ Sort operator (spill to tempdb)
- **Parameter sniffing จาก `@CompanyId`** — ถ้าแต่ละบริษัทมีพนักงานต่างกันมาก (บริษัทหนึ่ง 50 คน อีกบริษัท 500,000 คน) plan ที่ cache ไว้จากตัวเล็กจะพังกับตัวใหญ่ ลองทดสอบด้วย `OPTION (RECOMPILE)` ถ้าเร็วขึ้นชัดเจน แสดงว่าใช่
- **Statistics** — เช็ก `STATS_DATE()` ว่าอัปเดตล่าสุดเมื่อไหร่ ตาราง 2 ล้านแถวที่ auto-update threshold ยังไม่ถึงอาจมี estimate เพี้ยน

เดาว่าแค่แก้ข้อ 1 + สร้าง index ตัวแรก ก็น่าจะเห็นผลชัดแล้วครับ ถ้ามี execution plan หรือ schema ของตารางมาให้ดูด้วย จะช่วยฟันธงได้แม่นกว่านี้
