รหัสผ่านตัวนั้นถือว่ารั่วไปแล้วแน่นอนครับ ไม่ต้องรอดูว่ามีคนเอาไปใช้หรือเปล่า repo public มี bot ไล่ scan หา secret ตลอดเวลา ส่วนใหญ่เจอภายในไม่กี่นาทีหลัง push ผ่านไปหนึ่งวันนี่สมมติไว้เลยว่ามีคนเก็บไปแล้ว

ลำดับที่ต้องทำ เรียงตามความเร่งด่วน

## 1. เปลี่ยนรหัสผ่าน database ก่อนเลย

ข้อนี้สำคัญกว่าการลบ commit ทั้งหมด เพราะต่อให้ล้าง history สะอาดแค่ไหน รหัสที่หลุดไปแล้วก็ยังใช้งานได้อยู่ดี

- เปลี่ยนรหัสของ user ที่อยู่ใน connection string ทันที
- ถ้า user ตัวนั้นใช้ร่วมกันหลายระบบ ให้สร้าง user ใหม่แยกตาม service แล้วค่อยปิดตัวเก่า จะได้รู้ว่าอะไรพังบ้าง
- อัปเดตค่าใหม่ให้ครบทุก environment ทั้ง app settings, CI/CD secret, เครื่อง dev ในทีม

## 2. ปิดทางเข้าถึงจากข้างนอก

- เช็กว่า database เปิดรับ connection จาก public internet อยู่ไหม ถ้าเปิดให้จำกัด IP allowlist หรือย้ายไปหลัง private endpoint / VPN
- ถ้าเป็น cloud ดู firewall rule ว่ามี 0.0.0.0/0 ค้างอยู่หรือเปล่า อันนี้เจอบ่อยมาก

## 3. ไล่ log ว่ามีใครเข้ามาแล้วหรือยัง

- ดู connection log กับ audit log ย้อนตั้งแต่เวลาที่ push
- มองหา IP ที่ไม่ใช่ของออฟฟิศหรือ server เรา การ login นอกเวลาทำการ query ที่ดึงทั้งตาราง
- เช็กด้วยว่ามี user ใหม่โผล่มา สิทธิ์เปลี่ยน หรือข้อมูลหาย

ข้อนี้อย่าข้าม ถ้าใน database มีข้อมูลส่วนบุคคล แล้วเจอร่องรอยว่ามีคนเข้ามาจริง จะเข้าเงื่อนไข PDPA ที่ต้องแจ้งเหตุภายใน 72 ชั่วโมง ควรบอกทีม security หรือ DPO ไว้ตั้งแต่ตอนนี้

## 4. ล้าง secret ออกจาก git history

ทำหลังเปลี่ยนรหัสแล้วเท่านั้น และต้องเข้าใจว่าแค่ commit ทับไม่พอ ค่าเดิมยังอยู่ใน history

ใช้ `git filter-repo` (แนะนำกว่า BFG ตอนนี้)

```bash
pip install git-filter-repo
git filter-repo --path appsettings.json --invert-paths
# หรือถ้าอยากเก็บไฟล์ไว้แต่แทนที่เฉพาะค่า
git filter-repo --replace-text secrets.txt
git push --force --all
git push --force --tags
```

สองเรื่องที่ต้องรู้
- ทุกคนในทีมต้อง clone ใหม่ ไม่ใช่ pull เพราะ git สร้าง commit hash ใหม่หมด
- GitHub ยัง cache commit เก่าไว้ เข้าถึงผ่าน SHA ตรง ๆ ได้อยู่ และถ้ามีคน fork ไปแล้ว fork นั้นก็ยังมีข้อมูล ต้องเปิด ticket ให้ GitHub Support ลบ cached view ให้

ถ้า repo นี้ไม่จำเป็นต้อง public จริง ๆ ปรับเป็น private ไปเลยจะเร็วและชัวร์กว่า

## 5. กันไม่ให้เกิดซ้ำ

- เปิด secret scanning กับ push protection ใน repo settings ของ GitHub ใช้ฟรีกับ repo public ตัวนี้จะบล็อกตั้งแต่ตอน push
- ใส่ pre-commit hook ด้วย gitleaks หรือ trufflehog
- แยก secret ออกจากไฟล์ที่ commit ให้หมด dev ใช้ `dotnet user-secrets` หรือ `.env` ที่อยู่ใน `.gitignore` ส่วน production ใช้ environment variable หรือ Key Vault
- เหลือ `appsettings.Example.json` ไว้เป็น template ที่ใส่ค่าหลอก แล้วเอาตัวจริงออกจาก repo

## 6. บอกทีม

แจ้ง lead กับทีม security ไปตรง ๆ เรื่องนี้เกิดกับทุกคน ที่แย่กว่าคือเงียบไว้แล้วมีคนมาเจอทีหลัง

ถ้าบอก stack ที่ใช้ (SQL Server, PostgreSQL, Azure, AWS) เดี๋ยวช่วยดูให้ละเอียดได้ว่าต้องเช็ก log ตรงไหนบ้างครับ
