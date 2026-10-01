อาการนี้คือ EF พยายามจะ "สร้าง" ตาราง Employees ใหม่ แต่ในฐานข้อมูลมีอยู่แล้ว พูดง่าย ๆ คือ schema ในฐานข้อมูลกับประวัติ migration ไม่ตรงกัน

สาเหตุที่เจอบ่อยสุดสามแบบ:
- ฐานข้อมูลถูกสร้างด้วย `EnsureCreated()` มาก่อน (ตัวนี้ไม่เขียนประวัติลง `__EFMigrationsHistory`)
- สร้างตารางด้วย SQL มือ หรือ restore มาจากที่อื่น
- ตาราง `__EFMigrationsHistory` ถูกลบ/ไม่ถูก migrate มาด้วย

**เช็กก่อนว่าสถานะจริงเป็นยังไง**

```powershell
dotnet ef migrations list
```

แล้วดูในฐานข้อมูลว่า `__EFMigrationsHistory` มีอยู่ไหม มีกี่แถว

```sql
SELECT * FROM [__EFMigrationsHistory];
```

ถ้าตารางนี้ว่างหรือไม่มีเลย ทั้งที่ตาราง Employees มีข้อมูลอยู่แล้ว ก็ยืนยันได้ว่าเป็นเคสนี้

---

**ทางแก้ เลือกตามว่าข้อมูลใน DB ทิ้งได้หรือไม่**

### 1. ถ้าเป็นเครื่อง dev ข้อมูลทิ้งได้ (ง่ายและสะอาดที่สุด)

```powershell
dotnet ef database drop -f
dotnet ef database update
```

`drop` ลบฐานข้อมูลทั้งก้อน ข้อมูลหายหมดและกู้ไม่ได้ ถ้าไม่แน่ใจว่าชี้ไปที่ DB ตัวไหน เช็ค connection string ก่อน

### 2. ถ้าต้องเก็บข้อมูลไว้ — ทำ baseline

คือบอก EF ว่า "migration แรกรันไปแล้วนะ" โดยไม่ต้องรัน SQL จริง เอา MigrationId จากคำสั่ง `migrations list` มาใส่

```sql
INSERT INTO [__EFMigrationsHistory] ([MigrationId], [ProductVersion])
VALUES ('20260101000000_InitialCreate', '9.0.0');
```

(ถ้ายังไม่มีตาราง `__EFMigrationsHistory` ให้รัน `dotnet ef migrations script` ดู แล้วก๊อปส่วน `CREATE TABLE [__EFMigrationsHistory]` มารันก่อน)

จากนั้น `dotnet ef database update` อีกครั้ง มันจะข้าม migration แรกไปรันตัวถัด ๆ ไปแทน

ข้อควรระวัง: วิธีนี้ปลอดภัยก็ต่อเมื่อ schema จริงใน DB **ตรงกับ** ที่ migration แรกจะสร้าง ถ้าไม่ตรง (เช่น คอลัมน์ขาด/ชนิดไม่เหมือน) migration ตัวถัดไปจะพังอีกรอบ

### 3. ถ้า schema ไม่ตรงกันจริง ๆ

ทำ baseline ตามข้อ 2 ก่อน แล้วค่อยสร้าง migration ใหม่ให้ EF ไล่หา diff เอง

```powershell
dotnet ef migrations add SyncSchema
dotnet ef database update
```

ก่อน update ให้เปิดไฟล์ migration ที่ได้มาอ่านดูด้วยว่าไม่มี `DropTable` หรือ `DropColumn` ที่ทำให้ข้อมูลหาย

---

ผมแนะนำข้อ 1 ถ้าเป็น local dev ครับ เร็วและไม่มีของค้าง ส่วนข้อ 2 เก็บไว้ใช้กับ DB ที่มีข้อมูลจริง

บอกได้ไหมครับว่าฐานข้อมูลตัวนี้มีข้อมูลที่ต้องเก็บไหม และ `dotnet ef migrations list` ขึ้นอะไรบ้าง จะได้ชี้ขั้นตอนให้ตรงกว่านี้
