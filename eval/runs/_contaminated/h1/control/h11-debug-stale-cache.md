สาเหตุหลักคือ browser หรือ CDN ยัง cache ไฟล์ `index.html` เก่าไว้ครับ พอ HTML เป็นของเก่า ไฟล์ JS/CSS ที่อ้างถึงก็เป็น hash ชุดเก่าตามไปด้วย ทั้งที่ของใหม่ขึ้น server ไปแล้ว

ที่กด hard refresh แล้วหาย เพราะ hard refresh สั่ง browser ข้าม cache ทั้งหมดแล้วไปขอใหม่จากต้นทาง

## ไล่ทีละชั้น

| ชั้น | อาการ | วิธีเช็ก |
|---|---|---|
| browser cache | เจอเฉพาะบางคน คนที่เพิ่งเคยเข้าไม่เจอ | DevTools > Network ดู `index.html` ว่าขึ้น `(disk cache)` ไหม |
| CDN / reverse proxy | เจอเป็นกลุ่ม ตาม region | ดู response header `age`, `x-cache: HIT` |
| service worker (PWA) | เจอนานผิดปกติ ปิดแท็บแล้วยังเก่า | DevTools > Application > Service Workers |

## แก้ที่ cache header

กฎเหล็กคือ แยกนโยบายระหว่าง HTML กับไฟล์ที่มี hash ในชื่อ

```
# index.html  ต้อง revalidate ทุกครั้ง
Cache-Control: no-cache

# /assets/main.a1b2c3.js  ชื่อไฟล์เปลี่ยนทุก build
Cache-Control: public, max-age=31536000, immutable
```

`no-cache` ไม่ได้แปลว่าห้ามเก็บนะ แปลว่าเก็บได้แต่ต้องถาม server ก่อนใช้ทุกครั้ง ถ้าของไม่เปลี่ยนก็ได้ 304 กลับมา เบามาก ส่วนตัวที่ห้ามเก็บจริง ๆ คือ `no-store` ซึ่งไม่ต้องใช้ในเคสนี้

ส่วนไฟล์ asset ที่ build tool ใส่ hash ให้อยู่แล้ว ปล่อยให้ cache ยาว ๆ ได้เลย เพราะพอ build ใหม่ชื่อไฟล์ก็เปลี่ยน ไม่มีทางชนกัน

## แก้ที่ CDN

เพิ่มขั้นตอน purge cache ของ path `/` กับ `/index.html` เข้าไปใน pipeline ตอน deploy ถ้าใช้ Cloudflare หรือ CloudFront ก็ยิง invalidation หลัง upload เสร็จ

## ถ้ามี service worker

ตัวนี้ดื้อที่สุด เพราะ service worker เก่าจะยังคุมหน้าเดิมจนกว่าจะปิดแท็บทั้งหมด ทางแก้มีสองแนว

1. `skipWaiting()` + `clients.claim()` ให้ตัวใหม่เข้าคุมทันที ข้อเสียคือถ้าผู้ใช้กำลังกรอกฟอร์มอยู่อาจสะดุด
2. ตรวจเจอเวอร์ชันใหม่แล้วเด้ง toast บอก "มีเวอร์ชันใหม่ กดเพื่อโหลดใหม่" ให้ผู้ใช้กดเอง อันนี้ปลอดภัยกว่าและ UX ดีกว่า

## กันไว้ล่วงหน้า

วาง endpoint เล็ก ๆ เช่น `/version.json` ที่มีแค่เลข build แล้วให้ frontend poll ทุก 5 นาที ถ้าเลขไม่ตรงกับตอนโหลดหน้า ก็แจ้งผู้ใช้ให้ refresh วิธีนี้ช่วยเรื่อง chunk load error ด้วย เพราะเวลา deploy ทับแล้ว lazy chunk เก่าหายไปจาก server ผู้ใช้ที่ค้างหน้าเดิมจะเจอ 404 ตอนกดเข้าหน้าใหม่

ถ้าบอกได้ว่าใช้ stack อะไร deploy ขึ้นที่ไหน เดี๋ยวผมเขียน config ให้ตรงตัวเลยครับ
