เหตุผลหลักข้อเดียวคือ JWT ที่ออกไปแล้ว เรียกคืนกลางคันไม่ได้ครับ ที่เหลือคือการออกแบบรอบ ๆ ข้อจำกัดนี้

## ปัญหาที่ทำให้ต้องมีสองตัว

access token เป็น JWT ที่ server เซ็นลายเซ็นไว้ พอ client แนบมากับ request server แค่ verify signature ก็รู้แล้วว่าใครเป็นใคร สิทธิ์อะไรบ้าง ไม่ต้องแตะ database เลย เร็วและ scale ง่าย

แต่ข้อดีข้อนี้แลกมาด้วยข้อเสีย คือถ้า token หลุดไปอยู่กับคนอื่น server ไม่มีทางรู้ และบล็อกไม่ได้จนกว่าจะหมดอายุ

ทางแก้คือตั้งอายุให้สั้น 5-15 นาที ความเสียหายจะจำกัดอยู่แค่ช่วงนั้น แต่ถ้าให้ user login ใหม่ทุก 15 นาทีก็ไม่มีใครทน เลยต้องมี refresh token มารับหน้าที่ต่ออายุให้เงียบ ๆ อยู่เบื้องหลัง

## เปรียบเทียบ

| | access token | refresh token |
|---|---|---|
| หน้าที่ | พิสูจน์ตัวตนในทุก request | ขอ access token ใบใหม่ |
| อายุ | 5-15 นาที | 7-30 วัน |
| ส่งไปที่ไหน | ทุก endpoint | เฉพาะ `/auth/refresh` |
| server เก็บไว้ไหม | ไม่เก็บ ตรวจจาก signature | เก็บใน db หรือ redis |
| ยกเลิกกลางคัน | ไม่ได้ | ได้ ลบออกจาก db |
| รูปแบบ | JWT | JWT หรือ random string ก็ได้ |

สองแถวล่างคือหัวใจ refresh token ใช้นาน ๆ ครั้ง เลยยอมแลกกับการ query db ได้ ส่วน access token ที่วิ่งทุก request ต้องเร็วที่สุด ห้ามแตะ db

## flow จริง ๆ

1. login สำเร็จ server ออกให้ทั้งคู่
2. client ยิง API แนบ access token มาใน header `Authorization: Bearer ...`
3. พอหมดอายุ server ตอบ 401
4. client ยิง `/auth/refresh` พร้อม refresh token
5. server เช็กว่า refresh token ยังอยู่ใน db และยังไม่หมดอายุ แล้วออก access token ใบใหม่
6. client ยิง request เดิมซ้ำ user ไม่รู้สึกอะไรเลย

## เก็บไว้ที่ไหน

- access token: เก็บในตัวแปร memory ของฝั่ง front เช่นใน store อย่าเอาไปไว้ localStorage เพราะ XSS อ่านได้หมด
- refresh token: วางใน cookie ที่ตั้ง `httpOnly` + `Secure` + `SameSite` จะดีที่สุด เพราะ JavaScript อ่านไม่ได้ และตั้ง `path=/auth/refresh` ไปเลย จะได้ไม่ติดไปกับทุก request
- mobile app: keychain ของ iOS หรือ keystore ของ Android

## refresh token rotation

ทุกครั้งที่ refresh ให้ออก refresh token ใบใหม่ด้วย แล้วยกเลิกใบเก่าทิ้ง

ประโยชน์คือถ้าวันไหนมีคนเอาใบเก่าที่ใช้ไปแล้วกลับมา refresh แปลว่ามีคนก๊อป token ไป ให้ลบ token ทั้ง family ของ user คนนั้นทิ้ง เตะออกจากระบบทุกเครื่อง แล้วบังคับ login ใหม่ ตรงนี้คือสิ่งที่ access token เดี่ยว ๆ ทำไม่ได้เลย

## ที่เจอพลาดบ่อย

- ใส่ข้อมูล sensitive ใน payload ตัว JWT แค่ base64 ใครก็ decode อ่านได้ ลายเซ็นกันแก้ไข ไม่ได้กันอ่าน
- ตั้ง access token อายุเป็นวัน แบบนี้ refresh token แทบไม่มีประโยชน์ กลับไปมีช่องโหว่เดิม
- เก็บ refresh token ไว้ localStorage คู่กับ access token โดนขโมยพร้อมกันทั้งคู่ เสียจุดประสงค์ไปเลย
- ไม่มี logout ที่ลบ refresh token ออกจาก db ปิดเว็บแล้วแต่ token ยังใช้ได้อีกเป็นเดือน
- ตอนเจอ 401 แล้วหลาย request ยิง refresh พร้อมกัน ควรทำ queue ให้ refresh ครั้งเดียว ที่เหลือรอผลแล้วค่อย retry

ถ้าบอกมาว่าใช้ stack อะไร เดี๋ยวผมเขียนตัวอย่าง implement ทั้งฝั่ง api และ interceptor ให้ดูได้ครับ
