ส่วนใหญ่เกิดจาก browser หรือ CDN ยังเก็บ `index.html` ตัวเก่าไว้ใน cache ครับ พอไฟล์ HTML เป็นตัวเก่า มันก็ยังชี้ไปที่ bundle JS/CSS ชุดเดิม ทั้งที่ของใหม่ขึ้น server ไปแล้ว

เหตุผลที่ hard refresh แล้วหาย ก็เพราะ hard refresh ข้าม cache ไปขอไฟล์ใหม่ทั้งหมด ซึ่งยืนยันได้เลยว่าปัญหาอยู่ที่ชั้น cache ไม่ใช่ที่ตัว build

## ชั้นที่ต้องไล่เช็ก

มีสามชั้นหลักที่เก็บของเก่าไว้ได้

1. **browser cache** ถ้า `index.html` ส่งมาพร้อม `Cache-Control: max-age=3600` หรือไม่ได้ส่ง header อะไรมาเลย browser ก็จะใช้ของเก่าจนกว่าจะหมดอายุ
2. **CDN / reverse proxy** CloudFront, Cloudflare, nginx พวกนี้ cache ไว้อีกชั้น ถึง browser จะขอใหม่ แต่ CDN ก็อาจคืนของเก่าให้อยู่ดี
3. **service worker** ถ้าแอปเป็น PWA หรือเผลอเปิด service worker ไว้ ตัวนี้ดื้อที่สุด เพราะมันคุม cache เอง ไม่สนใจ HTTP header และ reload ธรรมดาไม่ช่วย

เช็กง่าย ๆ เปิด DevTools ไปที่ Network ดู response header ของ `index.html` แล้วดูต่อที่ Application > Service Workers ว่ามีตัวไหนลงทะเบียนค้างอยู่ไหม

## วิธีแก้

กฎเหล็กคือ แยก header ของ HTML ออกจาก asset ให้ชัด

| ไฟล์ | Cache-Control |
|---|---|
| `index.html` | `no-cache, must-revalidate` |
| JS/CSS ที่มี content hash ในชื่อไฟล์ | `public, max-age=31536000, immutable` |

`no-cache` ไม่ได้แปลว่าห้าม cache แต่แปลว่าให้ถาม server ทุกครั้งก่อนใช้ ถ้าไฟล์ไม่เปลี่ยน server ตอบ 304 กลับมา ซึ่งเร็วมากอยู่แล้ว

ส่วนไฟล์ asset ต้องมี content hash ในชื่อ เช่น `main.a1b2c3.js` พอ build ใหม่ชื่อไฟล์ก็เปลี่ยน ไม่มีทางชนกับของเก่า เลย cache ยาว ๆ ได้อย่างปลอดภัย เฟรมเวิร์กสมัยนี้ทำให้อยู่แล้ว แต่ก็ควรเปิดดูว่า build output ออกมาแบบนี้จริง

อีกสองอย่างที่ต้องทำ

- **purge CDN ตอน deploy** ใส่ขั้นตอน invalidate cache ของ path `/` กับ `/index.html` ไว้ใน pipeline เลย จะได้ไม่ต้องมานั่งกดเอง
- **จัดการ service worker** ถ้ามีใช้จริง ให้ตัว service worker ตัวใหม่เรียก `skipWaiting()` แล้วเด้ง toast บอกผู้ใช้ว่า "มีเวอร์ชันใหม่ กดเพื่อโหลดใหม่" ถ้าไม่ได้ตั้งใจใช้ ก็ unregister ทิ้งพร้อมเคลียร์ Cache Storage

## ตัวช่วยระยะยาว

ถ้าอยากกันเคสที่ผู้ใช้เปิดแท็บค้างไว้ข้ามวัน ให้ฝังเลข build ไว้ในแอป แล้วให้ frontend ยิงถาม endpoint เช่น `/version.json` เป็นระยะ ถ้าเลขไม่ตรงกับตอนที่โหลดมา ก็ขึ้นแจ้งให้ reload วิธีนี้ตัดปัญหาแบบนี้ไปได้เกือบหมด

ถ้าบอกได้ว่าใช้ stack อะไร deploy ขึ้นที่ไหน เดี๋ยวเขียน config ของ nginx หรือ CDN ตัวนั้นให้เลยครับ
