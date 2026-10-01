ตัว TypeScript บอกว่าค่าที่ส่งเข้าไปอาจเป็น `undefined` แต่ฟังก์ชันปลายทางรับแค่ `string` ค่ะ ต้องตัด `undefined` ออกก่อนส่ง

ค่าแบบนี้มักมาจาก optional property (`name?: string`), `process.env.XXX`, `arr.find(...)` ที่หาไม่เจอ หรือ index เข้า array ตอนเปิด `noUncheckedIndexedAccess`

**วิธีแก้ เรียงจากที่ควรใช้ก่อน**

1. เช็กก่อนเรียก ให้ TypeScript narrow type ให้เอง ปลอดภัยสุดเพราะได้จัดการเคสที่ไม่มีค่าจริง ๆ

```ts
if (!name) return   // หรือ throw
doSomething(name)   // ตรงนี้ name เป็น string แล้ว
```

2. ใส่ค่า default ถ้าเคสไม่มีค่าแปลว่าใช้ค่าว่างหรือค่าสำรองได้

```ts
doSomething(name ?? '')
```

ใช้ `??` ไม่ใช่ `||` เพราะ `||` จะกินค่า `''` กับ `0` ไปด้วย

3. แก้ที่ signature ถ้าฟังก์ชันปลายทางควรรับเคสไม่มีค่าอยู่แล้ว

```ts
function doSomething(name: string | undefined) { ... }
```

4. `name!` ใช้ได้ แต่เป็นการบอก compiler ว่า "เชื่อหนูเถอะ" โดยไม่มีการเช็กตอน runtime ถ้าเดาผิดจะไประเบิดตอนรันแทน ใช้เฉพาะตอนมั่นใจจริง ๆ ว่ามีค่าแน่

**กรณีที่เจอบ่อยเป็นพิเศษ**

- env var: `process.env.API_URL` เป็น `string | undefined` เสมอ แนะนำให้ validate ตอน start app ครั้งเดียว แล้ว export ออกมาเป็น `string` ที่โค้ดส่วนอื่นใช้ได้เลย
- `arr.find()`: คืน `T | undefined` ตามสเปก ต้องเช็กผลลัพธ์ก่อนใช้ทุกครั้ง
- เช็กแล้วแต่ยังขึ้น error: ถ้าเช็กที่ property ของ object (เช่น `if (obj.name)`) แล้วมี function call คั่นกลาง TypeScript จะทิ้ง narrowing ให้ดึงใส่ตัวแปร local ก่อน

ถ้าส่งโค้ดบรรทัดที่ error มาด้วย เดี๋ยวบอกได้ว่าควรใช้ข้อไหนค่ะ
