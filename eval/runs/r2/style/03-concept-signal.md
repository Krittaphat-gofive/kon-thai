ต่างกันที่ตัวตั้งต้นเลยครับ signal คือ "ค่า" ที่รู้ตัวว่าใครอ่านมันอยู่ ส่วน Observable คือ "สายน้ำของเหตุการณ์" ที่ไหลมาตามเวลา

## signal คืออะไร

```ts
import { signal, computed, effect } from '@angular/core';

const count = signal(0);
const double = computed(() => count() * 2);

count();            // อ่านค่าปัจจุบัน ได้ 0 ทันที
count.set(5);
count.update(n => n + 1);
double();           // 12 คำนวณตอนอ่าน แล้ว cache ไว้

effect(() => console.log('count =', count()));  // ยิงทุกครั้งที่ count เปลี่ยน
```

จุดสำคัญคือตอนเรียก `count()` ใน template หรือใน `computed` Angular จะจดไว้ว่าใครพึ่งค่านี้อยู่ พอค่าเปลี่ยน ก็ไปอัปเดตเฉพาะจุดนั้น ไม่ต้องไล่เช็กทั้งต้นไม้ นี่คือเหตุผลที่ signal มาคู่กับ zoneless

## ต่างกันตรงไหน

| | signal | Observable |
|---|---|---|
| ค่าปัจจุบัน | มีเสมอ อ่านได้ทันที | ไม่มี ต้องรอค่าไหลมา |
| จำนวนค่า | ค่าเดียว ณ เวลาหนึ่ง | ไหลมาได้เรื่อย ๆ |
| sync / async | sync ล้วน | รองรับ async |
| การใช้งาน | อ่านตรง ๆ `count()` | ต้อง subscribe |
| memory leak | แทบไม่ต้องกังวล | ต้องเคลียร์เอง |
| จัดการเวลา | ไม่มี | debounce, throttle, retry, switchMap |
| ยกเลิกงานกลางคัน | ไม่ได้ | ได้ |
| error / complete | ไม่มีแนวคิดนี้ | มี |

## เรื่องที่คนมักไม่รู้: signal ไม่ยิงค่ากลาง ๆ

```ts
const firstName = signal('สมชาย');
const lastName  = signal('ใจดี');
const fullName  = computed(() => `${firstName()} ${lastName()}`);
```

ถ้าเปลี่ยนทั้งสองตัวในจังหวะเดียวกัน `fullName` จะคำนวณรอบเดียว ได้ค่าที่ถูกต้องเลย เทียบกับ `combineLatest` ที่จะยิงค่าระหว่างทางออกมาด้วย เช่น "สมหญิง ใจดี" ก่อนจะกลายเป็นค่าจริง ปัญหาแบบนี้ใน RxJS ต้องแก้ด้วย operator เพิ่ม แต่ signal ตัดไปได้ตั้งแต่ต้น

อีกข้อที่พลาดกันบ่อย อย่าใช้ `effect` ไปเซ็ต signal ตัวอื่น ถ้าอยากได้ค่าที่คำนวณจากค่าอื่นให้ใช้ `computed` หรือ `linkedSignal` เมื่อต้องการให้แก้ทับได้ `effect` เอาไว้ทำงานที่ออกไปนอกระบบ reactive เช่น เขียน localStorage หรือสั่ง chart วาดใหม่

## เลือกยังไง

ใช้ signal เมื่อโจทย์คือ "ค่า"
- state ใน component: loading flag, โหมดฟอร์ม, แถวที่เลือกอยู่, ค่า filter
- ค่าที่คำนวณจาก state อื่น ใช้ `computed`
- `@Input()` เปลี่ยนมาใช้ `input()` ได้เลย ได้ `computed` ต่อฟรี
- อะไรก็ตามที่ template ต้องอ่าน

ใช้ RxJS เมื่อโจทย์คือ "เหตุการณ์ตามเวลา"
- search box ที่ต้อง debounce แล้วยกเลิก request เก่า
- websocket, SSE, polling, `interval`
- event stream: scroll, drag, keyboard
- HTTP ที่ต้อง retry หรือต่อคิวหลายสเต็ปตามลำดับ
- `router.events`, `form.valueChanges` ที่ Angular ยังคืนเป็น Observable

สรุปสั้น ๆ ถ้าเวลาเป็นส่วนหนึ่งของโจทย์ ใช้ RxJS ถ้าแค่อยากรู้ว่าตอนนี้ค่าเป็นอะไร ใช้ signal

## ใช้ร่วมกันคือคำตอบจริง ๆ

ของจริงไม่ต้องเลือกข้าง `@angular/core/rxjs-interop` ให้สะพานไว้แล้ว

```ts
import { toSignal, toObservable } from '@angular/core/rxjs-interop';

query = signal('');

results = toSignal(
  toObservable(this.query).pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap(q => this.api.search(q)),
  ),
  { initialValue: [] as Item[] },
);
```

รูปแบบนี้ใช้ได้เกือบทุกหน้า: signal เป็นหน้าบ้านให้ template อ่าน RxJS อยู่ตรงกลางรับหน้าที่คุมจังหวะเวลา แล้วแปลงกลับเป็น signal ด้วย `toSignal` ซึ่ง unsubscribe ให้ตอน component ตายอยู่แล้ว

ย้ำอีกที signal ไม่ได้มาแทน RxJS แต่มาแทน `BehaviorSubject` ที่เราใช้เก็บ state ใน component กับ zone.js มากกว่า

ถ้าบอกมาว่าโปรเจกต์ใช้ Angular เวอร์ชันไหนและตอนนี้เขียน state แบบไหนอยู่ เดี๋ยวช่วยดูให้ว่าตรงไหนย้ายมา signal แล้วคุ้มครับ
