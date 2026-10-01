เกือบทุกเคสเกิดจาก cache ที่ไฟล์ entry point ครับ คือ `index.html` ถ้า browser หรือ CDN ยังเก็บ `index.html` ตัวเก่าไว้ ไฟล์นั้นก็จะยังชี้ไป bundle ชุดเก่าอยู่ ต่อให้อัปโหลดไฟล์ใหม่ขึ้น server ครบแล้วก็ตาม พอกด hard refresh browser จะ bypass cache ทั้งหมดแล้วไปขอไฟล์สดจาก server เลยเห็นของใหม่

## จุดที่ต้องไล่เช็ก

มี cache อยู่หลายชั้น ไล่จากใกล้ผู้ใช้ที่สุด

**1. browser cache**
ดูใน DevTools แท็บ Network โหลดหน้าเว็บแล้วดูแถว `index.html` ถ้าขึ้น `(disk cache)` หรือ `(memory cache)` แปลว่าไม่ได้ยิงไป server เลย ปัญหาอยู่ที่ `Cache-Control` ของไฟล์นี้

**2. service worker**
ถ้าโปรเจกต์เป็น PWA หรือเคยลง service worker ไว้ ตัวนี้จะเสิร์ฟไฟล์จาก cache storage ของตัวเอง ซึ่งไม่สนใจ HTTP cache header เช็กที่ DevTools > Application > Service Workers ถ้าเห็นสถานะ "waiting to activate" ก็คือสาเหตุ

**3. CDN / reverse proxy**
ดู response header พวก `age`, `x-cache`, `cf-cache-status` ถ้า `age` เป็นเลขเยอะ ๆ แปลว่า edge ยังเสิร์ฟของเก่าอยู่ ต้อง purge ตอน deploy

**4. ชื่อไฟล์ asset ไม่มี content hash**
ถ้า bundle ยังชื่อ `main.js` เฉย ๆ ทุก build browser จะมองว่าเป็นไฟล์เดิม แล้วใช้ตัวใน cache ต่อ

## วิธีแก้

กฎเหล็กคือแยกไฟล์เป็นสองกลุ่ม ตั้ง header คนละแบบ

| ไฟล์ | Cache-Control |
|---|---|
| `index.html` | `no-cache` |
| asset ที่มี hash ในชื่อ เช่น `main.a3f9c2.js` | `max-age=31536000, immutable` |

`no-cache` ไม่ได้แปลว่าห้าม cache นะครับ แปลว่า cache ได้แต่ต้องถาม server ทุกครั้งว่าของเปลี่ยนหรือยัง ถ้าไม่เปลี่ยน server ตอบ 304 กลับมาซึ่งเบามาก ส่วนไฟล์ที่มี hash ในชื่อ cache ยาวไปเลยได้ เพราะพอ content เปลี่ยน hash ก็เปลี่ยน ชื่อไฟล์ใหม่ browser ก็โหลดใหม่เองอยู่แล้ว

เพิ่มอีกสามอย่างที่ควรทำ

- **ใส่ purge CDN เข้าไปใน pipeline** ตอน deploy เสร็จ ให้ยิง purge เฉพาะ `index.html` ก็พอ
- **จัดการ service worker ให้อัปเดตทันที** ใช้ `skipWaiting()` + `clients.claim()` หรือถ้าอยากให้ผู้ใช้ตัดสินใจเอง ก็ขึ้น toast ว่า "มีเวอร์ชันใหม่ กดเพื่อโหลดใหม่"
- **ดัก chunk load error** SPA ที่ทำ lazy loading จะเจอเคสที่ผู้ใช้เปิดหน้าค้างไว้ตั้งแต่ก่อน deploy พอกดเข้าหน้าใหม่ browser ไปขอ chunk เก่าที่ไม่มีบน server แล้ว ให้ดัก error ตรงนี้แล้วสั่ง `window.location.reload()` อัตโนมัติ

## ตรวจว่าแก้ได้จริงไหม

หลัง deploy รอบถัดไป ยิงคำสั่งนี้ดู header

```
curl -I https://your-site.com/
```

ดูว่า `cache-control` เป็น `no-cache` และ `age` เป็น 0 หรือไม่มี ถ้าใช่ก็ไม่ต้องให้ผู้ใช้กด hard refresh อีกแล้ว

ถ้าบอกได้ว่าใช้ stack อะไรกับ host ที่ไหน เดี๋ยวผมเขียน config ที่ตั้ง header ให้ตรงจุดเลยครับ
