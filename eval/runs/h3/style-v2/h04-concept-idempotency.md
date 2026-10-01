idempotent แปลว่าเรียก API เดิมซ้ำกี่ครั้ง ผลต่อ state ของระบบก็เท่ากับเรียกครั้งเดียวครับ

จุดที่คนมักเข้าใจผิดคือมันพูดถึง state ไม่ใช่ response ครั้งที่สองจะได้ status code ต่างออกไปก็ได้ (เช่น 200 แทน 201) แต่ห้ามมี side effect เพิ่ม

ตาม HTTP spec นับ GET, PUT, DELETE เป็น idempotent ส่วน POST ไม่ใช่ แต่ spec บอกแค่ว่าควรเป็นแบบนั้น คนเขียน endpoint ต้องทำให้จริงเอง `PUT /balance` ที่ข้างในเขียนว่า `balance += amount` ก็ไม่ idempotent ถึงจะใช้ PUT

## ทำไมระบบจ่ายเงินเดือนต้องสน

เงินที่โอนออกไปแล้วเรียกคืนยาก ต่างจากแถวซ้ำใน report ที่ลบทิ้งได้ พอผิดทีก็ลามไปยอดภาษีหัก ณ ที่จ่าย ประกันสังคม ยอดสะสมทั้งปี แล้วยังต้องแจ้งพนักงานกับทำเอกสารแก้อีก

ปัญหาที่หนักกว่าคือฝั่ง client ไม่มีทางรู้ว่า timeout แปลว่าอะไร request ไปไม่ถึง server หรือถึงแล้วประมวลผลเสร็จแต่ response หายกลางทาง สองกรณีนี้หน้าตาเหมือนกันเป๊ะ ทางเลือกมีแค่ retry กับปล่อยผ่าน ถ้า API ไม่ idempotent ก็ผิดทั้งคู่ retry แล้วจ่ายซ้ำ ไม่ retry แล้วพนักงานไม่ได้เงิน

จุดที่เกิดซ้ำได้จริงในระบบ payroll
- HR กดปุ่ม "ประมวลผลรอบจ่าย" สองครั้งเพราะหน้าจอหมุนนาน
- job รัน batch ล่มกลางคัน แล้วมีคนสั่งรันใหม่ทั้งรอบ
- queue ที่การันตีแบบ at-least-once ส่ง message เดิมมาซ้ำตอน consumer ไม่ได้ ack ทัน
- webhook จากธนาคารที่ยิงซ้ำเมื่อไม่ได้รับ 200 ภายในเวลาที่กำหนด

## ทำยังไงให้ idempotent

**1. ให้ DB เป็นคนกันด้วย unique constraint** วิธีที่ได้ผลที่สุดและเขียนโค้ดน้อยสุด ตั้ง unique index บน `(payroll_run_id, employee_id)` ของตาราง payslip ยิงซ้ำกี่รอบก็ชน constraint แล้วจับ error นั้นมาคืน payslip เดิมไป

**2. Idempotency-Key สำหรับ POST ที่ไม่มี natural key** client gen UUID ส่งมาใน header แล้ว server เก็บตารางแบบนี้

```
idempotency_keys (key PK, request_hash, status, response_body, created_at)
```

flow คือ insert key ด้วย status `in_progress` ก่อนทำงานจริง ถ้า insert ชน unique แปลว่าเคยรับ request นี้ไปแล้ว เช็กต่อว่า status เป็นอะไร ถ้า `done` ก็คืน `response_body` ที่เก็บไว้ ถ้ายัง `in_progress` คืน 409 ให้มา retry ใหม่ทีหลัง

อย่าลืมเก็บ `request_hash` ด้วย ถ้า key เดิมแต่ body ไม่เหมือนเดิม แปลว่า client ใช้ key ผิด ให้ตอบ 422 ไปเลย ดีกว่าปล่อยให้ได้ response ของ request อื่น

**3. เปลี่ยน status แบบมีเงื่อนไข** รอบจ่ายเงินเดือนมี state ชัดอยู่แล้ว draft → calculated → approved → paid เวลาเปลี่ยนให้เขียนเป็น

```sql
UPDATE payroll_run SET status = 'paid' WHERE id = @id AND status = 'approved'
```

แล้วดู affected rows ถ้าได้ 0 แปลว่ามีคนทำไปก่อนแล้ว ไม่ต้องสั่งโอนซ้ำ

**4. เขียนเป็น set ไม่ใช่ increment** `SET net_pay = 50000` ปลอดภัยกว่า `SET net_pay = net_pay + 5000` เสมอ ตรงไหนเลี่ยง increment ได้ให้เลี่ยง

## ข้อควรระวัง

- idempotency key ต้องผูกกับเจตนาครั้งนั้นของผู้ใช้ ถ้า client gen key ใหม่ทุกครั้งที่ retry ก็ไม่ได้ช่วยอะไร ปกติ gen ตอนเปิดฟอร์มหรือตอนกดปุ่มครั้งแรก แล้วใช้ตัวเดิมตลอดจนกว่าจะสำเร็จ
- TTL ของ key ทั่วไปตั้ง 24 ชั่วโมงก็พอ แต่ payroll ควรเก็บยาวกว่านั้น อย่างน้อยจนปิดรอบจ่ายและกระทบยอดเรียบร้อย
- ถ้าเราไปเรียก API ธนาคารหรือ payment gateway ต่อ ต้องส่ง reference number ที่ปลายทางใช้ dedupe ด้วย ไม่งั้นเรา idempotent แค่ฝั่งตัวเอง แต่คำสั่งโอนยังซ้ำได้อยู่ดี
