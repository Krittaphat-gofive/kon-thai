เรื่องเร่งด่วนที่สุดคือเปลี่ยนรหัสผ่าน ไม่ใช่ลบ commit ค่ะ

repo public ที่มี secret ค้างอยู่ 1 วัน ให้ถือว่ารั่วไปแล้วเต็ม ๆ มี bot ที่เฝ้า public event feed ของ GitHub แล้วดึง credential ไปลองใช้ภายในไม่กี่วินาทีหลัง push การลบ commit ทีหลังไม่ช่วยกับคนที่ copy ไปแล้ว

## ทำตามลำดับนี้

**1. เปลี่ยนรหัสผ่าน database เดี๋ยวนี้**

สร้างรหัสใหม่ แล้วอัปเดตที่ทุกที่ที่ใช้อยู่ (app config, CI/CD secret, เครื่อง dev) ถ้าเป็น prod แล้วเปลี่ยนทันทีไม่ได้ ให้ปิดทางเข้าที่ระดับ network ก่อน เช่น ปิด public access ของ database แล้วเหลือแต่ IP allowlist ของ server ที่ใช้งานจริง

ถ้ารหัสตัวนี้เอาไป reuse ที่ระบบอื่นด้วย ต้องเปลี่ยนทั้งหมด

**2. เช็กว่ามีใครเข้ามาแล้วหรือยัง**

- ดู connection log หรือ audit log ย้อนไป 24 ชั่วโมง หา IP ที่ไม่คุ้น หรือ login นอกเวลาทำงาน
- ดูว่ามี user ใหม่โผล่มาไหม สิทธิ์เปลี่ยนไหม ข้อมูลหายหรือเพิ่มผิดปกติไหม
- ดูปริมาณ data ที่อ่านออกไป ถ้ามี metric นี้

ถ้าเจอร่องรอยว่ามีคนเข้ามาจริง เรื่องนี้กลายเป็น data breach ต้องแจ้งทีม security กับฝ่ายที่ดูแล PDPA ต่อ

**3. ล้าง secret ออกจาก git history**

ใช้ `git filter-repo` (เครื่องมือที่ GitHub แนะนำตอนนี้) หรือ BFG ก็ได้

```bash
pip install git-filter-repo
echo 'Server=xxx;Password=yyy' > ../secrets.txt
git filter-repo --replace-text ../secrets.txt
git push --force --all
git push --force --tags
```

หลัง force push บอกทุกคนในทีมให้ clone ใหม่ อย่า pull ทับของเดิม เพราะ commit เก่าจะไหลกลับขึ้นไปอีก

**4. จัดการสำเนาที่ยังค้างอยู่**

ข้อนี้คนมักลืม ถึง force push แล้ว commit เก่ายังเปิดดูได้ผ่าน URL ตรง ๆ อยู่

- เปิด ticket หา GitHub Support ขอให้ purge cached view กับ dangling commit ให้
- ถ้ามีคน fork ไป ต้องให้เจ้าของ fork ลบเอง หรือแจ้ง support ไปพร้อมกัน
- PR เก่าที่ยังเปิดอยู่ก็มี diff ที่เห็นรหัส ลบหรือปิดด้วย

**5. กันไม่ให้ซ้ำ**

- ย้าย connection string ออกไปไว้ที่ environment variable หรือ secret manager (Azure Key Vault, AWS Secrets Manager) ตอน dev ใช้ `dotnet user-secrets` ได้
- เพิ่ม `appsettings.Development.json`, `.env` ลง `.gitignore`
- เปิด secret scanning กับ push protection ใน repo settings ฟรีสำหรับ repo public จะดักให้ตั้งแต่ตอน push
- ติด gitleaks เป็น pre-commit hook ไว้ดักอีกชั้นตั้งแต่ก่อน commit

ถ้าบอกได้ว่าเป็น database อะไรกับ host อยู่ที่ไหน (Azure SQL, RDS, on-prem) เดี๋ยวดูขั้นตอน rotate กับการปิด public access ให้ตรงกว่านี้ค่ะ
