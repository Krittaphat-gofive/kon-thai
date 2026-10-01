แปลว่า EF พยายามจะสร้างตาราง `Employees` แต่ในฐานข้อมูลมีตารางนั้นอยู่แล้วครับ คือตัว schema กับตาราง `__EFMigrationsHistory` ไม่ตรงกัน EF เลยคิดว่า migration ตัวนี้ยังไม่เคยรัน

## ไล่เช็กก่อน 3 อย่าง

**1. connection string ชี้ไปที่ไหน** เคสที่เจอบ่อยสุดคือชี้ไปผิด database เช่น dev DB ที่ทีมใช้ร่วมกัน ซึ่งมีตารางครบอยู่แล้ว

**2. ดูว่า migration ไหนรันไปแล้วบ้าง**

```
dotnet ef migrations list
```

ตัวที่ยังไม่รันจะมีคำว่า `(Pending)` ต่อท้าย

**3. เปิดดูตาราง history ตรง ๆ**

```sql
SELECT * FROM [__EFMigrationsHistory] ORDER BY MigrationId;
```

ถ้าตารางนี้ว่างหรือไม่มีเลย แต่ `Employees` กับตารางอื่น ๆ มีครบ แปลว่าใครสักคนสร้าง schema ด้วยวิธีอื่น ส่วนใหญ่คือ `context.Database.EnsureCreated()` หรือรัน SQL script มือ สองตัวนี้ไม่เขียน history ไว้ให้

## ทางแก้ ขึ้นกับว่าข้อมูลใน DB ทิ้งได้ไหม

### เคส A: เป็น local dev ข้อมูลทิ้งได้

ง่ายสุดคือลบทิ้งแล้วรันใหม่

```
dotnet ef database drop -f
dotnet ef database update
```

ได้ schema ที่ตรงกับ migration เป๊ะ ๆ และ history ครบ

### เคส B: ข้อมูลทิ้งไม่ได้ และ schema ตรงกับ migration อยู่แล้ว

ให้ทำ baseline คือบอก EF ว่า migration ตัวนี้รันไปแล้ว ด้วยการ insert เข้า history เอง

```sql
INSERT INTO [__EFMigrationsHistory] ([MigrationId], [ProductVersion])
VALUES (N'20260115093000_InitialCreate', N'9.0.0');
```

`MigrationId` ต้องตรงกับชื่อไฟล์ใน โฟลเดอร์ `Migrations/` แบบเป๊ะ ๆ รวม timestamp ด้วย ส่วน `ProductVersion` ใส่เวอร์ชัน EF Core ที่โปรเจกต์ใช้อยู่

ถ้ามี migration หลายตัวที่รันไปแล้ว ก็ insert ให้ครบทุกตัวตามลำดับ แล้วค่อย `dotnet ef database update` ตัวที่เหลือจะรันต่อเอง

**ก่อน insert ควรเช็กให้ชัวร์ก่อน** ว่า schema ใน DB ตรงกับที่ migration จะสร้างจริง ๆ ไม่งั้นจะมี column หายไปแบบเงียบ ๆ แล้วไปพังตอน runtime วิธีเช็กคือ gen script ออกมาดูก่อน

```
dotnet ef migrations script 0 InitialCreate -o check.sql
```

เอา `check.sql` ไปเทียบกับ schema จริง

### เคส C: schema ใน DB ไม่ตรงกับ migration

เช่นมีตาราง `Employees` แต่ column ไม่เหมือนกัน แบบนี้ baseline ไม่ได้ ต้องเลือกว่าจะยึดอะไรเป็นหลัก

- ยึด DB เป็นหลัก: ลบไฟล์ใน `Migrations/` ทิ้ง แล้ว `dotnet ef migrations add InitialCreate` ใหม่จาก model ปัจจุบัน จากนั้น baseline ตามเคส B
- ยึด model เป็นหลัก: เขียน migration เพิ่มเพื่อแก้ส่วนที่ต่าง แล้วรันปกติ

## กันไม่ให้เกิดอีก

อย่าใช้ `EnsureCreated()` คู่กับ migrations ในโปรเจกต์เดียวกัน เลือกอย่างใดอย่างหนึ่ง ถ้าใช้ migrations แล้วก็เอา `EnsureCreated()` ออกจาก startup ให้หมด แล้วเปลี่ยนไปใช้ `Database.Migrate()` แทน หรือดีกว่านั้นคือ gen script แล้วรันใน deploy pipeline

```
dotnet ef migrations script --idempotent -o migrate.sql
```

script แบบ idempotent จะข้าม migration ที่ลงไปแล้วให้เอง แต่ย้ำว่าตัวนี้เช็กจาก `__EFMigrationsHistory` เหมือนกัน ถ้า history เพี้ยนอยู่ก็ยังพังเหมือนเดิม ต้อง baseline ให้เรียบร้อยก่อน

ถ้าบอกได้ว่าตาราง `__EFMigrationsHistory` มีข้อมูลอะไรอยู่ กับ DB นี้เป็น local หรือ server ที่มีข้อมูลจริง เดี๋ยวผมชี้ทางที่ตรงกับเคสให้ครับ
