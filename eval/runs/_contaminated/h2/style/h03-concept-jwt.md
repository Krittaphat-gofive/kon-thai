เหตุผลหลักคือ JWT เพิกถอนยากครับ เลยต้องแยกเป็นตัวอายุสั้นที่ใช้บ่อย กับตัวอายุยาวที่ควบคุมได้

## access token

- JWT ที่แนบไปกับทุก request ใน header `Authorization: Bearer ...`
- server แค่ verify signature กับ `exp` ก็รู้ว่าใครเรียก ไม่ต้อง query DB
- อายุสั้น ปกติ 5 ถึง 15 นาที

## refresh token

- ใช้อย่างเดียวคือยิงไป endpoint `/auth/refresh` เพื่อขอ access token ใบใหม่
- อายุยาว หลักวันถึงหลักเดือน
- เก็บไว้ฝั่ง server ด้วย (ตารางใน DB หรือ Redis) ไม่จำเป็นต้องเป็น JWT ด้วยซ้ำ random string ก็พอ

## ทำไมใช้ตัวเดียวไม่ได้

ลองคิดจากสองทางเลือก

**ถ้ามีแค่ access token อายุยาว** พอ token หลุด เช่น ติด log, โดนดูดจาก localStorage, หรือ user กด logout คนร้ายก็ยังใช้ token ใบนั้นได้จนกว่าจะหมดอายุ จะ revoke ก็ต้องเช็ก blacklist ใน DB ทุก request ซึ่งทำให้ข้อดีของ JWT ที่ไม่ต้องแตะ DB หายไปหมด

**ถ้ามีแค่ access token อายุสั้น** ปลอดภัยขึ้น แต่ user ต้อง login ใหม่ทุก 15 นาที ไม่มีใครทนใช้

refresh token คือทางสายกลาง เรายอมแตะ DB แค่ตอน refresh ซึ่งเกิดทุก 15 นาทีครั้ง ไม่ใช่ทุก request พอ user กด logout หรือเราตรวจเจอว่าบัญชีโดนเจาะ ก็ลบ refresh token ทิ้ง คนร้ายใช้ access token ที่มีอยู่ได้อีกไม่เกิน 15 นาทีแล้วก็หมดสิทธิ์

## flow คร่าว ๆ

1. login สำเร็จ server ส่ง access token กับ refresh token กลับมา
2. client เรียก API ด้วย access token ไปเรื่อย ๆ
3. เจอ 401 เพราะ token หมดอายุ client ยิง `/auth/refresh` พร้อม refresh token
4. server เช็กว่า refresh token ใบนี้ยังอยู่ใน DB และไม่ถูกเพิกถอน แล้วออก access token ใบใหม่ให้
5. client ยิง request เดิมซ้ำ user ไม่รู้สึกอะไรเลย

## จุดที่มักพลาด

- **ที่เก็บ** อย่าเก็บ refresh token ใน localStorage เพราะ JavaScript อ่านได้ ถ้าโดน XSS คือจบ ให้ใช้ httpOnly cookie กับ `SameSite=Strict` ส่วน access token เก็บใน memory ของ app ได้ เพราะอายุสั้นอยู่แล้ว
- **rotation** ทุกครั้งที่ refresh ให้ออก refresh token ใบใหม่และยกเลิกใบเก่า อย่าให้ใบเดิมใช้ซ้ำได้ตลอดอายุ
- **reuse detection** ถ้ามีคนเอา refresh token ใบที่ยกเลิกไปแล้วมาใช้ แปลว่า token รั่วเกือบแน่นอน ให้ล้าง session ทั้งหมดของ user คนนั้นทิ้งแล้วบังคับ login ใหม่
- **อย่าใส่ข้อมูลลับใน payload** JWT แค่ encode base64 ไม่ได้เข้ารหัส ใครก็เปิดอ่านได้
- **จัดการ race condition ฝั่ง client** ถ้ามี 5 request เด้ง 401 พร้อมกัน อย่าให้ยิง refresh พร้อมกัน 5 ครั้ง ให้ทำ queue รอ refresh ตัวแรกเสร็จแล้วค่อยปล่อยทั้งหมดไปต่อ จุดนี้พังบ่อยตอน rotation เปิดอยู่

ถ้าบอกมาว่าใช้ stack อะไร เดี๋ยวผมเขียนตัวอย่าง interceptor กับฝั่ง API ให้ดูครับ
