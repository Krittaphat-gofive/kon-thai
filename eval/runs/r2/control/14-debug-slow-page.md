## หลักคิด: อย่าเพิ่งเดา — แยกให้ได้ก่อนว่า 8 วินาทีนั้นหมดไปกับอะไร

เปิด DevTools → แท็บ Network → hard reload แล้วดู waterfall ก่อนเลย คำถามเดียวที่ต้องตอบคือ **เวลาส่วนใหญ่อยู่ช่วงไหน**

| ช่วงที่ช้า | แปลว่า | ไปดูต่อที่ |
|---|---|---|
| TTFB ของ request แรก / API สูง | backend หรือ DB ช้า | query, index, cache |
| TTFB เร็ว แต่ download นาน | payload ใหญ่ / bundle ใหญ่ | ขนาด JSON, code splitting |
| ไฟล์มาครบแล้วแต่หน้ายังขาว | render / JS ช้า | แท็บ Performance |
| request เรียงกันเป็นขั้นบันได | API waterfall (ยิงทีละตัว) | ทำให้ parallel |

ข้อสุดท้ายเป็นสาเหตุที่เจอบ่อยที่สุดในหน้า dashboard โดยเฉพาะ — มี 8 widget ยิง 8 endpoint แบบรอกันทีละตัว ตัวละ 1 วิ ก็ครบ 8 วินาทีพอดี ถ้า waterfall เป็นขั้นบันได คุณเจอต้นเหตุแล้วโดยไม่ต้องดูอย่างอื่น

## คำถามคัดกรองที่ช่วยตัดตัวเลือกได้เร็ว

- **ช้าทุกครั้ง หรือช้าเฉพาะครั้งแรก?** — ครั้งแรกอย่างเดียวมักเป็น cold start / lambda / connection pool ยังไม่อุ่น
- **ช้าเฉพาะ production หรือ local ก็ช้า?** — ถ้า local เร็วแต่ prod ช้า มักเป็นเรื่องปริมาณข้อมูลหรือ network latency ไม่ใช่โค้ด
- **ช้าเฉพาะ user บางคน / บางช่วงวันที่?** — เป็นสัญญาณชัดว่า query scale ตามจำนวน row ของ user นั้น
- **เพิ่งช้า หรือช้ามานาน?** — ถ้าเพิ่งช้า ให้ย้อนดู deploy ล่าสุดก่อนเลย คุ้มกว่าไล่โค้ดทั้งหมด

## ถ้าปัญหาอยู่ฝั่ง backend

ไล่ตามลำดับนี้:

1. **หา endpoint ที่ช้าที่สุด** จาก Network tab แล้วโฟกัสตัวเดียวก่อน อย่าแก้พร้อมกันหลายจุด
2. **นับจำนวน query ต่อ 1 request** — เปิด query log แล้วดู ถ้าเห็น query หน้าตาเหมือนกันรันซ้ำ 50-100 ครั้ง นั่นคือ N+1 (แก้ด้วย eager loading / join / batch)
3. **`EXPLAIN ANALYZE` query ที่ช้า** — มองหา full table scan, missing index บน column ที่ใช้ใน `WHERE` / `JOIN` / `ORDER BY`
4. **ดูว่ามีการคำนวณ aggregate สดทุกครั้งไหม** — `SUM`/`COUNT` ทั้งตารางเพื่อโชว์การ์ดใบเดียว เป็นปัญหาคลาสสิกของ dashboard แก้ด้วย summary table, materialized view หรือ cache ที่ refresh เป็นรอบ
5. **เช็ก external call** — ถ้า backend ไปเรียก API อื่นหรือ service อื่นระหว่างทาง ตรงนั้นมักเป็นคอขวดที่มองไม่เห็นจากฝั่ง client

## ถ้าปัญหาอยู่ฝั่ง frontend

- ขนาด JS bundle (ดู Coverage tab ว่าโหลดมาแล้วไม่ได้ใช้เท่าไร) — chart library หนัก ๆ ควร lazy load
- จำนวน re-render (React DevTools Profiler) — dashboard ที่ state ตัวเดียวทำให้ทั้งหน้า render ใหม่
- render ตารางหลายพันแถวพร้อมกันโดยไม่มี virtualization หรือ pagination

## สิ่งที่ควรทำก่อนแก้

วัดให้ได้ตัวเลข baseline แล้วจดไว้ (เช่น endpoint นี้ 4.2 วิ, bundle 2.1 MB) เพราะ dashboard มักช้าจากหลายสาเหตุรวมกัน ถ้าไม่มีตัวเลขเทียบ จะไม่รู้ว่าที่แก้ไปได้ผลจริงหรือแค่รู้สึกว่าเร็วขึ้น

---

ถ้าบอก stack ที่ใช้ (framework, ฐานข้อมูล, SSR/CSR) และ screenshot ของ Network waterfall มา ผมช่วยเจาะจุดที่น่าจะเป็นต้นเหตุให้ตรงกว่านี้ได้ครับ
