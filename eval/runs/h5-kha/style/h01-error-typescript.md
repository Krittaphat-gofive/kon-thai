สาเหตุคือค่าที่ส่งเข้าไปอาจเป็น `undefined` ได้ แต่ฟังก์ชันปลายทางรับแค่ `string` ค่ะ error ตัวนี้จะโผล่มาตอนเปิด `strictNullChecks`

ที่มาของ `undefined` ที่เจอบ่อย
- property ที่ประกาศเป็น optional เช่น `name?: string`
- `process.env.API_URL` ซึ่ง type เป็น `string | undefined` เสมอ
- `arr.find(...)` หรือ `map.get(...)` ที่หาไม่เจอ
- group ของ regex match
- อ่าน array ด้วย index ตอนเปิด `noUncheckedIndexedAccess`

ทางแก้ เรียงจากที่ควรเลือกก่อน

**1. เช็กก่อนใช้** ตรงไปตรงมาที่สุด และได้จัดการเคสที่ไม่มีค่าไปด้วย

```ts
if (!name) {
  throw new Error('name is required');
}
doSomething(name); // ตรงนี้ type แคบเหลือ string แล้ว
```

**2. ใส่ค่า default ด้วย `??`** ใช้ตอนที่ค่าว่างแปลว่าใช้ค่าตั้งต้นได้

```ts
doSomething(name ?? '');
```

ระวังนิดนึงว่า `??` ต่างจาก `||` ตรงที่ `''` กับ `0` จะไม่โดนแทนที่

**3. แก้ signature ของฟังก์ชัน** ถ้า `undefined` เป็นเคสปกติที่ฟังก์ชันควรรับได้อยู่แล้ว ก็แก้ที่ต้นทางจะตรงกว่า

```ts
function doSomething(name: string | undefined) { ... }
```

**4. `name!` หรือ `name as string`** ใช้เฉพาะตอนที่รู้แน่ว่ามีค่าแต่ TypeScript มองไม่เห็น เช่น เช็กไว้คนละฟังก์ชัน วิธีนี้แค่ปิดปาก compiler ไม่ได้ป้องกันอะไรตอน runtime ถ้าพลาดจะไปพังเอาตอนรันแทน

ส่วนใหญ่ข้อ 1 กับ 2 จบงาน ถ้าวางบรรทัดที่ error กับ signature ของฟังก์ชันมาให้ดู เดี๋ยวชี้ให้ว่าเคสนี้ควรใช้แบบไหนค่ะ
