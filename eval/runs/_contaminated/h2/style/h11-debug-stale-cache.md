เกือบทุกเคสที่เจออาการนี้คือ cache ของ `index.html` ครับ ไฟล์ JS/CSS มี hash ในชื่ออยู่แล้วเลยไม่ค่อยมีปัญหา แต่ตัว HTML ที่ชี้ไปหาไฟล์พวกนั้น ถ้า browser หรือ CDN เก็บตัวเก่าไว้ ผู้ใช้ก็โหลด bundle เวอร์ชันเก่าต่อไป

ที่บอกว่า hard refresh แล้วหาย ยิ่งตรง เพราะ Ctrl+Shift+R สั่งข้าม cache ทั้งหมด

## cache ซ่อนอยู่ได้ 3 ชั้น

**1. browser cache**
ถ้า server ไม่ได้ส่ง `Cache-Control` มากับ `index.html` browser จะเดา TTL ให้เอง (heuristic caching ปกติคิดจาก `Last-Modified`) แล้วใช้ไฟล์เก่าโดยไม่ถาม server เลย

**2. CDN หรือ reverse proxy**
CloudFront, Cloudflare, nginx `proxy_cache` ถือ `index.html` ไว้ตาม TTL ถ้า deploy แล้วไม่ purge ก็ยังเสิร์ฟของเก่าอยู่ ข้อนี้อธิบายคำว่า "บางคน" ได้ดีที่สุด เพราะแต่ละ edge หมดอายุไม่พร้อมกัน คนที่วิ่งเข้า edge ที่ยังไม่หมดอายุก็เห็นหน้าเก่า

**3. service worker**
ถ้าโปรเจกต์เป็น PWA หรือใช้ Angular service worker / Workbox ตัว service worker จะเสิร์ฟจาก cache ก่อนแล้วค่อยดึงของใหม่มาเก็บไว้เบื้องหลัง ของใหม่จะมีผลก็ต่อเมื่อปิดแท็บเดิมหมดทุกแท็บแล้วเปิดใหม่ คนที่เปิดเว็บค้างไว้ทั้งวันเลยไม่เห็นเวอร์ชันใหม่สักที

## เช็กว่าเป็นชั้นไหน

เปิด DevTools แล้วดู response header ของ `index.html`
- `Cache-Control` กับ `Age` บอกว่าใครเก็บไว้นานแค่ไหน
- `x-cache: Hit from cloudfront` หรือ `cf-cache-status: HIT` ฟ้องว่า CDN เสิร์ฟของเก่า
- แท็บ Application > Service Workers ดูว่ามี worker ค้างสถานะ waiting อยู่ไหม

## วิธีแก้

| ไฟล์ | Cache-Control |
|---|---|
| JS/CSS ที่มี hash ในชื่อ | `public, max-age=31536000, immutable` |
| `index.html` | `no-cache` |

`no-cache` ไม่ได้แปลว่าห้าม cache แต่แปลว่าต้อง revalidate กับ server ทุกครั้งก่อนใช้ ถ้าไฟล์ไม่เปลี่ยนจะได้ 304 กลับมา ไม่เปลืองแบนด์วิดท์ อย่าใช้ `no-store` เพราะจะโหลดใหม่ทั้งก้อนทุกครั้ง

จากนั้นใส่ขั้นตอน invalidate `/index.html` เข้าไปใน deploy pipeline ด้วย เช่น `aws cloudfront create-invalidation --paths "/index.html"` ข้อนี้คนลืมกันบ่อยสุด ตั้ง header ถูกแล้วแต่ CDN ยังถือของเก่าอยู่

ถ้ามี service worker ให้ทำ update flow ให้ชัด คือพอตรวจเจอเวอร์ชันใหม่ ก็ขึ้นแถบแจ้งผู้ใช้ว่า "มีเวอร์ชันใหม่ กดเพื่อโหลด" แล้วค่อย `skipWaiting()` ตอนผู้ใช้กด ดีกว่าสลับให้เองเงียบ ๆ ตอนผู้ใช้กำลังกรอกฟอร์มอยู่

อีกอย่างที่ช่วยได้กับ SPA ที่คนเปิดค้างไว้ข้ามวัน คือให้ frontend poll ไฟล์ `version.json` เป็นระยะ ถ้าเลข build ไม่ตรงกับที่โหลดมาตอนแรก ก็ขึ้นแจ้งให้ reload

ถ้าบอกได้ว่า deploy บนอะไร (S3 + CloudFront, nginx, IIS) และมี service worker หรือเปล่า เดี๋ยวผมเขียน config ที่ตรงกับของจริงให้ครับ
