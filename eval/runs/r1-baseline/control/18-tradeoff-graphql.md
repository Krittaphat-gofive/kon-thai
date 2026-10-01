# REST → GraphQL: ข้อดีข้อเสีย

## ข้อดี

**1. Client กำหนด shape ของข้อมูลเองได้**
แก้ปัญหา over-fetching (ได้ field เกินที่ใช้) และ under-fetching (ต้องยิงหลายรอบ) หน้าจอ dashboard ที่เคยยิง 8 endpoints เหลือ query เดียว — ผลชัดมากกับ mobile และเน็ตช้า

**2. Schema เป็น contract ที่ typed จริง**
Introspection ทำให้ generate TypeScript types ให้ frontend ได้อัตโนมัติ, GraphiQL/Apollo Studio เป็น docs ที่ไม่มีวันล้าสมัย ต่างจาก OpenAPI ที่มักเขียนแล้วลืมอัปเดต

**3. Frontend เลิกรอ backend**
เพิ่มหน้าจอใหม่ที่ใช้ข้อมูลเดิมในมุมต่างกัน ไม่ต้องขอ endpoint ใหม่ทุกครั้ง — ตรงนี้คือเหตุผลที่ทีมส่วนใหญ่เปลี่ยนจริง ๆ

**4. Versioning นุ่มนวลกว่า**
`@deprecated` ที่ระดับ field แทนการทำ `/v1`, `/v2` ทั้งก้อน และวัดได้ว่ายังมีใครเรียก field นั้นอยู่ไหมก่อนลบ

**5. รวมหลาย service เป็น graph เดียว**
Federation (Apollo Federation / schema stitching) ช่วยได้มากถ้ามี BFF หลายตัวที่ logic ซ้ำกัน

## ข้อเสีย — ตรงนี้คือที่ทีมมักประเมินต่ำไป

**1. HTTP caching หายไปเกือบหมด**
ทุกอย่างเป็น `POST /graphql` → CDN, browser cache, `ETag`, reverse proxy ใช้ไม่ได้เลย ต้องไปลงทุนกับ persisted queries + APQ และ client-side cache (Apollo/urql/Relay) แทน ถ้า API ปัจจุบันพึ่ง CDN cache หนัก ๆ นี่คือ regression ที่เจ็บที่สุด

**2. N+1 queries**
Resolver ที่เขียนตรงไปตรงมาจะยิง DB รัว ๆ ต้องใช้ DataLoader (batching + per-request caching) ตั้งแต่วันแรก ไม่ใช่ค่อยมาแก้ทีหลัง

**3. ความปลอดภัย/DoS**
Client ขออะไรก็ได้ แปลว่า query ซ้อนลึก ๆ ล้ม DB ได้ ต้องมี depth limit, query cost analysis, timeout และปิด introspection บน production (ถ้าเป็น public API)

**4. Rate limiting และ observability พัง**
นับเป็น "request ต่อนาที" ไม่ได้อีกต่อไป ต้องนับเป็น cost แทน และ metric/APM ที่แยกตาม route จะเห็นแค่ endpoint เดียว — ต้องบังคับตั้งชื่อ operation และ instrument ระดับ resolver

**5. Error handling ผิดธรรมชาติ HTTP**
ตอบ `200 OK` พร้อม `errors` array เสมอ ระบบ monitoring, alert, log aggregation ที่ดูจาก status code ต้องรื้อใหม่

**6. Authorization ย้ายไปอยู่ระดับ field**
เดิมเช็คที่ route middleware ทีเดียวจบ ตอนนี้ต้องคิดว่า user คนนี้เห็น `User.email` ได้ไหมในทุกเส้นทางที่เดินมาถึง field นั้น

**7. Learning curve ของทั้งทีม**
Schema design, pagination แบบ Relay cursor spec, mutation design ไม่ได้เรียนรู้ใน sprint เดียว และ tooling เดิม (Postman collection, WAF rules, API gateway) ต้องเปลี่ยนตาม

## ข้อเสนอแนะ

**อย่าทำ big-bang rewrite** วาง GraphQL เป็น layer บาง ๆ หน้า REST เดิม (BFF pattern) แล้วย้ายทีละส่วน — REST เดิมยังอยู่ ไม่มี flag day

เริ่มจาก **หน้าจอเดียวที่เจ็บที่สุด** เช่นหน้าที่ยิงหลาย endpoint แล้วประกอบข้อมูลฝั่ง client วัดผลก่อนตัดสินใจขยาย: จำนวน round trip, payload size, time-to-first-render, และเวลาที่ frontend ต้องรอ backend เพิ่ม endpoint

**ตั้ง guardrail ตั้งแต่ query แรก** — DataLoader, depth/cost limit, persisted queries, บังคับตั้งชื่อ operation ย้อนกลับไปใส่ทีหลังแพงกว่ามาก

**ลองพิจารณาทางเลือกที่ถูกกว่าก่อน** ถ้าปัญหาจริงคือ "ยิงหลายรอบเกินไป" อย่างเดียว อาจแก้ได้ด้วย sparse fieldsets (`?fields=id,name`) หรือ BFF endpoint เฉพาะหน้าจอ และถ้า stack เป็น TypeScript ทั้งหมด tRPC ให้ type safety แบบเดียวกันโดยไม่ต้องแลกกับ caching และ complexity ข้างบนเลย

**GraphQL คุ้มชัดเจนเมื่อ:** มี client หลายตัว (web/iOS/Android) ที่ต้องการข้อมูลคนละ shape, data มีความสัมพันธ์เชื่อมโยงกันเยอะ, หรือ frontend ติด bottleneck รอ backend บ่อย
**ไม่คุ้มเมื่อ:** API เป็น CRUD ตรงไปตรงมา, public API ที่พึ่ง CDN cache, งาน file-heavy, หรือทีมเล็กที่ไม่มีเวลาดูแล infrastructure เพิ่ม

---

ถ้าบอกลักษณะระบบปัจจุบันได้ (stack, จำนวน client, ขนาดทีม, pain point ที่เจอจริง) ผมช่วยประเมินให้เจาะจงกว่านี้ได้ว่าคุ้มไหม
