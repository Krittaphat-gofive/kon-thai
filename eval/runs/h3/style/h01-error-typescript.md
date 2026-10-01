TypeScript บอกว่าค่าที่ส่งเข้าไปอาจเป็น `undefined` ได้ แต่ฟังก์ชันปลายทางรับแค่ `string` ครับ

เจอบ่อยตอนเปิด `strict` แล้วไปดึงค่าจากที่ที่ไม่การันตีว่ามีค่า เช่น

- `process.env.API_URL` TypeScript มองเป็น `string | undefined` เสมอ
- property ที่ประกาศเป็น optional เช่น `name?: string`
- ผลจาก `.find()` หรือ `Map.get()` ถ้าหาไม่เจอก็ได้ `undefined`
- regex capture group หรือ `str.split(",")[1]` ตอนเปิด `noUncheckedIndexedAccess`

## แก้ได้ 4 ทาง เรียงจากที่ควรใช้ก่อน

**1. เช็กก่อนส่ง** ดีที่สุดเพราะได้จัดการเคสที่ไม่มีค่าจริง ๆ

```ts
const url = process.env.API_URL
if (!url) throw new Error("API_URL is not set")
connect(url)   // ตรงนี้ TypeScript รู้แล้วว่าเป็น string
```

**2. ใส่ค่า default** ใช้ตอนที่ค่าว่างแล้วระบบยังทำงานต่อได้

```ts
connect(process.env.API_URL ?? "http://localhost:3000")
```

ระวังอย่าใช้ `||` ถ้าค่าว่าง (`""`) หรือ `0` เป็นค่าที่ถูกต้องในระบบ

**3. แก้ signature ปลายทาง** ถ้าฟังก์ชันนั้นรับค่าว่างได้อยู่แล้ว ก็เปลี่ยนให้ตรงความจริง

```ts
function connect(url: string | undefined) { ... }
```

**4. `!` หรือ `as string`** ใช้ต่อเมื่อมั่นใจจริง ๆ ว่ามีค่าแน่นอน แต่ compiler ไม่รู้

```ts
connect(process.env.API_URL!)
```

ข้อนี้ไม่ได้แก้ปัญหา แค่สั่งให้ TypeScript เงียบ ถ้าค่าเป็น `undefined` ขึ้นมาจริงก็พังตอน runtime เหมือนเดิม

## สรุปสั้น ๆ

ถ้าค่านั้น "ต้องมี" ให้ใช้ข้อ 1 ถ้า "ไม่มีก็ได้" ให้ใช้ข้อ 2 หรือ 3 เก็บข้อ 4 ไว้เป็นทางสุดท้าย

ถ้าส่งโค้ดบรรทัดที่ error มาด้วย เดี๋ยวดูให้ว่าเข้าเคสไหนครับ
