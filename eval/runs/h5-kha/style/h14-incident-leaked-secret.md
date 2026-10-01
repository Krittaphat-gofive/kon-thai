เปลี่ยนรหัสผ่าน database ก่อนเลยค่ะ อย่างอื่นรอได้ แต่อันนี้รอไม่ได้

ที่ต้องเข้าใจก่อนคือ secret ที่ขึ้น public repo แล้วถือว่ารั่วถาวร ไม่ว่าจะลบ commit สำเร็จแค่ไหน มี bot ที่ scan GitHub แบบ realtime เพื่อเก็บ credential อยู่จำนวนมาก ผ่านมาหนึ่งวันแปลว่าโดนเก็บไปแล้วเกือบแน่นอน การลบ history เป็นแค่การทำความสะอาด ไม่ใช่การแก้ปัญหา

## 1. ตัดการเข้าถึงทันที

- เปลี่ยนรหัสผ่านของ user ตัวนั้น ถ้าเป็นไปได้ให้ลบ user เดิมทิ้งแล้วสร้างใหม่ด้วยชื่ออื่น
- ถ้ารหัสผ่านนี้ใช้ซ้ำกับระบบอื่น เปลี่ยนที่นั่นด้วยทั้งหมด
- ปิด public access ของ database ถ้ายังเปิดอยู่ จำกัดด้วย IP allowlist หรือ security group ให้เหลือเฉพาะ IP ของ server ที่ต้องใช้จริง
- ไปอัปเดต connection string ใหม่ในที่ที่ app ใช้งาน (secret manager, environment variable ของ CI/CD, server config)

## 2. เช็กว่ามีใครเข้ามาแล้วหรือยัง

ส่วนนี้สำคัญพอกับการเปลี่ยนรหัสผ่าน เพราะถ้ามีคนเข้าไปแล้ว การเปลี่ยนรหัสผ่านไม่ได้ไล่เขาออก

- ดู connection log หรือ audit log ของ database ย้อนไปตั้งแต่เวลาที่ commit ขึ้นไป หา IP ที่ไม่คุ้น
- เช็กว่ามี user, role หรือ scheduled job ที่ถูกสร้างเพิ่มมาไหม เป็นวิธีฝังตัวที่เจอบ่อย
- ดู metric การใช้งาน เช่น network egress ผิดปกติ หรือ query ที่อ่านข้อมูลทั้งตาราง
- ถ้าใน database มีข้อมูลส่วนบุคคล แจ้งคนที่ดูแลเรื่อง compliance ของบริษัทด้วย เพราะ PDPA มีกรอบเวลาแจ้งเหตุ 72 ชั่วโมงนับจากทราบเหตุ

## 3. ล้าง git history

ทำหลังจากสองข้อบนเสร็จแล้ว เครื่องมือที่แนะนำคือ `git filter-repo`

```
pip install git-filter-repo
git filter-repo --path path/to/config-file --invert-paths
```

ถ้า secret อยู่ในไฟล์ที่ยังต้องใช้ ให้แทนที่เฉพาะข้อความแทน โดยสร้างไฟล์ `replacements.txt` ที่มีบรรทัด `รหัสผ่านเดิม==>REMOVED` แล้วรัน

```
git filter-repo --replace-text replacements.txt
```

จากนั้น force push ขึ้นไป แล้วบอกทุกคนในทีมให้ clone ใหม่ อย่า merge ของเก่าเข้ามา ไม่งั้น commit เดิมจะกลับขึ้นไป

## 4. จัดการส่วนที่ GitHub เก็บไว้

force push ไม่ได้ลบ commit เก่าออกจาก GitHub ทันที commit นั้นยังเปิดดูได้ถ้ารู้ SHA และยังค้างอยู่ใน cache ของ pull request กับ fork

- เปิด ticket กับ GitHub Support ขอให้ลบ cached view ของ commit ที่ระบุ SHA ไว้ อันนี้ต้องให้ GitHub ทำให้ ทำเองไม่ได้
- เช็กว่ามี fork ของ repo ไหม ถ้ามี fork อยู่ commit จะยังอยู่ใน fork นั้น ต้องติดต่อเจ้าของให้ลบ
- ลองค้นรหัสผ่านนั้นใน GitHub code search และ Google ดูว่ามี mirror ที่อื่นไหม

ถ้า repo นี้เพิ่งสร้าง ยังไม่มี issue, star หรือ fork ที่สำคัญ การลบ repo ทิ้งแล้ว push ขึ้นใหม่จบกว่าและเร็วกว่าการไล่ทำทั้งหมดข้างบน

## 5. กันไม่ให้เกิดซ้ำ

- เปิด GitHub Secret Scanning กับ Push Protection ที่ repo setting ตัวนี้จะบล็อก push ที่มี credential ตั้งแต่ตอน push
- ใส่ pre-commit hook ด้วย `gitleaks` หรือ `detect-secrets`
- ย้าย connection string ไปอยู่ใน environment variable หรือ secret manager แล้วเก็บแค่ไฟล์ตัวอย่างอย่าง `.env.example` ที่ไม่มีค่าจริงไว้ใน repo
- เพิ่มไฟล์ config ที่มี secret เข้า `.gitignore`

ลำดับที่ควรทำตอนนี้คือข้อ 1 ให้เสร็จก่อนภายในชั่วโมงนี้ แล้วค่อยทำข้อ 2 ส่วนข้อ 3 ถึง 5 ทำตามสบายได้ค่ะ
