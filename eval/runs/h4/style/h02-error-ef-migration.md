สาเหตุคือ migration สั่ง `CREATE TABLE Employees` แต่ตารางนี้มีอยู่ใน database แล้วครับ แปลว่า schema กับตาราง `__EFMigrationsHistory` ไม่ตรงกัน EF เลยคิดว่า migration ตัวนั้นยังไม่เคยรัน

## เช็กก่อนว่าสถานะจริงเป็นยังไง

```
dotnet ef migrations list
```

ตัวที่ยังไม่ apply จะมี `(Pending)` ต่อท้าย แล้วเปิด database ดูอีกฝั่ง

```sql
SELECT * FROM __EFMigrationsHistory
```

ถ้าตาราง `Employees` มีอยู่แต่ history ว่างเปล่า (หรือไม่มีตาราง history เลย) ก็ตรงกับอาการนี้พอดี

ต้นเหตุที่เจอบ่อย
- โค้ดตอน startup เรียก `Database.EnsureCreated()` ซึ่งสร้าง schema ให้โดยไม่บันทึกลง history ใช้คู่กับ migrations ไม่ได้
- restore database มาจากที่อื่น หรือสร้างตารางด้วย SQL เอง
- ลบไฟล์ migration เดิมทิ้งแล้ว `migrations add` ใหม่ ทำให้ MigrationId ไม่ตรงกับที่บันทึกไว้
- connection string ชี้ไป database ที่มีตารางอยู่แล้ว

## ทางแก้ เลือกตามสถานการณ์

**1. เป็น dev database ไม่มีข้อมูลที่ต้องเก็บ**

ลบทิ้งแล้วสร้างใหม่ ง่ายและชัวร์ที่สุด

```
dotnet ef database drop -f
dotnet ef database update
```

**2. ข้อมูลต้องเก็บไว้ และ schema ตรงกับ migration อยู่แล้ว**

ทำ baseline คือบอก EF ว่า migration ตัวนี้ apply ไปแล้ว ด้วยการ insert แถวเข้า history เอง

```sql
INSERT INTO [__EFMigrationsHistory] ([MigrationId], [ProductVersion])
VALUES (N'20260101000000_InitialCreate', N'9.0.0');
```

`MigrationId` ต้องตรงกับชื่อไฟล์ migration เป๊ะ ๆ (ไม่เอานามสกุล `.cs`) ส่วน `ProductVersion` ดูได้จากบรรทัด `HasAnnotation("ProductVersion", ...)` ใน `ModelSnapshot.cs` ถ้าตาราง `__EFMigrationsHistory` ยังไม่มี ให้สร้างก่อนด้วย script จากข้อ 3

เสร็จแล้วค่อยรัน `dotnet ef database update` ต่อ ตัวที่เหลือจะไหลไปตามปกติ

**3. schema มีอยู่แต่ไม่ตรงทั้งหมด**

gen script ออกมาดูแล้วแก้มือ

```
dotnet ef migrations script --idempotent -o migrate.sql
```

เปิด `migrate.sql` ตัดส่วน `CREATE TABLE` ที่มีอยู่แล้วออก เหลือเฉพาะส่วนที่ database ยังไม่มี แล้วรันใน SSMS ข้อควรระวังคือ `--idempotent` เช็กแค่ระดับ migration จาก history ไม่ได้เช็กว่าตารางมีอยู่จริงไหม ดังนั้นถ้า history ว่าง script ก็ยังสั่ง `CREATE TABLE` ซ้ำอยู่ดี

## อีกเรื่องที่ควรเก็บกวาด

ถ้าเจอ `EnsureCreated()` ใน `Program.cs` หรือใน seeding code ให้เอาออก แล้วใช้ `Database.Migrate()` แทน ไม่งั้นปัญหานี้จะกลับมาทุกครั้งที่สร้าง database ใหม่

ถ้าไม่แน่ใจว่าเข้าเคสไหน ส่งผลของ `dotnet ef migrations list` กับข้อมูลในตาราง `__EFMigrationsHistory` มาดูได้ครับ เดี๋ยวบอกให้ว่าควรไปทางไหน
