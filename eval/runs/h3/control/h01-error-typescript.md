TypeScript บอกว่าค่าที่ส่งเข้าไป "อาจเป็น undefined" แต่ฟังก์ชันปลายทางรับแค่ `string` เท่านั้น — ต้องกำจัดความเป็นไปได้ที่จะเป็น undefined ก่อนส่ง

ตัวที่มักเป็นต้นเหตุ: `process.env.XXX`, property ที่เป็น optional (`foo?: string`), ผลลัพธ์จาก `.find()` / `Map.get()`, regex match group, หรือการ index array ตอนเปิด `noUncheckedIndexedAccess`

## วิธีแก้ เรียงจากดีสุด

**1. เช็กก่อนใช้ (narrow)** — ปลอดภัยสุด เพราะ TS จะ narrow type ให้เอง

```ts
const name = user.name;
if (!name) throw new Error('name is required');
doSomething(name); // ตรงนี้เป็น string แล้ว
```

ถ้าอยู่ในฟังก์ชันก็ early return ไปเลย

**2. ใส่ค่า default** — ใช้เมื่อ "ไม่มีค่า" เป็นเรื่องปกติและมี fallback ที่สมเหตุสมผล

```ts
doSomething(user.name ?? 'anonymous');
```

ใช้ `??` ไม่ใช่ `||` นะ เพราะ `||` จะ fallback ตอนเป็น `''` หรือ `0` ด้วย ซึ่งมักไม่ใช่สิ่งที่ต้องการ

**3. แก้ที่ signature ปลายทาง** — ถ้าจริง ๆ แล้วฟังก์ชันนั้นรับ undefined ได้อยู่แล้ว ก็เปลี่ยนเป็น `string | undefined` หรือ `name?: string` ตรงนั้นแทน จะตรงความจริงมากกว่ามาไล่ปะที่ caller ทุกจุด

**4. `!` (non-null assertion)** — เขียนสั้นสุดแต่เป็นการปิดปาก compiler เฉย ๆ

```ts
doSomething(user.name!);
```

ถ้าเดาผิดก็ได้ `undefined` ไปเต็ม ๆ ตอน runtime แนะนำให้ใช้เฉพาะตอนที่มั่นใจจริงและ narrow ไม่ได้ (เช่น TS ตามไม่ทันข้าม closure) ไม่ควรใช้เป็นวิธีหลัก

## ถ้าเป็น env var

เคสนี้เจอบ่อยสุด อย่าไล่ใส่ `!` ทีละจุด ทำ validate รวมที่เดียวตอน start app ดีกว่า:

```ts
function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) throw new Error(`Missing env: ${key}`);
  return value;
}

export const env = {
  dbUrl: requireEnv('DATABASE_URL'),
  apiKey: requireEnv('API_KEY'),
};
```

แล้วที่อื่นก็ import `env` ไปใช้ได้เลย เป็น `string` ล้วน พังตั้งแต่ตอน boot ไม่ใช่ตอน request เข้ามา (ถ้าโปรเจกต์ใช้ zod อยู่แล้ว ทำเป็น schema ก็ได้ผลเดียวกัน)

---

อยากให้ดูเคสจริง ๆ ว่าควรใช้วิธีไหน แปะโค้ดบรรทัดที่ error กับ signature ของฟังก์ชันที่เรียกมาได้เลย
