ด้านล่างเป็นหัวข้อที่เขียนไว้ให้ copy ไปวางใน README ได้เลยครับ ผมตั้งสมมติฐานไว้ 3 อย่าง (ปรับชื่อให้ตรงโปรเจกต์จริงได้เลย): โครงสร้างโฟลเดอร์เป็น `src/Api` กับ `src/web`, backend ใช้ EF Core migrations และ Angular เรียก API ผ่าน proxy

````markdown
## วิธีรันโปรเจกต์บนเครื่อง

### สิ่งที่ต้องติดตั้งก่อน

| เครื่องมือ | เวอร์ชันที่ใช้ |
|---|---|
| [.NET SDK](https://dotnet.microsoft.com/download) | 9.0 ขึ้นไป |
| [Node.js](https://nodejs.org/) | 20.19+, 22.12+ หรือ 24+ (ข้อกำหนดของ Angular 20) |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | เวอร์ชันล่าสุด |

ตรวจสอบว่าติดตั้งครบแล้ว:

```bash
dotnet --version   # ต้องขึ้นต้นด้วย 9.
node --version
docker --version
```

### 1. Clone โปรเจกต์

```bash
git clone <repo-url>
cd <ชื่อโฟลเดอร์โปรเจกต์>
```

### 2. รัน SQL Server ด้วย Docker

โปรเจกต์มีไฟล์ `docker-compose.yml` สำหรับฐานข้อมูลบนเครื่อง dev อยู่แล้ว:

```yaml
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: sqlserver-dev
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "Your_password123!"
      MSSQL_PID: "Developer"
    ports:
      - "1433:1433"
    volumes:
      - mssql-data:/var/opt/mssql

volumes:
  mssql-data:
```

สั่งรัน:

```bash
docker compose up -d
```

ตรวจสอบว่า container ขึ้นแล้ว:

```bash
docker compose ps
docker compose logs -f sqlserver   # รอจนเห็น "SQL Server is now ready for client connections"
```

> **หมายเหตุ**
> - รหัสผ่าน SA ต้องยาวอย่างน้อย 8 ตัวอักษร และมีตัวพิมพ์ใหญ่ พิมพ์เล็ก ตัวเลข และอักขระพิเศษ ไม่งั้น container จะดับทันทีหลังสตาร์ท
> - ข้อมูลถูกเก็บใน volume `mssql-data` ถ้าต้องการล้างฐานข้อมูลทั้งหมดให้ใช้ `docker compose down -v`
> - บน Mac ที่เป็น Apple Silicon ต้องเปิด Rosetta ใน Docker Desktop (Settings → General → Use Rosetta for x86/amd64 emulation)

### 3. ตั้งค่าและรัน Backend (.NET 9)

ตั้งค่า connection string ผ่าน User Secrets เพื่อไม่ให้รหัสผ่านหลุดเข้า git:

```bash
cd src/Api
dotnet user-secrets init
dotnet user-secrets set "ConnectionStrings:DefaultConnection" "Server=localhost,1433;Database=AppDb;User Id=sa;Password=Your_password123!;TrustServerCertificate=True"
```

> `TrustServerCertificate=True` จำเป็นสำหรับ dev เพราะ SQL Server ใน container ใช้ self-signed certificate

สร้างฐานข้อมูลและรัน migrations:

```bash
dotnet tool install --global dotnet-ef   # ข้ามได้ถ้าติดตั้งไว้แล้ว
dotnet restore
dotnet ef database update
```

รัน API:

```bash
dotnet run
```

API จะรันที่ `https://localhost:5001` และดู endpoint ทั้งหมดได้ที่ `https://localhost:5001/swagger`

ถ้าเบราว์เซอร์เตือนเรื่องใบรับรองไม่ปลอดภัย ให้รันคำสั่งนี้หนึ่งครั้ง:

```bash
dotnet dev-certs https --trust
```

### 4. ตั้งค่าและรัน Frontend (Angular 20)

เปิด terminal อีกหน้าต่างหนึ่ง:

```bash
cd src/web
npm ci
npm start
```

เปิดเบราว์เซอร์ที่ `http://localhost:4200`

Angular dev server จะ proxy request ที่ขึ้นต้นด้วย `/api` ไปยัง backend ตามค่าใน `proxy.conf.json`:

```json
{
  "/api": {
    "target": "https://localhost:5001",
    "secure": false,
    "changeOrigin": true
  }
}
```

ถ้าเปลี่ยนพอร์ตของ API อย่าลืมแก้ `target` ในไฟล์นี้ด้วย

### สรุปพอร์ตที่ใช้

| Service | URL |
|---|---|
| Angular (dev server) | http://localhost:4200 |
| .NET API | https://localhost:5001 |
| Swagger UI | https://localhost:5001/swagger |
| SQL Server | localhost,1433 |

### ปัญหาที่พบบ่อย

**`docker compose up` แล้ว container ดับทันที**
ดู log ด้วย `docker compose logs sqlserver` ส่วนใหญ่เกิดจากรหัสผ่าน SA ไม่ผ่านเกณฑ์ความซับซ้อน

**พอร์ต 1433 ถูกใช้งานอยู่แล้ว**
ถ้ามี SQL Server ติดตั้งบนเครื่องอยู่แล้ว ให้เปลี่ยน port mapping เป็น `"14330:1433"` แล้วแก้ connection string เป็น `Server=localhost,14330`

**`dotnet ef database update` ขึ้น error เชื่อมต่อไม่ได้**
ตรวจสอบว่า container พร้อมใช้งานแล้วจริง (SQL Server ใช้เวลาสตาร์ทประมาณ 10–30 วินาทีหลัง `docker compose up`)

**Angular ขึ้น error เรื่อง Node version**
Angular 20 ไม่รองรับ Node 18 แล้ว ให้อัปเกรดเป็น Node 20.19+ ขึ้นไป แนะนำให้ใช้ [nvm](https://github.com/nvm-sh/nvm) จัดการหลายเวอร์ชัน
````

สองจุดที่อยากให้ตรวจก่อนใช้งาน: ชื่อฐานข้อมูล (`AppDb`) และ path โฟลเดอร์ ถ้าโปรเจกต์ไม่ได้ใช้ EF Core migrations ให้แทนขั้นตอน `dotnet ef database update` ด้วยวิธี init ฐานข้อมูลที่ใช้จริง (เช่น รัน SQL script หรือ DbUp)
