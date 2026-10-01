แปลว่าตรงนั้นส่งค่าที่อาจเป็น `undefined` เข้าไปในพารามิเตอร์ที่ประกาศว่ารับ `string` เท่านั้นครับ TypeScript เลยกันไว้ก่อน เพราะถ้าเป็น `undefined` จริงโค้ดข้างในฟังก์ชันอาจพังตอน runtime

ที่มาของ `undefined` ที่เจอบ่อยมีไม่กี่แบบ

| ต้นทาง | ทำไมเป็น undefined |
|---|---|
| `arr.find(...)` | หาไม่เจอก็คืน `undefined` |
| `process.env.API_URL` | type คือ `string \| undefined` เสมอ |
| `obj.name?` (optional property) | ไม่มี key นี้ก็ได้ |
| `arr[0]` ตอนเปิด `noUncheckedIndexedAccess` | index อาจไม่มีของ |
| `map.get(key)` | ไม่เจอ key ก็คืน `undefined` |
| `useParams()` / `searchParams.get()` | route param อาจไม่มี |

**วิธีแก้ เรียงจากที่ควรใช้ก่อน**

1. เช็กก่อนใช้ แล้วให้ TypeScript narrow type ให้เอง อันนี้ปลอดภัยสุดและบอก intent ชัด

```ts
const user = users.find(u => u.id === id);
if (!user) {
  throw new Error(`User not found: ${id}`);
}
doSomething(user.name); // ตรงนี้ TS รู้แล้วว่าไม่ใช่ undefined
```

2. ใส่ค่า default ด้วย `??` ถ้ามีค่าสำรองที่สมเหตุสมผล ระวังอย่าใช้ `||` เพราะ empty string จะโดนแทนด้วย

```ts
doSomething(process.env.API_URL ?? 'http://localhost:3000');
```

3. แก้ที่ signature ถ้าฟังก์ชันนั้นรับ `undefined` ได้อยู่แล้ว ก็ประกาศให้ตรงความจริง

```ts
function doSomething(name: string | undefined) { ... }
```

4. `!` (non-null assertion) เก็บไว้เป็นทางสุดท้าย

```ts
doSomething(user!.name);
```

ตัวนี้แค่ปิดปาก compiler ไม่ได้เช็กอะไรเลย ถ้าค่าเป็น `undefined` จริงก็พังตอน runtime เหมือนเดิม ใช้ได้เฉพาะตอนที่มั่นใจจริง ๆ ว่ามีค่าแน่ แต่ TypeScript พิสูจน์เองไม่ได้ และควรเขียน comment กำกับไว้ว่าทำไมถึงมั่นใจ

**ถ้าเป็นเคสที่เจอซ้ำ ๆ** ลองเขียน helper ไว้ใช้ร่วมกัน จะได้ไม่ต้องกระจาย `if` ไปทั่ว

```ts
function assertDefined<T>(value: T | undefined, message: string): T {
  if (value === undefined) throw new Error(message);
  return value;
}

doSomething(assertDefined(user, 'user is required').name);
```

ถ้าแปะโค้ดบรรทัดที่ error กับ signature ของฟังก์ชันปลายทางมาให้ดู เดี๋ยวผมชี้ให้ว่าเคสนี้ควรใช้แบบไหนครับ
