## ข้อดีของ GraphQL

**ลด over-fetching / under-fetching**
Client ระบุ field ที่ต้องการเอง ไม่ต้องรับ payload ทั้งก้อน — ได้ผลชัดกับ mobile หรือเน็ตช้า

**ลด round trip**
จากเดิมที่ต้องยิง `/users/1` → `/users/1/orders` → `/orders/5/items` เหลือ query เดียว ซึ่งช่วยเรื่อง latency มากกว่าเรื่อง bandwidth อีก

**Schema เป็น contract ที่ strongly typed**
มี introspection ทำให้ codegen ได้จริง (TypeScript types, React hooks) และ tooling อย่าง GraphiQL / Apollo Studio ใช้งานได้ทันที เอกสารไม่หลุดจากโค้ดเหมือน OpenAPI ที่ต้องมาคอยอัปเดตเอง

**ลด coupling ระหว่างทีม**
Frontend เปลี่ยน requirement ได้โดยไม่ต้องรอ backend เพิ่ม endpoint ใหม่ ข้อนี้มักเป็นเหตุผลที่คุ้มที่สุดจริง ๆ ถ้าทีม frontend ถูก block บ่อย

**Versioning ยืดหยุ่นกว่า**
Deprecate ทีละ field ได้ ไม่ต้องทำ `/v2` ทั้งชุด

---

## ข้อเสียและต้นทุนที่ต้องจ่าย

**HTTP caching หายไป**
POST ไป endpoint เดียวทำให้ CDN / reverse proxy / browser cache ใช้ไม่ได้เลย ต้องไปทำ persisted queries + GET, หรือพึ่ง client-side cache (Apollo/urql) แทน ถ้าระบบปัจจุบันพึ่ง CDN caching หนัก ๆ นี่คือข้อเสียที่ใหญ่ที่สุด

**N+1 query problem**
Resolver ที่เขียนตรงไปตรงมาจะยิง DB ซ้ำมหาศาล ต้องใช้ DataLoader / batching แทบทุกที่ ซึ่งไม่ใช่ของที่เขียนครั้งเดียวจบ

**Security surface กว้างขึ้น**
Client เขียน query เองได้แปลว่ายิง query ลึก ๆ หรือซ้อน ๆ จนล่มระบบได้ ต้องมี depth limit, query cost analysis, allowlist ของ operation — งานที่ REST ไม่ต้องทำ

**Authorization ย้ายไปอยู่ระดับ field**
จากเดิมเช็คที่ route เดียวจบ กลายเป็นต้องเช็คทุก field ที่ sensitive และต้องมั่นใจว่าไม่มีช่องให้เข้าถึงอ้อมผ่าน relation

**Observability และ error handling ต้องรื้อ**
GraphQL ตอบ HTTP 200 เสมอแม้มี error ทำให้ alert ที่ตั้งบน 5xx ใช้ไม่ได้ และ metric แบบ per-endpoint ก็ใช้ไม่ได้ ต้อง instrument ใหม่เป็น per-operation

**เรื่องจุกจิกอื่น ๆ**
File upload ไม่ native, rate limiting แบบนับ request ใช้ไม่ได้ผล (ต้องนับ cost แทน), learning curve ของทีมทั้ง backend และ frontend

---

## ข้อคิดก่อนตัดสินใจ

คำถามสำคัญกว่าคือ **ปัญหาที่เจอตอนนี้คืออะไร** เพราะหลายเคสแก้ได้ถูกกว่ามาก:

- ถ้าปัญหาคือ over-fetching → ลอง sparse fieldsets (`?fields=id,name`) ก่อน
- ถ้าปัญหาคือ round trip เยอะ → ทำ BFF endpoint รวมข้อมูลให้หน้าจอนั้น ๆ
- ถ้าปัญหาคือ type safety / DX → OpenAPI + codegen หรือ tRPC (ถ้าเป็น TypeScript ทั้ง stack) ให้ผลใกล้เคียงด้วยต้นทุนต่ำกว่าเยอะ

**GraphQL คุ้มเมื่อ:** มีหลาย client ที่ต้องการข้อมูลต่างกัน (web / iOS / Android), data model เชื่อมโยงกันเป็น graph จริง ๆ, หรือมีทีม frontend หลายทีมที่ติดคอขวดที่ backend

**ไม่คุ้มเมื่อ:** เป็น CRUD ตรงไปตรงมา, มี client เดียว, ทีมเล็ก, หรือเป็น public API ให้ลูกค้าภายนอกใช้ (REST เรียนรู้ง่ายกว่าสำหรับคนนอก)

---

## ถ้าตัดสินใจจะไป

อย่า rewrite ทั้งระบบรวดเดียว — วิธีที่เสี่ยงน้อยสุดคือวาง GraphQL layer ครอบ REST เดิม แล้วย้ายทีละ domain หรือเริ่มจากหน้าจอที่เจ็บที่สุดหน้าเดียว วัดผลจริงว่า latency / จำนวนบรรทัดโค้ด frontend ดีขึ้นจริงไหม แล้วค่อยขยาย ระหว่างนั้น REST เดิมยังอยู่ได้ ไม่มีใครต้องรอ

ถ้าบอกได้ว่าตอนนี้ pain point ของทีมคืออะไร และ client มีกี่ตัว จะช่วยประเมินให้ตรงกว่านี้ได้ครับ
