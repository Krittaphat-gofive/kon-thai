เขียนให้แล้วครับ ขอเดาโครงโฟลเดอร์เป็น `src/Api` กับ `src/web` ไว้ก่อน ถ้าของจริงไม่ตรงก็แก้ชื่อ path ในไฟล์ได้เลย

````markdown
## วิธีรันโปรเจกต์บนเครื่อง

### สิ่งที่ต้องติดตั้งก่อน

| เครื่องมือ | เวอร์ชัน | เช็กด้วย |
|---|---|---|
| .NET SDK | 9.0 | `dotnet --version` |
| Node.js | 20.19+, 22.12+ หรือ 24.x | `node -v` |
| Docker Desktop | เวอร์ชันล่าสุด | `docker -v` |
| Angular CLI | 20.x | `ng version` |

Angular CLI จะติดตั้งแบบ global ก็ได้ (`npm i -g @angular/cli@20`) หรือเรียกผ่าน `npx ng` แทน

### 1. Clone โค้ดและเตรียม environment

```bash
git clone <repo-url>
cd <repo-name>
```

### 2. รัน SQL Server ด้วย Docker

ไฟล์ `docker-compose.yml` ที่ root:

```yaml
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: app-sqlserver
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "Your_strong_Password123"
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
docker compose logs -f sqlserver   # รอจนขึ้น "SQL Server is now ready for client connections"
```

ครั้งแรก container ใช้เวลาประมาณ 20-30 วินาทีกว่าจะพร้อมรับ connection

> password ของ `sa` ต้องยาวอย่างน้อย 8 ตัว และมีตัวพิมพ์ใหญ่ ตัวพิมพ์เล็ก ตัวเลข หรืออักขระพิเศษ อย่างน้อย 3 ใน 4 กลุ่ม ไม่งั้น container จะดับทันทีที่สตาร์ท

### 3. ตั้งค่า connection string

เก็บ password ไว้ใน user secrets แทนการ commit ลง `appsettings.json`

```bash
cd src/Api
dotnet user-secrets init
dotnet user-secrets set "ConnectionStrings:DefaultConnection" \
  "Server=localhost,1433;Database=AppDb;User Id=sa;Password=Your_strong_Password123;TrustServerCertificate=True"
```

`TrustServerCertificate=True` จำเป็น เพราะ SqlClient เปิด encryption เป็นค่าเริ่มต้น แต่ container ใช้ self-signed certificate

### 4. สร้าง database และรัน migration

```bash
dotnet tool install --global dotnet-ef   # ข้ามได้ถ้าลงไว้แล้ว
dotnet ef database update --project src/Api
```

### 5. รัน API

```bash
dotnet dev-certs https --trust   # ทำครั้งเดียวต่อเครื่อง
cd src/Api
dotnet run
```

API จะขึ้นที่ `https://localhost:7001` และ Swagger อยู่ที่ `https://localhost:7001/swagger`
เลขพอร์ตจริงดูได้จาก `src/Api/Properties/launchSettings.json`

### 6. รัน Angular

เปิด terminal อีกหน้าต่าง:

```bash
cd src/web
npm install
npm start
```

เปิดเบราว์เซอร์ที่ `http://localhost:4200`

ฝั่ง frontend ยิง API ผ่าน proxy เพื่อเลี่ยงปัญหา CORS ตั้งค่าใน `src/web/proxy.conf.json`:

```json
{
  "/api": {
    "target": "https://localhost:7001",
    "secure": false,
    "changeOrigin": true
  }
}
```

### 7. เช็กว่าครบทุกส่วน

- `docker compose ps` เห็น container สถานะ `Up`
- เปิด `https://localhost:7001/swagger` แล้วยิง endpoint ใดก็ได้ผ่าน
- เปิด `http://localhost:4200` แล้วหน้าเว็บโหลดข้อมูลจาก API ได้

### หยุดการทำงาน

```bash
docker compose stop        # หยุด container แต่ข้อมูลยังอยู่
docker compose down        # ลบ container แต่ข้อมูลยังอยู่ใน volume
docker compose down -v     # ลบ volume ด้วย ข้อมูลใน database หายทั้งหมด
```

### ปัญหาที่เจอบ่อย

| อาการ | สาเหตุและวิธีแก้ |
|---|---|
| `Login failed for user 'sa'` | container ยังสตาร์ทไม่เสร็จ รอสักครู่แล้วลองใหม่ หรือ password ใน connection string ไม่ตรงกับใน compose |
| `The certificate chain was issued by an authority that is not trusted` | ลืมใส่ `TrustServerCertificate=True` ใน connection string |
| port 1433 ชนกัน | มี SQL Server ลงบนเครื่องอยู่แล้ว แก้ port mapping เป็น `"14330:1433"` แล้วเปลี่ยน connection string เป็น `Server=localhost,14330` |
| `dotnet ef` ไม่รู้จักคำสั่ง | ยังไม่ได้ติดตั้ง tool หรือ PATH ยังไม่อัปเดต ปิดแล้วเปิด terminal ใหม่ |
| Angular ฟ้องเรื่อง Node version | ใช้ nvm สลับไปเวอร์ชันที่ Angular 20 รองรับ |
| เรียก API จากหน้าเว็บแล้วได้ 404 | ตรวจว่า `npm start` อ่าน `proxy.conf.json` จริง ดูที่ `serve` options ใน `angular.json` |
````

สองจุดที่ควรแก้ให้ตรงกับของจริงก่อนใช้: ชื่อ path (`src/Api`, `src/web`) กับชื่อ database และ connection string key ว่าโค้ดอ่านชื่อไหนอยู่ ถ้าบอกโครงสร้างโฟลเดอร์จริงกับเลขพอร์ตมา เดี๋ยวปรับให้ตรงเป๊ะครับ
