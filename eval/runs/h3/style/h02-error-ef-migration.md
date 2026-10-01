เกิดจาก EF คิดว่า migration ตัวนี้ยังไม่เคยรัน แต่ตาราง `Employees` มีอยู่ใน database แล้วครับ

EF ดูว่า migration ไหนรันไปแล้วจากตาราง `__EFMigrationsHistory` อย่างเดียว ไม่ได้ไปส่องว่าตารางจริงมีอะไรบ้าง พอ history ไม่มีแถวของ migration ตัวนั้น ก็สั่ง `CREATE TABLE Employees` ตามปกติ แล้วชนกับของเดิม

สาเหตุที่เจอบ่อย
- สร้าง database ด้วย `EnsureCreated()` มาก่อน ตัวนี้ไม่เขียน history ไว้เลย
- เอา database มาจากที่อื่น (restore/copy จาก prod หรือของเพื่อน) แต่ history ไม่ได้มาด้วยหรือมาไม่ครบ
- merge branch แล้วได้ migration ที่ `CREATE TABLE Employees` ซ้ำกับตัวเก่า
- เคยรัน migration แล้วพังกลางทาง ตารางสร้างไปแล้วแต่ยังไม่ได้บันทึกลง history

## เช็กก่อนว่าเป็นเคสไหน

```bash
dotnet ef migrations list
```

ดูว่ามีตัวไหนบ้าง ตัวที่ขึ้น `(Pending)` คือตัวที่กำลังจะรัน แล้วเปิดไฟล์ migration ตัวนั้นดู `Up()` ว่ามี `CreateTable(name: "Employees", ...)` จริงไหม

จากนั้นดู history ใน database

```sql
SELECT * FROM __EFMigrationsHistory ORDER BY MigrationId;
```

ถ้าตารางนี้ว่างหรือไม่มีอยู่เลย แปลว่าเป็นเคส `EnsureCreated()` หรือ restore มา

## ทางแก้

**ถ้าเป็น database สำหรับ dev ที่ข้อมูลหายได้** ทางนี้สะอาดที่สุด

```bash
dotnet ef database drop -f
dotnet ef database update
```

เช็ก connection string ให้ชัวร์ก่อนว่าชี้ไป local จริง คำสั่งนี้ลบทั้ง database

**ถ้าต้องเก็บข้อมูลไว้ และ schema ที่มีอยู่ตรงกับ migration แล้ว** ให้บอก EF ว่า migration ตัวนี้รันไปแล้ว ด้วยการใส่แถวใน history เอง

```sql
INSERT INTO __EFMigrationsHistory (MigrationId, ProductVersion)
VALUES ('20260101120000_InitialCreate', '9.0.0');
```

`MigrationId` เอาจากชื่อไฟล์ migration ตรง ๆ (ส่วนหน้า `.cs`) ส่วน `ProductVersion` ใส่เวอร์ชัน EF Core ที่ใช้อยู่ ดูได้จาก `dotnet ef --version` ถ้ามี migration ก่อนหน้าหลายตัวที่ schema ครอบคลุมอยู่แล้ว ก็ใส่ให้ครบทุกตัว แล้วค่อยรัน `dotnet ef database update` ต่อ ที่เหลือจะรันแค่ตัวที่ยัง pending จริง ๆ

ถ้าตาราง `__EFMigrationsHistory` ยังไม่มี ให้ generate script มาดูโครงก่อน

```bash
dotnet ef migrations script -o migrate.sql
```

ในไฟล์จะมีท่อน `CREATE TABLE [__EFMigrationsHistory]` ให้ก๊อปไปรันเฉพาะท่อนนั้น แล้วค่อย insert แถวตามข้างบน

**ถ้า schema ของจริงกับ migration ไม่ตรงกัน** อย่าใช้วิธี insert history เพราะจะพังตัวถัดไปแทน กรณีนี้ลบ migration ที่มีปัญหาออก (`dotnet ef migrations remove`) แล้วสร้างใหม่เป็น baseline ที่ตรงกับ database ปัจจุบัน จากนั้นค่อยทำ migration ส่วนที่ต้องการเปลี่ยนจริงแยกออกมา

**ถ้าเป็นเคส merge แล้ว migration ซ้ำ** ให้ลบตัวที่สร้างตารางซ้ำทิ้ง แล้ว `dotnet ef migrations add` ใหม่ ให้ EF เทียบกับ snapshot ปัจจุบันเอง

ส่ง output ของ `dotnet ef migrations list` กับผลจาก `SELECT * FROM __EFMigrationsHistory` มาได้ครับ เดี๋ยวดูให้ว่าควรไปทางไหน
