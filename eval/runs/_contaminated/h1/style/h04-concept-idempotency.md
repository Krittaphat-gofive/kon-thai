สรุปสั้น ๆ idempotency คือการที่เรียก API เดิมซ้ำกี่ครั้ง ผลลัพธ์ในระบบก็เท่ากับเรียกครั้งเดียวครับ

ตัวสำคัญคือ "ผลต่อ state" ไม่ใช่ response ที่ต้องเหมือนกันเป๊ะ เทียบง่าย ๆ กดปุ่มลิฟต์ชั้น 5 ซ้ำสิบครั้ง ลิฟต์ก็มาชั้น 5 รอบเดียว ต่างจาก "เพิ่มเงินเข้าบัญชี 1000 บาท" ที่เรียกสิบครั้งแล้วได้หมื่น

ตาม HTTP spec นั้น GET, PUT, DELETE เป็น idempotent ส่วน POST ไม่ใช่ แล้ว endpoint ที่สั่งจ่ายเงินส่วนใหญ่ก็เป็น POST พอดี

## ทำไม payroll ต้องสนใจเป็นพิเศษ

เรื่องแรกคือ network ไม่เคยบอกความจริงทั้งหมด พอ client ยิง `POST /payroll/runs` แล้ว timeout เราแยกไม่ออกเลยว่า

1. request ไปไม่ถึง server
2. server ทำงานจบแล้ว แต่ response หายกลางทาง

สองเคสนี้หน้าตาเหมือนกันหมดที่ฝั่ง client ถ้า retry ไปโดนเคสที่สอง ก็คือจ่ายเงินซ้ำ

ที่เจอกันจริง ๆ ในระบบเงินเดือน
- HR กดปุ่มประมวลผล หน้าค้างไปสิบวินาที เลยกดซ้ำ
- scheduler รันรอบเดือนซ้ำ เพราะ pod restart กลางทาง
- message queue ส่ง message เดิมซ้ำ (at-least-once delivery เป็นค่า default ของคิวส่วนใหญ่)
- retry policy ของ HTTP client ยิงซ้ำให้เองโดยที่เราไม่ได้สั่ง

เรื่องที่สองคือต้นทุนความผิดพลาดสองฝั่งไม่เท่ากัน จ่ายขาด พนักงานโทรมาแจ้งแล้วโอนเพิ่มได้ในวันเดียว แต่จ่ายซ้ำคือเงินออกจากบัญชีบริษัทไปแล้ว ต้องไล่ขอคืนทีละคน แถมยอดภาษีหัก ณ ที่จ่าย ยอดประกันสังคม และ ยอดที่ส่งเข้าธนาคารเพี้ยนตามไปหมด บางเคสต้องยื่นแก้ ภ.ง.ด.1 ย้อนหลัง

## วิธีทำจริง

ให้ client สร้าง key หนึ่งตัวต่อหนึ่งเจตนา แล้วส่งมากับ request ทุกครั้งที่ retry โดยใช้ key เดิม

```http
POST /api/payroll/runs
Idempotency-Key: 8f14e45f-ea8d-4c1a-9b2e-7d3f1a0b5c62

{ "companyId": 42, "period": "2026-09" }
```

ฝั่ง server ทำตามลำดับนี้

1. INSERT key ลงตาราง idempotency ที่มี unique constraint ก่อน แล้วค่อยทำงานจริง
2. ถ้า insert ชนเพราะซ้ำ แปลว่ามีคนทำไปแล้ว ให้ไปอ่าน response เดิมมาตอบแทน
3. ทำงานเสร็จแล้วค่อยอัปเดต response กลับเข้าแถวเดิม

```sql
CREATE TABLE idempotency_keys (
    key           VARCHAR(64)  PRIMARY KEY,
    request_hash  VARCHAR(64)  NOT NULL,
    status        VARCHAR(20)  NOT NULL,   -- in_progress | completed
    response_code INT          NULL,
    response_body TEXT         NULL,
    expires_at    TIMESTAMP    NOT NULL
);
```

## จุดที่พลาดกันบ่อย

| พลาดตรงไหน | ผลที่ตามมา |
|---|---|
| เก็บ key หลังทำงานเสร็จ | request ที่สองเข้ามาระหว่างนั้น หลุดทั้งคู่ |
| ใช้ SELECT แล้วค่อย INSERT | มีช่องว่างให้ race ต้องให้ unique constraint ของ database ตัดสิน |
| ไม่เก็บ request_hash | ใช้ key เดิมแต่ payload คนละตัว ควรตอบ 422 ไม่ใช่คืนผลเก่าเงียบ ๆ |
| ไม่มีสถานะ in_progress | request ที่สองมาตอนแรกยังไม่จบ ควรตอบ 409 ให้ไป retry ใหม่ |
| server สร้าง key เอง | ไม่ช่วยอะไรเลย เพราะ retry แต่ละครั้งจะได้ key ใหม่ |
| TTL สั้นไป | payroll ควรเก็บอย่างน้อยจนจบรอบ ไม่ใช่ 24 ชั่วโมงแบบ API ทั่วไป |

## อีกชั้นที่ผมว่าสำคัญกว่า key ด้วยซ้ำ

วาง unique constraint บน `(company_id, period, employee_id)` ในตาราง payslip ไปเลย ต่อให้ logic ชั้นบนพลาด หรือมีคนยิงเข้ามาทาง admin tool ทาง import file หรือทาง script ที่ลืม key database ก็ยัง insert ซ้ำไม่ได้อยู่ดี Idempotency-Key กันได้แค่ทางเดียวคือทาง API แต่ natural key กันได้ทุกทางเข้า

ส่วน API ของธนาคารที่เราคุมไม่ได้ ถ้าปลายทางไม่รองรับ idempotency key ก็ต้องเปลี่ยนมาเก็บ state ของแต่ละรายการโอนฝั่งเราเอง (pending / submitted / confirmed) แล้วทำ reconciliation เทียบกับ statement ทีหลัง ไม่ควร retry ตรง ๆ เด็ดขาด

ถ้าบอกมาว่าใช้ stack อะไร แล้วส่วนไหนเป็น queue เดี๋ยวช่วยดูให้ว่าควรวาง key ตรงไหนบ้างครับ
