ถือว่ารหัสผ่านรั่วไปแล้วแน่นอนครับ ไม่ต้องรอดูว่ามีใครเจอหรือเปล่า เพราะมี bot ไล่ scan commit ใหม่ ๆ บน GitHub public ตลอดเวลา บางตัวเจอภายในไม่กี่สิบวินาทีหลัง push ผ่านไปหนึ่งวันแปลว่าสายไปนานแล้ว

สิ่งสำคัญที่สุด: **เปลี่ยนรหัสผ่านก่อน อย่าเพิ่งไปลบ commit** คนส่วนใหญ่ทำสลับกัน เสียเวลาไปกับการ rewrite history ครึ่งชั่วโมง ระหว่างนั้นรหัสเดิมยังใช้ login ได้อยู่

## 1. เปลี่ยนรหัส database เดี๋ยวนี้

เปลี่ยนรหัสของ user ที่อยู่ใน connection string นั้น แล้วอัปเดตค่าใหม่ไปที่ระบบที่ใช้งานจริง ถ้า account นั้นใช้ร่วมกันหลายระบบ เปลี่ยนให้ครบทุกที่

ถ้าเปลี่ยนรหัสแล้วมีบริการล่ม ยอมให้ล่มดีกว่าปล่อยให้คนอื่นเข้า DB ได้

## 2. ปิดทางเข้าถึงจากภายนอก

ถ้า database เปิดรับ connection จาก internet ตรง ๆ ให้ปิดทันที

- Azure SQL / RDS: เอา rule ที่เปิด `0.0.0.0/0` ออก เหลือเฉพาะ IP ของ app server หรือ VNet/VPC
- on-prem: เช็ก firewall กับ port forwarding ที่ router

ขั้นนี้สำคัญพอ ๆ กับการเปลี่ยนรหัส เพราะต่อให้รหัสรั่ว ถ้าต่อเข้ามาไม่ได้ก็จบ

## 3. เช็ก log ว่ามีใครเข้ามาแล้วหรือยัง

ไล่ดูตั้งแต่เวลาที่ push commit จนถึงตอนนี้ หา login ที่มาจาก IP ที่ไม่รู้จัก

- SQL Server: `sys.event_log` (Azure SQL), audit log, หรือ Extended Events ถ้าเปิดไว้
- PostgreSQL: log ที่มาจาก `log_connections` ถ้าเปิดไว้
- MySQL: general log หรือ audit plugin
- cloud ทุกเจ้ามี audit log ในพอร์ทัล เปิดดูได้เลย

ดูด้วยว่ามี query แปลก ๆ อย่างการ dump ทั้งตาราง หรือมีข้อมูลหาย มีตารางเพิ่มมาไหม

ถ้าเจอร่องรอยว่ามีคนเข้ามาจริง เรื่องนี้กลายเป็น data breach ไม่ใช่แค่ secret รั่ว ต้องแจ้งทีม security ของบริษัทตาม incident response policy

## 4. ล้างประวัติ Git

ทำหลังจากสามข้อแรกเสร็จ

```bash
pip install git-filter-repo

# ลบทั้งไฟล์ออกจากทุก commit
git filter-repo --path src/appsettings.json --invert-paths

# หรือถ้าอยากเก็บไฟล์ไว้ แทนที่เฉพาะข้อความ
# สร้างไฟล์ secrets.txt ที่มีบรรทัด: MyP@ssw0rd==>REMOVED
git filter-repo --replace-text secrets.txt
```

แล้ว force push

```bash
git push origin --force --all
git push origin --force --tags
```

เรื่องที่ต้องรู้: การ force push ไม่ได้ลบของจาก GitHub จริง ๆ commit เดิมยังค้างเป็น dangling object เปิดดูได้ถ้ารู้ SHA แถม fork กับ pull request ที่อ้างถึง commit นั้นก็ยังเห็นเนื้อหาเดิมอยู่ ต้องเปิด ticket กับ GitHub Support ขอให้ garbage collect และลบ cached view ให้

ถ้า repo ยังเล็กและไม่มีคนอื่นใช้ร่วม ลบ repo ทิ้งแล้ว push ขึ้นใหม่จาก working copy ที่สะอาด จบเร็วกว่าและชัวร์กว่า

ส่วนคนในทีมที่ clone ไปแล้ว บอกให้ clone ใหม่ อย่า pull ทับ ไม่งั้นประวัติเก่ากลับมา

## 5. สแกนหาของที่เหลือ

มีรหัสหลุดหนึ่งที่ มักมีที่อื่นด้วย ลองไล่ทั้ง repo

```bash
gitleaks detect --source . --log-opts="--all"
```

หรือ `trufflehog git file://. --results=verified`

## 6. กันไม่ให้เกิดซ้ำ

- เปิด **secret scanning + push protection** ใน repo settings ของ GitHub ตัวนี้จะบล็อกตั้งแต่ตอน push ฟรีสำหรับ public repo
- ย้าย connection string ไปอยู่ที่ user secrets ตอน dev และ environment variable หรือ Key Vault / Secrets Manager ตอน deploy
- ใส่ `appsettings.Development.json`, `.env`, `*.local.json` ใน `.gitignore`
- ลง pre-commit hook ที่เรียก gitleaks ก่อน commit

## เรื่อง PDPA

ถ้า database นั้นมีข้อมูลส่วนบุคคลของลูกค้าหรือพนักงาน และข้อ 3 พบว่ามีคนเข้ามาจริง ให้แจ้งทีม DPO หรือฝ่ายกฎหมายของบริษัทเลย เพราะกฎหมายกำหนดให้แจ้งสำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคลภายใน 72 ชั่วโมงนับจากทราบเหตุ ส่วนจะเข้าข่ายต้องแจ้งหรือไม่ ปล่อยให้ฝ่ายที่รับผิดชอบเป็นคนตัดสิน อย่าประเมินเอง

ถ้าบอกได้ว่าใช้ database อะไร host ที่ไหน เดี๋ยวผมช่วยดูให้ละเอียดขึ้นว่าต้องไปหา audit log ตรงไหนครับ
