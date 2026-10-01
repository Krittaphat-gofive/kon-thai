ก่อนตอบข้อดีข้อเสีย อยากชวนตั้งคำถามก่อนว่าตอนนี้เจ็บตรงไหนครับ เพราะ GraphQL แก้ปัญหาบางแบบได้ดีมาก แต่ถ้าย้ายเพราะอยากลองของใหม่ จะเจอต้นทุนที่ไม่คุ้ม

## ข้อดี

**client ขอข้อมูลเองได้**
หน้า list ขอแค่ 3 field หน้า detail ขอ 20 field ใช้ query เดียวกันไม่ได้ก็เขียนคนละ query ไม่ต้องทำ endpoint `/users/summary` กับ `/users/full` แยกกัน ปัญหา over-fetching กับ under-fetching หายไปเกือบหมด

**ลด round trip**
หน้าเดียวที่เดิมต้องยิง 5 endpoint แล้วรอทีละตัว เหลือ request เดียว เรื่องนี้เห็นผลชัดมากบน mobile ที่ latency สูง

**schema เป็น contract ที่บังคับใช้จริง**
มี type ชัดเจน generate typescript type จาก schema ได้เลย เอกสารไม่หลุดจากโค้ดเพราะเป็นตัวเดียวกัน ต่างจาก swagger ที่ต้องคอยอัปเดตเอง

**frontend ไม่ต้องรอ backend**
UI เปลี่ยน อยากได้ field เพิ่มที่มีใน schema อยู่แล้ว ก็แก้ query ฝั่งเดียวจบ ทีมที่แยก frontend/backend ชัด ๆ ได้ประโยชน์ข้อนี้มากที่สุด

**versioning ง่ายกว่า**
ไม่ต้องทำ `/v2` ใช้ `@deprecated` ที่ field แล้วดูจาก metrics ว่ายังมีใครเรียกอยู่ไหม พอไม่มีคนใช้ค่อยลบ

## ข้อเสีย

**caching ยากขึ้นเยอะ**
ข้อนี้หนักสุด REST ได้ HTTP cache กับ CDN ฟรี แต่ GraphQL ยิง POST ไป `/graphql` ทางเดียว CDN ช่วยอะไรไม่ได้ ต้องไปทำ cache ที่ client (Apollo, urql) หรือใช้ persisted query + GET ถึงจะเอา CDN กลับมาได้ ซึ่งก็เป็นงานเพิ่ม

**N+1 query**
query ที่ขอ `posts { author { name } }` 50 posts จะกลายเป็น 51 query ถ้าไม่ระวัง ต้องใช้ DataLoader หรือตัวเทียบเท่าตั้งแต่วันแรก ไม่ใช่ค่อยมาแก้ทีหลัง

**คุมโหลดยาก**
rate limit แบบนับจำนวน request ใช้ไม่ได้แล้ว เพราะ 1 request หนักเบาไม่เท่ากัน ต้องทำ depth limit กับ query cost analysis เอง ไม่งั้นมีคนยิง query ซ้อน 10 ชั้นเข้ามาที DB ล่ม

**monitoring มืดลง**
ทุกอย่างเป็น `POST /graphql` ตอบ 200 หมด แม้แต่ตอน error APM เดิมที่ดู status code กับ path จะอ่านอะไรไม่ได้เลย ต้อง instrument ที่ระดับ resolver ใหม่

**error handling คนละโลก**
error มาใน `errors` array พร้อม HTTP 200 โค้ดฝั่ง client ที่เช็ก status code อยู่ต้องรื้อหมด

**authorization ละเอียดขึ้น**
เดิมเช็กที่ endpoint จบ ทีนี้ต้องเช็กราย field เพราะคนที่เข้า query ได้ อาจไม่ควรเห็น `user.salary`

**file upload กับ streaming ไม่ถนัด** ส่วนใหญ่สุดท้ายก็ต้องเหลือ REST endpoint ไว้ทำงานพวกนี้อยู่ดี

## ตัดสินใจแบบนี้

| สถานการณ์ | ควรไหม |
|---|---|
| มี client หลายตัว (web, iOS, Android) ขอข้อมูลต่างกัน | คุ้ม |
| หน้าหนึ่งต้องยิง 4-5 endpoint แล้วรอกัน | คุ้ม |
| frontend รอ backend ทำ endpoint ใหม่ตลอด | คุ้ม |
| public API ที่พึ่ง CDN cache หนัก | อย่า |
| internal API, client เดียว, endpoint นิ่งแล้ว | ไม่คุ้ม |
| ทีมเล็ก ไม่มีคนดูแล tooling เพิ่ม | ไม่คุ้ม |

## ถ้าจะย้ายจริง

อย่าทำ big bang เริ่มจากวาง GraphQL เป็น layer หน้า REST เดิม (BFF pattern) resolver ไปเรียก service เดิมที่มีอยู่ ยังไม่ต้องแตะ data layer แล้วเลือกมาสัก feature เดียวที่เจ็บที่สุด ทำให้จบ วัดผลจริงว่า request ลดลงเท่าไร หน้าเร็วขึ้นไหม ทีมรับไหวไหม ค่อยตัดสินใจขยาย

REST ก็ไม่ต้องทิ้ง webhook, health check, file upload, OAuth callback ปล่อยไว้แบบเดิมดีกว่า ระบบใหญ่ ๆ ส่วนใหญ่ก็อยู่กันสองแบบแบบนี้

ถ้าบอกได้ว่าตอนนี้ระบบหน้าตาประมาณไหน มี client กี่ตัว และปัญหาที่ทำให้อยากเปลี่ยนคืออะไร เดี๋ยวช่วยดูให้ว่าคุ้มหรือมีทางแก้ที่ถูกกว่าครับ
