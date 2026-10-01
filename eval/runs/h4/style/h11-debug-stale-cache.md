ส่วนใหญ่เกิดจาก cache ฝั่ง browser ครับ โดยเฉพาะตัว `index.html` ที่ browser ยังเก็บของเก่าไว้ อาการที่กด hard refresh แล้วหายก็เป็นเบาะแสตรงนี้ เพราะ Ctrl+Shift+R สั่งข้าม cache ไปโหลดใหม่ทั้งหมด

## ไล่สาเหตุทีละข้อ

**1. index.html เก่าค้างอยู่ใน cache (เจอบ่อยสุด)**

ตอน build ไฟล์ js/css จะได้ชื่อที่มี hash ติดมา เช่น `main.a3f9c2.js` เปลี่ยนทุก build ตัวที่บอกว่าจะโหลดไฟล์ไหนคือ `index.html` ถ้า browser ยังใช้ `index.html` ตัวเก่า ก็จะเรียก bundle เก่าต่อไป ทั้งที่ของใหม่ขึ้น server เรียบร้อยแล้ว

**2. asset ไม่มี hash ในชื่อ**

ถ้า build ออกมาเป็น `main.js`, `style.css` เฉย ๆ ชื่อเดิมทุก deploy พอ browser เห็นชื่อเดิมและ `max-age` ยังไม่หมดอายุ ก็หยิบของใน cache มาใช้เลย ไม่ยิงถาม server ด้วยซ้ำ

**3. CDN หรือ reverse proxy ยังเสิร์ฟของเก่า**

CloudFront, Cloudflare, nginx proxy_cache พวกนี้ถ้า deploy แล้วไม่ invalidate แต่ละ edge จะหมดอายุไม่พร้อมกัน ตรงกับอาการ "ผู้ใช้บางคน" พอดี เพราะแต่ละคนเข้าคนละ edge

**4. service worker**

ถ้าโปรเจกต์เป็น PWA หรือมี service worker อยู่ ตัวใหม่จะค้างสถานะ waiting จนกว่าจะปิดแท็บเดิมทั้งหมด hard refresh รอบเดียวบางทีก็ยังไม่พอ ต้องปิดแท็บหมดก่อน

**5. instance เก่ายังไม่ตาย**

ถ้าเป็น SSR ระหว่าง rolling update ตัวเก่ากับตัวใหม่รันพร้อมกันอยู่ load balancer สุ่มส่งไปเจอตัวเก่าได้ แต่ข้อนี้จะหายเองภายในไม่กี่นาทีหลัง rollout เสร็จ ถ้าอาการค้างข้ามวัน ตัดทิ้งได้เลย

## วิธีเช็กว่าเป็นข้อไหน

เปิด DevTools แท็บ Network กด hard refresh แล้วดู response header ของ `index.html`

- `cache-control` บอกว่าตั้งค่าไว้ยังไง
- `age` สูง ๆ แปลว่าของมาจาก cache ของ CDN
- `x-cache: Hit from cloudfront` ชี้ชัดว่าติดที่ CDN
- แท็บ Application > Service Workers ดูว่ามีตัวไหนค้าง waiting อยู่ไหม

## ทางแก้

แยก cache policy ตามชนิดไฟล์ อันนี้เป็นมาตรฐานที่ใช้กันทั่วไป

| ไฟล์ | Cache-Control |
|---|---|
| `index.html` | `no-cache` (เก็บได้ แต่ต้องถาม server ทุกครั้งว่ามีของใหม่ไหม) |
| ไฟล์ที่มี hash ในชื่อ | `public, max-age=31536000, immutable` |

แล้วเพิ่มอีกสองอย่าง

- เปิด hash ใน build config ถ้ายังไม่ได้เปิด ไม่งั้น policy ข้างบนใช้ไม่ได้
- ใส่คำสั่ง invalidate CDN ไว้ใน deploy pipeline ให้รันอัตโนมัติทุกครั้ง
- ถ้ามี service worker ให้ดัก event `updatefound` แล้วเด้ง toast บอกผู้ใช้ว่ามีเวอร์ชันใหม่ กดแล้ว reload ให้ ดีกว่าปล่อยให้ผู้ใช้ไปค้นเองว่าต้องกดอะไร

ใช้ framework อะไรกับ deploy ไว้ที่ไหนครับ เดี๋ยวเขียน config ให้ตรงตัวเลย
