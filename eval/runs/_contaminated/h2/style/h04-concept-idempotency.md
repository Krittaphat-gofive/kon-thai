idempotency คือการออกแบบให้เรียก API เดิมซ้ำกี่ครั้งก็ตาม ผลลัพธ์ในระบบเท่ากับเรียกครั้งเดียวครับ

จุดที่คนเข้าใจผิดบ่อยคือคิดว่า idempotent แปลว่า response ต้องเหมือนเดิมเป๊ะ จริง ๆ แล้วสิ่งที่ต้องเหมือนเดิมคือ state ของระบบ ส่วน response ต่างได้ เช่น ครั้งแรกคืน `201 Created` ครั้งที่สองคืน `200 OK` พร้อมข้อมูลเดิม แบบนี้ยังถือว่า idempotent

ตามสเปก HTTP method พวก GET, PUT, DELETE, HEAD เป็น idempotent โดยธรรมชาติ ส่วน POST ไม่ใช่ ซึ่งงานสร้าง transaction ส่วนใหญ่ก็เป็น POST พอดี เลยต้องมาทำ idempotency เพิ่มเอง

## ทำไมระบบ payroll ถึงต้องสนเป็นพิเศษ

เพราะเป็นงานที่ย้อนกลับไม่ได้ ถ้าโอนเงินซ้ำรอบหนึ่ง เงินออกจากบัญชีบริษัทไปจริง แล้วการตามเก็บคืนจากพนักงานไม่ใช่เรื่อง technical อีกต่อไป กลายเป็นเรื่อง HR กฎหมายแรงงาน แล้วก็มีภาษีหัก ณ ที่จ่ายกับประกันสังคมที่ยื่นผิดตามมาอีก ต่างจากระบบทั่วไปที่สร้าง record ซ้ำแล้วลบทิ้งได้

ช่องทางที่ทำให้เกิดการเรียกซ้ำ มีเยอะกว่าที่คิด
- timeout แล้ว client retry อันนี้อันตรายสุด เพราะ timeout ไม่ได้แปลว่าไม่สำเร็จ request อาจไปถึง server ทำงานเสร็จแล้ว แต่ response หายระหว่างทาง ฝั่ง client แยกสองกรณีนี้ไม่ออกเลย
- ผู้ใช้กดปุ่ม "ประมวลผลรอบจ่าย" รัว ๆ ตอนหน้าจอค้าง
- scheduler หรือ background job ยิงซ้ำตอน pod restart กลางทาง
- message queue ที่การันตีแบบ at-least-once ส่ง message เดิมมาสองรอบ
- webhook callback จากธนาคารที่ส่งซ้ำเมื่อไม่ได้รับ ack

เพราะ retry เลี่ยงไม่ได้ ทางที่เหลือคือทำให้ retry แล้วไม่เกิดผลซ้ำ

## วิธีทำจริง

ใช้สองชั้นคู่กัน ชั้นแรกคือ idempotency key ชั้นที่สองคือ unique constraint ที่ DB

**ชั้นที่ 1: Idempotency-Key header**

ให้ client ส่ง UUID มาใน header ต่อ 1 business operation ไม่ใช่ต่อ 1 HTTP request จุดนี้สำคัญมาก เวลา retry ต้องส่ง key ตัวเดิม ถ้า generate ใหม่ทุกครั้งก็ไม่มีความหมาย

ฝั่ง server เก็บตารางประมาณนี้

```sql
CREATE TABLE idempotency_keys (
    key           VARCHAR(64) PRIMARY KEY,
    request_hash  VARCHAR(64) NOT NULL,
    status        VARCHAR(20) NOT NULL,  -- in_progress | completed
    status_code   INT NULL,
    response_body JSONB NULL,
    created_at    TIMESTAMPTZ NOT NULL,
    expires_at    TIMESTAMPTZ NOT NULL
);
```

flow คือพอ request เข้ามา ให้ `INSERT` key พร้อม status `in_progress` ก่อนเลย
- insert ผ่าน: ทำงานจริงต่อ เสร็จแล้ว update เป็น `completed` พร้อมเก็บ response ไว้
- insert ชน primary key แล้วแถวนั้น `completed`: คืน response ที่เก็บไว้ ไม่ต้องทำงานซ้ำ
- insert ชน แล้วแถวนั้นยัง `in_progress`: แปลว่ามี request คู่แฝดกำลังทำอยู่ คืน `409 Conflict` ให้ client รอแล้ว retry ทีหลัง

ถ้าทำได้ ให้ insert/update ตารางนี้อยู่ใน transaction เดียวกับการเขียนข้อมูล payroll จะได้ atomic ถ้าแยก DB กันต้องคิดเรื่อง outbox เพิ่ม

**ชั้นที่ 2: unique constraint ตาม natural key**

ชั้นนี้ไว้วางใจได้กว่า เพราะไม่ต้องพึ่งว่า client ส่ง key มาถูกต้อง

```sql
ALTER TABLE payslip
  ADD CONSTRAINT uq_payslip UNIQUE (payroll_period_id, employee_id);

ALTER TABLE payment_instruction
  ADD CONSTRAINT uq_payment UNIQUE (payrun_id, employee_id, payment_type);
```

กฎทางธุรกิจคือพนักงาน 1 คน ต่อ 1 งวด ได้ payslip ใบเดียว เขียนกฎนั้นลงไปที่ DB ตรง ๆ เลย ต่อให้โค้ดพลาด bug ที่ application layer ก็ยังชนกำแพงนี้

**ขาส่งธนาคาร** ตอนยิง payment file หรือเรียก API ธนาคาร ให้แนบ end-to-end reference ที่ unique ต่อรายการและคำนวณจากข้อมูลเดิมได้ เช่น `{payrun_id}-{employee_id}` ธนาคารส่วนใหญ่ dedupe จาก reference นี้ให้อยู่แล้ว ส่งซ้ำก็ไม่โอนซ้ำ

## จุดที่พลาดกันบ่อย

**key เดิมแต่ payload ต่าง** ต้อง reject ด้วย `422` ไม่ใช่คืน response เดิมเฉย ๆ สมมติรอบแรกส่งโบนัส 10,000 แล้วแก้เป็น 50,000 ส่งซ้ำด้วย key เดิม ถ้าคืน response เก่าไป ฝั่ง client จะเข้าใจว่าแก้สำเร็จแล้ว ทั้งที่ยอดยังเป็น 10,000 เลยต้องเก็บ `request_hash` ไว้เทียบด้วย

**TTL สั้นไป** ระบบทั่วไปเก็บ key ไว้ 24 ชั่วโมงก็พอ แต่ payroll รอบจ่ายมันห่างกันเป็นเดือน แล้วมีการ rerun ย้อนหลังตอนปิดงบด้วย แนะนำเก็บยาวหน่อย อย่างน้อยครอบรอบ audit

**DELETE ที่คืน 404 รอบสอง** ตามสเปกถือว่า idempotent เพราะ state ไม่เปลี่ยน แต่ client เห็น error แล้วงง คืน `204` ทุกครั้งจะใช้งานง่ายกว่า

ถ้าบอกมาว่าใช้ stack อะไรกับฝั่ง client เป็น web หรือ batch job เดี๋ยวผมช่วยร่าง middleware กับ schema ให้ตรงกับงานจริงได้ครับ
