แปลว่า EF กำลังจะรัน migration ที่สั่ง `CREATE TABLE Employees` แต่ตารางนั้นมีอยู่ใน database แล้วครับ ต้นตอเกือบทุกครั้งคือตาราง `__EFMigrationsHistory` ไม่มี record ของ migration ตัวนั้น EF เลยคิดว่ายังไม่เคยรัน

## เช็กสองอย่างก่อน

**1. ต่อถูก database ไหม**

เผลอชี้ไปคนละ DB เจอบ่อยมาก ดูว่า `ASPNETCORE_ENVIRONMENT` ตอนนี้เป็นอะไร แล้วมันหยิบ connection string จาก appsettings ไฟล์ไหน ลองสั่งแบบระบุชัด ๆ

```bash
dotnet ef database update --connection "Server=...;Database=...;"
```

**2. ดู migration history ใน DB**

```sql
SELECT * FROM __EFMigrationsHistory
```

ถ้าตารางนี้ไม่มี หรือมีแต่ว่าง ทั้งที่ตาราง `Employees` มีข้อมูลอยู่ ก็ชัดเจนว่าใครสร้าง schema ไว้นอกเส้นทาง migration

## ทางแก้ เลือกตามสถานการณ์

**กรณี A: dev อยู่ ข้อมูลทิ้งได้** วิธีเร็วสุด

```bash
dotnet ef database drop
dotnet ef database update
```

**กรณี B: ต้องเก็บข้อมูลไว้ และ schema ตรงกับ migration อยู่แล้ว** ให้ baseline คือบอก EF ว่า migration ตัวแรกรันไปแล้ว ด้วยการ insert record เข้า history เอง

ดูชื่อ migration ให้ตรงเป๊ะก่อน

```bash
dotnet ef migrations list
dotnet ef --version
```

แล้วรัน

```sql
INSERT INTO __EFMigrationsHistory (MigrationId, ProductVersion)
VALUES ('20260101120000_InitialCreate', '9.0.0');
```

`MigrationId` ต้องตรงกับชื่อไฟล์ migration ทุกตัวอักษร (ไม่เอา `.cs`) ไม่งั้นรอบหน้าจะชนซ้ำ จากนั้นสั่ง `dotnet ef database update` อีกที EF จะข้ามตัวแรกไปรันตัวถัดไปต่อ

ข้อควรระวัง วิธีนี้ตั้งอยู่บนสมมติฐานว่า schema จริงใน DB ตรงกับที่ migration ตัวแรกเขียนไว้ ถ้าไม่ตรง ปัญหาจะไปโผล่ที่ migration ตัวหลัง ๆ แทน เช็กด้วยการ generate script ออกมาอ่านก่อนได้

```bash
dotnet ef migrations script --idempotent -o migrate.sql
```

**กรณี C: ใน `Program.cs` มี `EnsureCreated()`**

```csharp
db.Database.EnsureCreated();   // ตัวต้นเหตุ
```

`EnsureCreated` สร้างตารางจาก model ตรง ๆ โดยไม่แตะ `__EFMigrationsHistory` เลย ใช้คู่กับ migration ไม่ได้ ให้เปลี่ยนเป็น

```csharp
db.Database.Migrate();
```

แล้วกลับไปทำตามกรณี A หรือ B เพื่อเคลียร์ DB ที่ค้างอยู่

---

ถ้าบอกได้ว่า `__EFMigrationsHistory` ในมือตอนนี้มีอะไรอยู่บ้าง กับ DB ตัวนี้เป็น dev หรือมีข้อมูลจริง เดี๋ยวผมชี้ทางที่ตรงที่สุดให้ครับ
