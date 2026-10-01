ถ้าไม่เห็นโค้ดก็ตอบได้คร่าว ๆ ว่าค่าที่ส่งเข้าไปเป็น optional อยู่ แต่ parameter ฝั่งรับประกาศเป็น `string` เฉย ๆ TypeScript เลยไม่ยอมให้ผ่านครับ

ที่มาของ `undefined` ที่เจอบ่อย
- property แบบ optional (`name?: string`)
- `process.env.API_URL` คืน `string | undefined` เสมอ
- `array.find()`, `map.get()`, ผลลัพธ์ของ regex `match()`
- เปิด `noUncheckedIndexedAccess` แล้วเข้าถึงด้วย index เช่น `arr[0]`

ทางแก้ เรียงจากที่ควรใช้ก่อน

**1. เช็กก่อนใช้ ให้ TS narrow type ให้**

```ts
const url = process.env.API_URL
if (!url) throw new Error('API_URL ยังไม่ได้ตั้งค่า')
connect(url) // ตรงนี้เป็น string แล้ว
```

วิธีนี้ดีสุดเพราะกรณีที่ค่าหายไปจริงก็มี error ที่อ่านรู้เรื่อง ไม่ใช่ไปพังที่อื่นทีหลัง

**2. ใส่ค่า default ถ้ามีค่าที่สมเหตุสมผล**

```ts
greet(name ?? 'guest')
```

ใช้ `??` อย่าใช้ `||` เพราะ `||` จะตีว่า empty string เป็นค่าว่างด้วย

**3. แก้ที่ signature ถ้าฝั่งรับควรรองรับ undefined อยู่แล้ว**

```ts
function greet(name: string | undefined) { ... }
```

บางทีต้นเหตุคือ type ฝั่งรับแคบเกินจริง ไม่ใช่ฝั่งส่งผิด

**4. `name!` หรือ `as string`** ใช้เฉพาะตอนมั่นใจว่ามีค่าแน่ ๆ แต่ TS พิสูจน์ไม่ได้ ตัวนี้แค่ปิดปาก compiler ถ้าเดาผิดก็ไปพังตอน runtime

อีกเรื่องที่เจอบ่อย: เช็ก `if (user.name)` แล้วแต่ยัง error อยู่ เกิดตอนมี `await` หรือ callback คั่นกลาง หรือ `user` ไม่ใช่ตัวแปร const พวกนี้ TS จะทิ้ง narrowing ไป แก้ด้วยการดึงออกมาเก็บเป็นตัวแปร local ก่อน

```ts
const name = user.name
if (!name) return
await save(name)
```

ถ้าส่งบรรทัดที่ error กับ signature ของฟังก์ชันที่เรียกมาให้ดู เดี๋ยวชี้ให้ว่าเคสนี้ควรใช้ข้อไหนครับ
