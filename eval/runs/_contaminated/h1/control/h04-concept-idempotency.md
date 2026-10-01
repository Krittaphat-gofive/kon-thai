idempotency คือเรียก API เดิมซ้ำกี่ครั้ง ผลลัพธ์ที่ค้างอยู่ในระบบก็เหมือนเรียกครั้งเดียวครับ

จุดที่คนสับสนบ่อยคือ idempotent ไม่ได้แปลว่า response ต้องเหมือนเดิมเป๊ะ ลบ resource ครั้งแรกได้ 204 ครั้งที่สองได้ 404 แบบนี้ยังถือว่า idempotent เพราะสถานะปลายทางเหมือนกัน คือ resource นั้นไม่อยู่แล้ว ส่วนที่ต้องเหมือนคือ side effect ไม่ใช่ status code

ตามสเปก HTTP นั้น GET, PUT, DELETE, HEAD เป็น idempotent ส่วน POST ไม่ใช่ ซึ่งงานจ่ายเงินส่วนใหญ่ก็เป็น POST พอดี

## ทำไม payroll ต้องสนเป็นพิเศษ

เพราะ "ทำซ้ำ" ในระบบอื่นแก้ได้ แต่ในระบบเงินเดือนแก้ไม่ได้ง่าย ๆ

- โอนเงินซ้ำแล้วต้องไปขอพนักงานโอนคืน ซึ่งเป็นเรื่องระหว่างคนกับคน ไม่ใช่แค่ลบ row
- ยอดที่คำนวณซ้ำลามไปถึงภาษีหัก ณ ที่จ่าย ประกันสังคม กองทุนสำรองเลี้ยงชีพ และรายงานที่ส่งหน่วยงานรัฐ ผิดจุดเดียวแก้ตามหลายที่
- รอบจ่ายมีกำหนดตายตัว เจอปัญหาวันจ่ายเงินคือมีเวลาแก้ไม่กี่ชั่วโมง

แล้วโอกาสที่จะเกิดซ้ำก็เยอะกว่าที่คิด

- client ยิง request ไปแล้ว timeout ตอน 30 วินาที แต่ server ประมวลผลเสร็จไปแล้ว client ไม่รู้เลยยิงใหม่
- HR กดปุ่ม "ประมวลผลเงินเดือน" ซ้ำเพราะหน้าจอหมุนนาน
- job ใน queue อย่าง Hangfire หรือ Service Bus retry ให้อัตโนมัติเมื่อ exception
- ไฟล์โอนเงินที่ส่งเข้าธนาคาร ถ้า upload ซ้ำโดยไม่มีเลขอ้างอิงกำกับ ธนาคารก็โอนให้สองรอบ
- webhook ยืนยันผลจากธนาคารเองก็ส่งซ้ำเป็นปกติ ตามหลัก at-least-once

สรุปคือ timeout ไม่เท่ากับไม่สำเร็จ ตราบใดที่ client แยกสองกรณีนี้ไม่ออก server ต้องรับผิดชอบเรื่องซ้ำเอง

## ทำยังไงให้ idempotent จริง

ทำสามชั้น ชั้นไหนขาดไม่ได้

**1. Idempotency-Key ที่ระดับ API**

ให้ client สร้าง key (UUID) ต่อหนึ่งเจตนาการเรียก แล้วส่งมาใน header ฝั่ง server มีตารางเก็บ key

```sql
create table idempotency_keys (
  key             varchar(64) primary key,
  request_hash    varchar(64) not null,
  status          varchar(20) not null,  -- in_progress / completed
  response_body   text,
  created_at      timestamptz not null
);
```

ขั้นตอนคือ insert key ด้วย status `in_progress` ก่อนทำงานจริง ถ้า insert ชน primary key แปลว่ามีคนทำอยู่หรือทำเสร็จไปแล้ว ให้คืน response เดิมที่เก็บไว้ หรือคืน 409 ถ้ายังทำไม่เสร็จ สำคัญคือ insert ต้องเกิดก่อนเริ่มงาน ไม่ใช่หลังทำเสร็จ ไม่งั้น request สองตัวที่มาพร้อมกันจะผ่านทั้งคู่

ส่วน `request_hash` ไว้กัน client ส่ง key เดิมแต่ payload ต่าง ถ้าไม่ตรงให้ตอบ 422 ไปเลย ดีกว่าเงียบ ๆ แล้วคืนผลของ request เก่า

**2. unique constraint ที่ระดับ domain**

ชั้นนี้คือตาข่ายกันพลาดที่เชื่อถือได้ที่สุด เพราะฐานข้อมูลบังคับให้เอง

```sql
alter table payslips
  add constraint uq_payslip unique (payroll_period_id, employee_id);

alter table payment_transactions
  add constraint uq_payment unique (payslip_id, attempt_reference);
```

ต่อให้ logic ชั้นบนรั่ว สุดท้ายก็ insert รายการจ่ายซ้ำในงวดเดียวกันไม่ได้

**3. state machine ของรอบจ่าย**

ให้ payroll period เดินทางเดียวคือ `draft` → `calculated` → `approved` → `paid` แล้ว update ด้วยเงื่อนไขสถานะเดิมเสมอ

```sql
update payroll_periods
set status = 'paid', paid_at = now()
where id = @id and status = 'approved';
```

ถ้า rows affected เป็น 0 แปลว่ามีคนทำไปแล้ว ไม่ใช่ error ให้ตอบกลับไปว่าสำเร็จแล้วตั้งแต่รอบก่อน

## จุดที่พลาดบ่อย

- เช็กก่อนแล้วค่อย insert แบบ `if (!exists) insert` ตรงนี้มีช่องว่างระหว่างสองคำสั่งเสมอ ต้องพึ่ง unique constraint หรือ `insert ... on conflict do nothing` แทน
- ให้ server เป็นคนสร้าง idempotency key เอง ซึ่งไม่ช่วยอะไรเลย เพราะ retry แต่ละครั้งก็ได้ key ใหม่ key ต้องมาจาก client เท่านั้น
- ลืม TTL ของตาราง key ปล่อยไว้สักพักก็บวมจนเป็นภาระ ส่วนใหญ่ตั้งไว้ 24 ถึง 72 ชั่วโมงพอ ครอบคลุมช่วง retry จริง
- idempotent แต่ไม่ atomic คือกัน request ซ้ำได้ แต่ตัวงานข้างในทำครึ่งทางแล้วพัง เหลือ payslip ที่สร้างไปครึ่งหนึ่ง ต้องห่อด้วย transaction ให้จบในก้อนเดียว

ถ้าบอกได้ว่าตอนนี้ระบบใช้ stack อะไรและตรงไหนที่เจอปัญหาซ้ำ เดี๋ยวผมช่วยดูว่าควรลงชั้นไหนก่อนครับ
