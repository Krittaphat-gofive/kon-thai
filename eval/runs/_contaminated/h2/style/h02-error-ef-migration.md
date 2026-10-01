แปลว่า migration สั่ง `CREATE TABLE Employees` แต่ในฐานข้อมูลมีตารางนี้อยู่แล้วครับ EF ไม่รู้ว่าเคยสร้างไปแล้ว เพราะตาราง `__EFMigrationsHistory` ไม่มีแถวของ migration ตัวนั้นบันทึกไว้

## เช็กก่อนว่าสถานะจริงเป็นยังไง

```sql
SELECT * FROM __EFMigrationsHistory ORDER BY MigrationId;
```

เทียบกับ

```
dotnet ef migrations list
```

สองอันนี้บอกได้เลยว่าตกกรณีไหน ถ้า `__EFMigrationsHistory` ว่างหรือไม่มีตารางนี้เลย แต่ตาราง `Employees` อยู่ครบ แปลว่าตารางมาจากทางอื่นที่ไม่ใช่ migration

อีกอย่างที่ควรเช็กไปพร้อมกัน: connection string ชี้ไป database ตัวที่ตั้งใจจริงหรือเปล่า เคสที่ชี้ผิดตัวไป DB เก่าที่มี schema อยู่แล้วก็เจอ error นี้เหมือนกัน

## กรณีที่ 1: เป็น dev DB ข้อมูลทิ้งได้

ง่ายสุด ลบแล้วสร้างใหม่

```
dotnet ef database drop -f
dotnet ef database update
```

คำสั่งนี้ลบทั้ง database กู้คืนไม่ได้ ใช้เฉพาะเครื่อง dev เท่านั้น อย่าเผลอรันตอน connection string ชี้ไป staging หรือ prod

## กรณีที่ 2: ต้องเก็บข้อมูลไว้ และ schema ตรงกับ migration อยู่แล้ว

ทำ baseline คือบอก EF ว่า migration ตัวนี้ apply ไปแล้ว โดยไม่ต้องรัน SQL ข้างใน

วิธีที่ปลอดภัยสุดคือ gen script ออกมาดูก่อน

```
dotnet ef migrations script --idempotent -o migrate.sql
```

แล้วหยิบเฉพาะท่อน `INSERT INTO [__EFMigrationsHistory]` ของ migration ที่ติดไปรัน ตัว script ที่ EF gen มาจะมีค่า MigrationId กับ ProductVersion ที่ถูกต้องให้อยู่แล้ว ไม่ต้องเดาเอง

หน้าตาประมาณนี้

```sql
INSERT INTO [__EFMigrationsHistory] ([MigrationId], [ProductVersion])
VALUES (N'20260115093012_InitialCreate', N'9.0.0');
```

`MigrationId` ต้องตรงกับชื่อไฟล์ใน โฟลเดอร์ `Migrations` เป๊ะ ๆ (เอาเฉพาะ timestamp กับชื่อ ไม่เอา `.cs`) ถ้าพิมพ์ผิด EF จะยังมองว่ายังไม่ได้ apply แล้วพังซ้ำที่เดิม

เสร็จแล้วรัน `dotnet ef database update` ต่อ ตัวที่เหลือจะไหลไปได้

**ข้อควรระวัง:** วิธีนี้ใช้ได้ต่อเมื่อ schema ใน DB ตรงกับที่ migration จะสร้างจริง ๆ ถ้าคอลัมน์ไม่ครบหรือ type ต่างกัน migration ตัวถัด ๆ ไปจะพังแบบงง ๆ แทน แนะนำให้เทียบ schema ก่อนสักรอบ

## กรณีที่ 3: มี EnsureCreated() อยู่ในโค้ด

อันนี้เป็นสาเหตุที่เจอบ่อยสุด ลองหาใน `Program.cs` หรือ startup

```csharp
db.Database.EnsureCreated();
```

`EnsureCreated` สร้างตารางทั้งหมดจาก model ตรง ๆ โดยไม่แตะ `__EFMigrationsHistory` เลย พอรัน `database update` ทีหลัง EF เลยเห็นว่ายังไม่เคย migrate อะไรและพยายามสร้างตารางซ้ำ

แก้โดยเปลี่ยนเป็น

```csharp
db.Database.Migrate();
```

สองตัวนี้ใช้ร่วมกันในโปรเจกต์เดียวไม่ได้ เลือกอย่างใดอย่างหนึ่ง แล้วจัดการ DB ที่พังไปตามกรณีที่ 1 หรือ 2 ข้างบน

## กรณีที่ 4: scaffold มาจาก DB ที่มีอยู่แล้ว

ถ้าใช้ `dotnet ef dbcontext scaffold` ดึง model มาจาก DB เดิม แล้ว `migrations add` ตัวแรก EF จะ gen `CreateTable` ให้ทุกตารางที่มีอยู่ ทางแก้คือ comment โค้ดใน `Up()` ของ migration ตัวนั้นทิ้งให้เหลือ method ว่าง ๆ แล้วรัน `database update` EF จะบันทึก history ให้โดยไม่สร้างอะไร จากนั้น migration ตัวถัดไปค่อยเขียนของจริง

---

ถ้าส่งผลลัพธ์จาก `SELECT * FROM __EFMigrationsHistory` กับ `dotnet ef migrations list` มาให้ดู เดี๋ยวผมชี้ให้ว่าควรไปทางไหนครับ
