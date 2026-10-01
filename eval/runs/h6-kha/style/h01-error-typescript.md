TS2345 ตัวนี้แปลว่า compiler เห็นว่าค่าที่ส่งเข้าไปมีโอกาสเป็น `undefined` แต่ฝั่งที่รับประกาศไว้ว่ารับแค่ `string` ค่ะ ไม่ใช่ error ของ type ที่ผิดชนิด แต่เป็นเรื่องที่ยังไม่ได้ตัดเคส `undefined` ออกก่อนใช้

ที่เจอบ่อยคือค่าพวกนี้
- `.find()` กับ `.pop()` คืน `T | undefined` เสมอ
- property ที่ประกาศเป็น optional เช่น `name?: string`
- `process.env.API_URL` type เป็น `string | undefined`
- เข้าถึง array หรือ object ด้วย index ตอนเปิด `noUncheckedIndexedAccess`
- regex match group กับ `req.query.id` ใน express

ทางแก้ เรียงจากที่ควรใช้ก่อน

**1. เช็กก่อนใช้ ให้ compiler narrow type ให้**

```ts
const user = users.find(u => u.id === id)
if (!user) {
  throw new NotFoundError(`ไม่พบ user id ${id}`)
}
greet(user.name)  // ตรงนี้ type เป็น string แล้ว
```

วิธีนี้ดีที่สุดเพราะพอ runtime เจอค่าว่างจริง จะได้ error ที่บอกสาเหตุ แทนที่จะพังที่อื่นแบบงง ๆ

**2. ใส่ค่า default ด้วย `??`**

ใช้ตอนที่มีค่าสำรองที่สมเหตุสมผลจริง

```ts
greet(user?.name ?? 'guest')
```

ระวังอย่าใช้ `||` แทน เพราะ `''` กับ `0` จะโดนแทนที่ไปด้วย

**3. แก้ที่ signature ถ้าฟังก์ชันนั้นรองรับค่าว่างได้อยู่แล้ว**

```ts
function greet(name?: string) { ... }
```

ถ้าข้างในมันเช็ก `if (!name)` อยู่แล้ว การประกาศแบบนี้ตรงกับความจริงมากกว่า

**4. `!` ใช้เมื่อมั่นใจจริง ๆ เท่านั้น**

```ts
greet(user!.name)
```

อันนี้แค่บอก compiler ให้เงียบ ไม่ได้กันอะไรตอน runtime ถ้าใช้ ควรเขียน comment กำกับว่าทำไมถึงรู้ว่าไม่มีทางเป็น `undefined`

**เคส env var** เจอบ่อยจนแนะนำให้ทำ helper ไว้ตัวเดียว

```ts
function requireEnv(key: string): string {
  const value = process.env[key]
  if (!value) throw new Error(`ตั้งค่า ${key} ใน .env ก่อน`)
  return value
}

const apiUrl = requireEnv('API_URL')
```

ส่วนการปิด `strictNullChecks` ใน tsconfig ก็ทำให้ error หายจริง แต่เท่ากับทิ้งการเช็ก null ทั้ง project ไป ไม่คุ้มกับการแลก

ถ้าส่งโค้ดบรรทัดที่ error กับ signature ของฟังก์ชันที่เรียกมาให้ดู เดี๋ยวบอกได้ว่าเคสนี้ควรใช้ข้อไหนคะ
