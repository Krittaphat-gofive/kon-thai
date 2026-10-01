## Signal คืออะไร

Signal คือ "กล่องเก็บค่า" ที่รู้ว่าใครอ่านมันอยู่บ้าง เวลาค่าเปลี่ยนมันจะไปบอกคนที่อ่านให้คำนวณใหม่เอง — เป็น reactive primitive ที่ Angular ทำขึ้นมาเองเพื่อแทนที่กลไก change detection แบบเดิม (Zone.js)

```ts
const count = signal(0);           // writable signal
const double = computed(() => count() * 2);  // derived, lazy + memoized

count();        // อ่านค่า — synchronous, ได้ค่าทันที
count.set(5);
count.update(c => c + 1);

effect(() => console.log(count(), double()));  // side effect, track dependency อัตโนมัติ
```

จุดสำคัญที่คนมักมองข้าม: **ไม่ต้องประกาศ dependency** Angular ดูจากว่าในฟังก์ชันเรียก signal ตัวไหนบ้างตอน runtime แล้วสร้างกราฟ dependency ให้เอง และ `computed` เป็น **lazy** — ถ้าไม่มีใครอ่าน มันไม่คำนวณเลย

API ที่เกี่ยวข้องในระบบนิเวศนี้: `input()` / `model()` / `viewChild()` / `contentChild()` (signal-based แทน decorator), `linkedSignal()` (state ที่ reset ตาม source ได้), `resource()` / `httpResource()` (async loading เป็น signal) — ตัวหลัง ๆ มาใน v19–v20 ควรเช็กเวอร์ชันที่โปรเจกต์ใช้ก่อน

---

## ต่างจาก Observable ยังไง

| | Signal | Observable |
|---|---|---|
| ค่าปัจจุบัน | มีเสมอ อ่านแบบ sync ได้ | ไม่มีจนกว่าจะ emit (ยกเว้น `BehaviorSubject`) |
| เวลา / async | ไม่รู้จักเวลา — เป็น snapshot ของ state | ออกแบบมาเพื่อ stream ที่ไหลตามเวลา |
| Operators | น้อยมาก (`computed`, `effect`) | 100+ ตัว: `debounce`, `retry`, `switchMap`, ... |
| การ cleanup | อัตโนมัติตาม injection context | ต้อง unsubscribe / `takeUntilDestroyed` เอง |
| ซ้ำค่าเดิม | ตัดทิ้งให้ด้วย `Object.is` | emit ทุกครั้ง จนกว่าจะใส่ `distinctUntilChanged` |
| Cold / Hot | เป็นค่าเดียวที่แชร์กัน (hot เสมอ) | cold by default — subscribe ใหม่ = รันใหม่ |
| Error / Complete | ไม่มี channel พวกนี้ | มีครบ |
| Change detection | ผูกกับ CD โดยตรง → zoneless ได้ | ต้องผ่าน `async` pipe หรือ `markForCheck` |

### สองเรื่องที่ต่างกันเชิงแนวคิดจริง ๆ

**1. Push vs. push-pull**
Observable *ผลัก* ค่าออกมาทุกครั้งที่มี ส่วน signal แค่ผลัก "สัญญาณว่าเปลี่ยนแล้ว" ออกไป แล้วปลายทางค่อย *ดึง* ค่าตอนที่ต้องใช้จริง ผลคือ chain ยาว ๆ ของ `computed` ที่ไม่มีใครอ่านจะไม่ถูกคำนวณเลย

**2. Glitch-free**
อันนี้คือข้อได้เปรียบที่ชัดที่สุดของ signal

```ts
// RxJS — combineLatest ยิง 2 ครั้ง ครั้งแรกเป็นค่า inconsistent
const total$ = combineLatest([price$, qty$]).pipe(map(([p, q]) => p * q));
// เปลี่ยน price จาก source เดียวกัน → total$ emit ค่ากลางที่ผิดก่อน 1 ครั้ง

// Signal — computed เห็นค่าที่ consistent เสมอ คำนวณครั้งเดียว
const total = computed(() => price() * qty());
```

Signal แก้ปัญหา diamond dependency ให้ในตัว ส่วน RxJS ต้องจัดการเอง

---

## ควรใช้อะไรตอนไหน

กฎที่ใช้ได้จริงที่สุด: **state → signal, event → observable**

