TypeScript บอกว่ามีค่าที่อาจเป็น `undefined` หลุดเข้าไปในพารามิเตอร์ที่รับแค่ `string` ครับ ตัวโค้ดเองอาจทำงานได้ปกติ แต่ compiler พิสูจน์ไม่ได้ว่าตรงนั้นมีค่าแน่

## หาต้นตอก่อน

ค่าที่เป็น `string | undefined` ส่วนใหญ่มาจากไม่กี่ที่นี้

| ที่มา | ตัวอย่าง |
|---|---|
| optional property | `user?.name`, `interface { name?: string }` |
| `process.env` | `process.env.API_URL` |
| `.find()` / `Map.get()` | หาไม่เจอก็ได้ `undefined` |
| `noUncheckedIndexedAccess` | `arr[0]`, `obj[key]` |
| regex / DOM | `str.match(...)?.[1]`, `getElementById()` |
| optional parameter | `function f(id?: string)` |

ชี้ cursor ไปที่ argument ตัวที่ error แล้วดูว่า type มาจากไหน จะเลือกวิธีแก้ได้ตรงจุดกว่า

## วิธีแก้ เรียงจากดีไปหาแย่

**1. เช็กก่อนใช้ (narrowing) ดีที่สุด**

```ts
if (!id) {
  throw new Error('id is required');
  // หรือ return / return NotFound() แล้วแต่ context
}
doSomething(id); // ตรงนี้ TypeScript รู้แล้วว่าเป็น string
```

ข้อดีคือได้จัดการเคส `undefined` จริง ๆ ไม่ใช่แค่ปิดปาก compiler

**2. ใส่ค่า default ถ้าค่าว่างแปลว่าอะไรบางอย่างที่รับได้**

```ts
doSomething(name ?? '');
doSomething(process.env.API_URL ?? 'http://localhost:3000');
```

ใช้ `??` ไม่ใช่ `||` เพราะ `||` จะกิน empty string กับ `0` ไปด้วย

**3. แก้ที่ signature ถ้าฟังก์ชันรับ undefined ได้อยู่แล้ว**

```ts
function doSomething(id: string | undefined) { ... }
```

เหมาะตอนที่ฟังก์ชันปลายทางเป็นโค้ดของเราเอง และข้างในเช็กอยู่แล้ว

**4. `!` (non-null assertion) ทางเลือกสุดท้าย**

```ts
doSomething(id!);
```

วิธีนี้แค่บอก compiler ว่า "เชื่อผม" ไม่ได้เพิ่มการป้องกันอะไรเลย ถ้าเดาผิดก็ไปพังตอน runtime แทน ใช้เฉพาะตอนมั่นใจจริง ๆ แล้วเขียน comment กำกับว่าทำไมถึงมั่นใจ

## เคสที่เจอบ่อยเป็นพิเศษ

**env variable** แนะนำให้ validate ตอน startup ทีเดียว แล้วที่เหลือใช้ได้สบาย

```ts
function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) throw new Error(`Missing env: ${key}`);
  return value;
}

export const config = {
  apiUrl: requireEnv('API_URL'),
};
```

**`.find()`**

```ts
const user = users.find(u => u.id === id);
if (!user) return null;
sendEmail(user.email);
```

**object property** ถ้าดึงจาก object ระวังเรื่อง narrowing หาย ตอนเป็น property ของ object ที่ไม่ใช่ `const` TypeScript จะลืม narrowing หลังเรียกฟังก์ชันอื่นคั่น ดึงออกมาเป็นตัวแปรก่อนจะชัวร์กว่า

```ts
const { name } = user;
if (!name) return;
greet(name);
```

ถ้าวางโค้ดจุดที่ error กับบรรทัดที่ compiler ชี้มาให้ดู เดี๋ยวผมบอกได้เลยว่าควรใช้วิธีไหนครับ
