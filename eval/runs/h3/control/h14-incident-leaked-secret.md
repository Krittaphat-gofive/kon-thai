รีบทำตามลำดับนี้เลยครับ — **ข้อ 1 สำคัญกว่าการลบ commit มาก** คนส่วนใหญ่มักรีบลบ history ก่อน ซึ่งผิดลำดับ

## 1. เปลี่ยนรหัสผ่าน database ทันที (ทำก่อนเพื่อน)

ถือว่ารหัสนี้หลุดไปแล้ว 100% ไม่ต้องลุ้น — มี bot ไล่ scan commit ใหม่บน public repo ตลอดเวลา บางตัวเจอภายในไม่กี่วินาทีหลัง push ผ่านมาวันนึงแล้วคือนานพอสมควร

- เปลี่ยน password ของ DB user ตัวนั้น
- ถ้า user ตัวนี้ถูกใช้ที่อื่นด้วย (service อื่น, cron, เครื่อง dev ทีม) ต้องตามเปลี่ยนให้ครบ
- **อัปเดต config ฝั่ง app/secret manager ให้เรียบร้อยก่อนหรือพร้อมกัน** ไม่งั้น service ล่มตามกันหมด
- ถ้าใน connection string มีอย่างอื่นติดไปด้วย (host, port, ชื่อ DB) ก็ถือว่าหลุดหมดเหมือนกัน

## 2. ปิดช่องทางเข้าถึง

เช็กว่า DB server เปิดรับ connection จากเน็ตข้างนอกได้ไหม ถ้าได้ ให้จำกัดทันที — firewall rule, IP allowlist, หรือบังคับผ่าน VPN/private subnet ถ้า DB อยู่หลัง private network อยู่แล้วความเสี่ยงต่ำลงเยอะ แต่ก็ยังต้องเปลี่ยนรหัสอยู่ดี

## 3. ไล่ดู log ว่ามีใครเข้ามาแล้วหรือยัง

ดู connection log / audit log ย้อนตั้งแต่เวลาที่ push ขึ้นไป หา login จาก IP ที่ไม่คุ้น, query แปลก ๆ, การ dump ข้อมูลก้อนใหญ่, หรือ user/table ที่ถูกสร้างเพิ่ม ถ้าเจอร่องรอยต้องยกระดับเป็น incident จริงจังแล้ว ไม่ใช่แค่เปลี่ยนรหัสจบ

## 4. ล้าง git history

ข้อนี้ค่อยทำทีหลังได้ และ**อย่าแค่ commit ใหม่ลบไฟล์ทิ้ง** — commit เก่ายังอยู่ใน history ใครก็ยังเปิดดูได้

ใช้ `git filter-repo` (แนะนำกว่า filter-branch) หรือ BFG:

```
# ลบทั้งไฟล์ออกจากทุก commit
git filter-repo --invert-paths --path path/to/appsettings.json

# หรือแทนที่เฉพาะข้อความ secret
git filter-repo --replace-text secrets.txt
```

แล้ว force push ขึ้นไป จากนั้นบอกทีมให้ re-clone ใหม่ (ห้าม merge ของเก่ากลับมา ไม่งั้น secret โผล่อีก)

ข้อควรรู้: ต่อให้ force push แล้ว GitHub ยังเก็บ commit เก่าไว้ในระบบ เข้าถึงได้ผ่าน URL `/commit/<sha>` โดยตรง ต้องเปิด ticket ให้ GitHub Support purge ให้ และถ้ามีคน fork หรือ clone ไปแล้ว คุณลบของเขาไม่ได้ — ย้ำว่าทำไมข้อ 1 ถึงสำคัญที่สุด

## 5. แจ้งทีม / security ตามนโยบายบริษัท

ถ้าเป็น production DB ที่มีข้อมูลลูกค้า ควรแจ้ง security หรือหัวหน้าทีมไว้ด้วย ไม่ใช่เพื่อโดนด่า แต่เพราะถ้ามีข้อมูลส่วนบุคคลหลุดจริง มันมีเงื่อนไขการรายงานตาม PDPA ที่มี timeline กำหนด — รู้ช้าแล้วแย่กว่า

## 6. กันรอบหน้า

- ย้าย secret ไป env var / secret manager (Azure Key Vault, AWS Secrets Manager, ฯลฯ) และใส่ไฟล์ config ลง `.gitignore`
- เปิด **GitHub Secret Scanning + Push Protection** ที่ repo (ฟรีสำหรับ public repo) ตัวนี้จะบล็อกตั้งแต่ตอน push เลย
- ลง pre-commit hook เช่น `gitleaks` หรือ `trufflehog` ไว้ดักที่เครื่องก่อนขึ้น remote

---

ถ้าจะให้ช่วยดูว่า repo นี้มี secret ค้างอยู่ที่ไหนอีกบ้าง หรือช่วยร่างคำสั่ง `filter-repo` ให้ตรงกับไฟล์จริง บอกได้ครับ