### ใช้ Signal เมื่อ

- **State ของ component** ที่ template ต้องแสดง — แทน `BehaviorSubject` ได้เกือบทั้งหมด
- **ค่าที่ derive จาก state อื่น** — `computed` ชนะ `combineLatest + map` ขาดลอยทั้งเรื่องอ่านง่ายและ performance
- **Input / query ของ component**
- **State ใน service ที่แชร์กันทั้งแอป** (store เล็ก ๆ)

```ts
@Component({
  template: `
    @for (u of visible(); track u.id) { <li>{{ u.name }}</li> }
    <p>เจอ {{ visible().length }} จาก {{ users().length }} คน</p>
  `
})
export class UserList {
  users = signal<User[]>([]);
  keyword = signal('');
  visible = computed(() =>
    this.users().filter(u => u.name.includes(this.keyword()))
  );
}
```

ไม่มี `async` pipe ซ้ำ ๆ ไม่มี subscription ให้ลืม และอ่าน `visible()` กี่รอบก็คำนวณครั้งเดียว

### ใช้ RxJS เมื่อ

- **ต้องจัดการเวลา** — `debounceTime`, `throttleTime`, `interval`, `timer`
- **ต้องยกเลิกงานเก่า** — `switchMap` คือ type-ahead search ที่ถูกต้อง ไม่มีอะไรใน signal แทนได้ตรง ๆ
- **ต้อง retry / error handling** — `retry({ delay })`, `catchError`
- **Stream ที่ไหลต่อเนื่อง** — WebSocket, SSE, mouse/scroll event
- **ประสาน async หลายเส้น** — `forkJoin`, `concatMap`, `race`

```ts
// เคสนี้ signal ทำไม่ได้สวยเท่า
search = new FormControl('');
results = toSignal(
  this.search.valueChanges.pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap(q => this.api.search(q)),   // ยกเลิก request เก่าให้อัตโนมัติ
  ),
  { initialValue: [] }
);
```

### เชื่อมสองโลกที่ขอบ

แนวทางที่ใช้กันจริงคือ **RxJS ทำ pipeline, signal เก็บผลลัพธ์, template อ่าน signal**

```ts
import { toSignal, toObservable } from '@angular/core/rxjs-interop';

user = toSignal(this.http.get<User>('/api/me'));          // Observable → Signal
query$ = toObservable(this.keyword);                       // Signal → Observable
```

`toSignal` จัดการ unsubscribe ตอน destroy ให้เอง — ถ้าไม่ใส่ `initialValue` ค่าแรกจะเป็น `undefined` (type ก็จะติด `| undefined` มาด้วย) ส่วน HTTP ล้วน ๆ ที่ไม่ต้องการ operator อะไรเลย ลองดู `httpResource()` ซึ่งให้ `value` / `isLoading` / `error` เป็น signal มาในชุดเดียว

---

## ข้อควรระวัง

**อย่าใช้ `effect` sync state** — นี่คือความผิดพลาดที่เจอบ่อยที่สุด

```ts
// ❌ ผิด
effect(() => this.total.set(this.price() * this.qty()));
// ✅ ถูก
total = computed(() => this.price() * this.qty());
```

`effect` มีไว้สำหรับ side effect ที่ออกนอกระบบ reactive เท่านั้น เช่น logging, localStorage, จัดการ DOM นอก Angular, ส่ง analytics ถ้าจะ "เขียน state ตาม state อื่นแต่ต้องแก้มือได้" ให้ใช้ `linkedSignal`

**การแก้ object/array ต้องสร้างใหม่** — signal เทียบด้วย `Object.is`

```ts
items.update(arr => { arr.push(x); return arr; });  // ❌ ไม่ trigger
items.update(arr => [...arr, x]);                   // ✅
```

**`untracked()`** ใช้เมื่อต้องอ่าน signal ใน `computed`/`effect` โดยไม่อยาก subscribe มัน

**ไม่ต้องรีบ migrate ทั้งหมด** — ทั้งสองอย่างอยู่ร่วมกันได้ดี ทีมส่วนใหญ่ย้าย component state ไป signal ก่อน แล้วปล่อย HTTP/event stream ไว้กับ RxJS ตามเดิม ซึ่งเป็นจุดที่ RxJS ยังแข็งแรงกว่ามาก
