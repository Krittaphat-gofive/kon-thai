ตั้งสติก่อนครับ แล้วทำตามลำดับนี้ เรื่องสำคัญที่สุดคือ **เปลี่ยนรหัสผ่าน database เดี๋ยวนี้** ส่วนการล้าง git history ไว้ทีหลังได้

เหตุผลคือมี bot ที่คอยไล่ดู public commit stream ของ GitHub แบบ real-time ปกติเจอ secret ภายในไม่กี่วินาทีถึงไม่กี่นาที ผ่านไปข้ามวันแล้วให้ถือไปเลยว่ารหัสนี้หลุดถึงมือคนอื่นแน่นอน การลบ commit ทีหลังไม่ได้ช่วยย้อนเวลา

## 1. ทำทันที (ชั่วโมงนี้)

- เปลี่ยนรหัสผ่านของ user ที่อยู่ใน connection string ถ้าทำได้ ให้สร้าง user ใหม่แล้ว disable user เก่าไปเลย จะได้เห็นชัดว่ามีใครพยายามใช้ของเก่าอยู่ไหม
- ปิดทางเข้าจากภายนอก: ตั้ง firewall rule / IP allowlist ให้เหลือเฉพาะ IP ของ app กับ office ถ้า database เปิด public endpoint อยู่ ให้ปิดก่อน
- อัปเดตรหัสใหม่ในที่ที่ใช้จริง (app service, CI/CD secret, เครื่อง dev) แล้ว deploy
- อย่าลืมว่า connection string รั่วทั้งก้อน ไม่ใช่แค่รหัสผ่าน ชื่อ server ชื่อ database ชื่อ user คนอื่นรู้หมดแล้ว

## 2. เช็กว่ามีใครเข้ามาแล้วหรือยัง

ไล่ดูย้อนไปตั้งแต่เวลาที่ push commit นั้น

- connection log / audit log ของ database ว่ามี IP แปลก ๆ หรือ login จากประเทศที่ไม่เกี่ยวข้องไหม
- login ที่ fail รัว ๆ ก็เป็นสัญญาณว่ามีคนลองแล้ว
- ดูว่ามี user, role, table, stored procedure โผล่มาใหม่ไหม
- ปริมาณ query หรือ data transfer ที่กระโดดผิดปกติ มักแปลว่ามีคนดูดข้อมูลออกไป

บน Azure SQL ดูที่ diagnostic log กับ Microsoft Defender for SQL ส่วน PostgreSQL/MySQL ดูที่ log file ของ instance

## 3. ล้าง git history

ทำหลังจากเปลี่ยนรหัสเสร็จแล้วเท่านั้น เครื่องมือที่ใช้ได้คือ `git filter-repo` (แนะนำ) หรือ BFG Repo-Cleaner

```bash
# ลบทั้งไฟล์ออกจากทุก commit
git filter-repo --invert-paths --path appsettings.json

# หรือแทนที่เฉพาะข้อความรหัสผ่าน
git filter-repo --replace-text secrets.txt
```

แล้ว force push ขึ้นไป

ข้อควรรู้ที่คนมักพลาด

- git เขียน commit hash ใหม่หมด ต้องบอกทุกคนในทีมให้ clone ใหม่ อย่า pull/rebase ทับ ไม่งั้น commit เก่าจะเด้งกลับขึ้นไป
- **fork ไม่หายไปด้วย** ถ้ามีใคร fork repo นี้ไปแล้ว ของเก่ายังอยู่ในนั้น
- GitHub ยังเก็บ commit object เดิมไว้บน server เข้าถึงได้ถ้ารู้ hash ต้องเปิด ticket ให้ GitHub Support ช่วย garbage collect และลบ cached view ให้
- ถ้า repo นี้ไม่จำเป็นต้อง public จริง ๆ เปลี่ยนเป็น private ไปก่อนก็ได้ ลดความเสี่ยงระหว่างจัดการ

## 4. เรื่อง PDPA

ถ้าใน database มีข้อมูลส่วนบุคคล และผลการเช็กในข้อ 2 พบว่ามีคนเข้ามาจริง อันนี้เข้าข่ายเหตุละเมิดข้อมูลส่วนบุคคล ต้องแจ้ง DPO ของบริษัท และโดยหลักต้องแจ้ง สคส. ภายใน 72 ชั่วโมงนับจากทราบเหตุ แนะนำให้วน loop หัวหน้าทีมกับฝ่าย compliance ตั้งแต่ตอนนี้เลย ไม่ต้องรอให้ชัวร์ 100% ก่อน

ส่วนกรณีที่เช็กแล้วไม่พบร่องรอยการเข้าถึง ก็ยังควรบันทึกเหตุการณ์ไว้เป็นลายลักษณ์อักษรว่าเกิดอะไรขึ้น ตรวจอะไรไปบ้าง ผลเป็นยังไง

## 5. กันไม่ให้เกิดอีก

- เปิด **secret scanning + push protection** ใน repo settings ของ GitHub ใช้ฟรีกับ public repo ตัวนี้จะบล็อก push ที่มี secret ตั้งแต่แรก
- ติดตั้ง `gitleaks` หรือ `trufflehog` เป็น pre-commit hook และใส่ใน CI pipeline ด้วย
- ย้าย secret ออกจากไฟล์ในโปรเจกต์: ตอน dev ใช้ `dotnet user-secrets` หรือ environment variable ตอน production ใช้ Azure Key Vault / AWS Secrets Manager
- ใน repo เก็บแค่ `appsettings.json` ที่เป็น placeholder แล้วใส่ `appsettings.Development.json` กับ `appsettings.*.local.json` ไว้ใน `.gitignore`

ถ้าบอกได้ว่าใช้ database อะไร host ที่ไหน (Azure SQL, RDS, on-prem) เดี๋ยวผมช่วยชี้ว่า log ตัวไหนที่ควรไล่ดูก่อนครับ
