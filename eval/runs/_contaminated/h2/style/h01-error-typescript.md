TypeScript ฟ้องว่าค่าที่ส่งเข้าฟังก์ชันอาจเป็น `undefined` แต่ parameter ฝั่งรับประกาศไว้ว่ารับ `string` อย่างเดียวครับ ไม่ใช่ error ของ runtime แต่เป็นการเตือนว่ามีเส้นทางหนึ่งที่ค่าหลุดมาเป็น `undefined` ได้

## ต้นตอที่เจอบ่อย

- property หรือ parameter ที่ประกาศเป็น optional: `name?: string`
- `process.env.API_URL` ซึ่ง type เป็น `string | undefined` เสมอ
- `map.get(key)`, `array.find(...)`, `str.match(...)?.[1]` ที่หาไม่เจอแล้วคืน `undefined`
- เปิด `noUncheckedIndexedAccess` ไว้ แล้วอ่านค่าจาก index เช่น `parts[1]`

## วิธีแก้ เรียงจากที่ควรใช้ก่อน

**1. เช็กก่อนใช้ (narrowing)** วิธีนี้ดีที่สุดเพราะโค้ดได้จัดการเคส `undefined` จริง

```ts
if (!userId) {
  throw new Error('userId is required');
}
doSomething(userId); // ตรงนี้ type เหลือ string แล้ว
```

**2. ใส่ค่า default** ใช้ตอนที่ค่าว่างแปลว่า "ไม่ระบุ" แล้วระบบไปต่อได้

```ts
doSomething(name ?? '');
// หรือกำหนดที่ parameter ไปเลย
function greet(name: string = 'guest') { ... }
```

ระวังอย่างเดียวคืออย่าใช้ `||` กับ string เพราะ `''` จะโดนแทนที่ไปด้วย ใช้ `??` ปลอดภัยกว่า

**3. แก้ที่ฝั่งฟังก์ชัน** ถ้าฟังก์ชันรับค่าว่างได้อยู่แล้ว ก็แก้ signature ให้ตรงความจริง

```ts
function doSomething(id: string | undefined) { ... }
```

**4. `!` (non-null assertion)** ใช้เมื่อมั่นใจจริง ๆ ว่าตรงนั้นมีค่าแน่ เช่น เพิ่งเช็กไปในบรรทัดก่อนหน้าแต่ TypeScript ตามไม่ทัน

```ts
doSomething(config.url!);
```

ข้อเสียคือเป็นการปิดปาก compiler ถ้าวันหลังค่าหลุดมาเป็น `undefined` จริงก็จะพังตอน runtime เลย ส่วน `as string` ยิ่งไม่แนะนำ เพราะกลบทั้ง type ไม่ใช่แค่ `undefined`

## กรณี env var

ถ้าเจอจาก `process.env` เขียน helper ตัวเดียวแล้วเรียกใช้ทั่วโปรเจกต์จะคุ้มกว่าไล่ใส่ `!` ทีละจุด

```ts
function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) throw new Error(`Missing env: ${key}`);
  return value;
}
```

## จุดที่คนมักพลาด

narrowing หายได้ถ้าค่าเป็น property ของ object เช่นเช็ก `if (obj.name)` แล้วไปใช้ `obj.name` ใน callback หรือหลัง `await` TypeScript จะถือว่าค่าอาจเปลี่ยนไปแล้ว ทางแก้คือดึงใส่ตัวแปร local ก่อน

```ts
const name = obj.name;
if (!name) return;
await save(name);
```

ถ้าแปะบรรทัดที่ error กับ signature ของฟังก์ชันที่เรียกมาด้วย เดี๋ยวผมดูให้ว่าควรแก้ฝั่งคนเรียกหรือฝั่งฟังก์ชันครับ
