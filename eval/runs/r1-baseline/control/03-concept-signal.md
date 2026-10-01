# Signal ใน Angular

## 1. Signal คืออะไร

Signal คือ **กล่องห่อค่า (value wrapper) ที่รู้ว่าใครกำลังอ่านมันอยู่** และจะแจ้งเตือนคนเหล่านั้นเมื่อค่าเปลี่ยน

```ts
import { signal, computed, effect } from '@angular/core';

const count = signal(0);        // สร้าง
console.log(count());            // อ่าน — เรียกเหมือนฟังก์ชัน
count.set(5);                    // เขียนทับ
count.update(c => c + 1);        // เขียนจากค่าเดิม
```

คุณสมบัติที่สำคัญที่สุด 3 ข้อ:

- **มีค่าปัจจุบันเสมอ และอ่านแบบ synchronous** — ไม่มีสถานะ "ยังไม่มีค่า"
- **Dependency tracking อัตโนมัติ** — แค่อ่าน signal ข้างใน `computed`/`effect` Angular ก็รู้เองว่าต้องติดตามตัวไหน ไม่ต้องประกาศ
- **ไม่ต้อง subscribe/unsubscribe** — ไม่มี memory leak จากการลืม unsubscribe

## 2. API หลักที่ต้องรู้

```ts
@Component({
  selector: 'app-cart',
  template: `
    <p>ราคา/ชิ้น: {{ price() }}</p>
    <p>จำนวน: {{ count() }}</p>
    <p>รวม: {{ total() }}</p>
    <button (click)="add()">เพิ่ม</button>
  `,
})
export class CartComponent {
  readonly price = signal(100);
  readonly count = signal(0);

  // computed = derived state, lazy + cache ผลลัพธ์
  readonly total = computed(() => this.price() * this.count());

  constructor() {
    // effect = side effect ออกนอกโลก Angular
    effect(() => localStorage.setItem('cart-count', String(this.count())));
  }

  add() {
    this.count.update(c => c + 1);
  }
}
```

| API | ใช้ทำอะไร |
|---|---|
| `signal()` | state ต้นทางที่เราเขียนเอง |
| `computed()` | state ที่คำนวณจาก signal อื่น — lazy, cache ไว้, read-only |
| `effect()` | side effect: logging, localStorage, DOM นอก Angular, third-party lib |
| `linkedSignal()` | state ที่ "เขียนได้" แต่ reset ตาม source เมื่อ source เปลี่ยน |
| `input()` / `model()` / `output()` | แทน `@Input` / two-way / `@Output` |
| `viewChild()` / `contentChild()` | แทน `@ViewChild` แบบ signal |

`linkedSignal` แก้ปัญหาคลาสสิกที่ `computed` ทำไม่ได้ (เพราะเขียนไม่ได้) และ `effect` ไม่ควรทำ:

```ts
// user เลือกเองได้ แต่พอ list เปลี่ยน ให้ reset ไปตัวแรก
readonly selectedId = linkedSignal({
  source: () => this.items(),
  computation: (items, prev) =>
    items.find(i => i.id === prev?.value)?.id ?? items[0]?.id ?? null,
});
```

## 3. ต่างจาก RxJS Observable ยังไง

ความต่างแกนกลาง: **Signal คือ "ค่า ณ ขณะนี้" ส่วน Observable คือ "สายธารของเหตุการณ์ตามเวลา"**

| | Signal | Observable |
|---|---|---|
| โมเดล | ค่าเดียวที่เปลี่ยนได้ (state) | 0..n ค่าไหลมาตามเวลา (event stream) |
| อ่านค่า | sync เสมอ `count()` | ต้อง subscribe, อาจไม่มีค่าเลย |
| Async | ไม่รองรับโดยตรง | รองรับเต็มที่ |
| Subscribe | ไม่มี | ต้อง subscribe + cleanup |
| Dependency | track อัตโนมัติ | ต้องประกอบด้วย operator เอง |
| Operator | มีแค่ `computed` / `linkedSignal` | 100+ ตัว (`debounceTime`, `switchMap`, `retry`, …) |
| ยกเลิกงาน (cancel) | ไม่มีแนวคิดนี้ | first-class (`switchMap`, `takeUntil`) |
| Error | ไม่มี error channel — throw ตรง ๆ | มี error channel แยก |
| ค่ากลางผิดเพี้ยน (glitch) | ไม่มี — รับประกันค่า consistent | `combineLatest` ปล่อยค่ากลางที่ยังไม่ครบได้ |
| Multicast | เป็นโดยธรรมชาติ | ต้อง `share()` / `Subject` ไม่งั้น cold |
| Change detection | ละเอียดระดับ component → รองรับ zoneless | ต้องพึ่ง `async` pipe / zone |

**จุดที่คนมักเข้าใจผิด:** signal ไม่ใช่ `BehaviorSubject` รุ่นใหม่ และ **ไม่ได้มาแทน RxJS** — มันมาแทน *การใช้ RxJS ผิดงาน* ต่างหาก คือการเอา `BehaviorSubject` มาเก็บ state ธรรมดาในคอมโพเนนต์

อีกจุด: `computed` เป็น **lazy + memoized** — ถ้าไม่มีใครอ่าน มันจะไม่คำนวณเลย และถ้า dependency เปลี่ยนแล้วผลลัพธ์เท่าเดิม (เทียบด้วย `Object.is`) ตัวที่อยู่ถัดไปจะไม่ถูกแจ้งเตือน ต่างจาก `map()` ที่ยิงทุกครั้งที่ต้นทาง emit

## 4. สะพานเชื่อมสองโลก

```ts
import { toSignal, toObservable } from '@angular/core/rxjs-interop';

readonly user = toSignal(this.http.get<User>('/api/me'));          // Observable → Signal
readonly keyword$ = toObservable(this.keyword);                     // Signal → Observable
```

`toSignal` จะ subscribe ให้เอง และ unsubscribe ตอน component ถูกทำลาย ถ้า source ไม่ปล่อยค่าทันที ต้องใส่ `initialValue` ไม่งั้นค่าแรกจะเป็น `undefined` (หรือ throw ถ้าตั้ง `requireSync: true`)

ของใหม่ฝั่ง async ที่ควรดู (ยังเป็น experimental — API อาจเปลี่ยน): `resource()`, `rxResource()` และ `httpResource()` ซึ่งห่อ loading / error / value ไว้เป็น signal ให้เสร็จ

```ts
readonly results = httpResource<Item[]>(() => ({
  url: '/api/search',
  params: { q: this.keyword() },
}));
// results.value()  results.isLoading()  results.error()
```

## 5. ควรใช้อะไรตอนไหน

**กฎนิ้วโป้งข้อเดียว: ถ้ามันคือ "ค่า" ใช้ signal / ถ้ามันคือ "เหตุการณ์ตามเวลา" ใช้ RxJS แล้วแปลงเป็น signal ที่ขอบ**

### ใช้ Signal เมื่อ

- State ในคอมโพเนนต์ และ derived state ทุกชนิด
- ทุกอย่างที่ bind เข้า template (เลิกใช้ `async` pipe ได้)
- `@Input` / `@Output` / `@ViewChild` → `input()` / `output()` / `viewChild()`
- Shared state ใน service (`signal` + `computed` แทน `BehaviorSubject` + `asObservable()`)
- แอปที่จะไป **zoneless** — signal คือสิ่งที่บอก Angular ได้แม่นว่าต้อง re-render ตรงไหน

### ใช้ RxJS เมื่อ

- ต้องจัดการ **เวลา**: `debounceTime`, `throttleTime`, `interval`, polling
- ต้อง **ยกเลิกงานเก่า**: พิมพ์ค้นหารัว ๆ แล้วต้องทิ้ง request เก่า → `switchMap` (signal ทำเองไม่ได้)
- Retry / backoff / error recovery
- Stream จริง ๆ: WebSocket, SSE, event จาก third-party lib
- ประสานงาน async หลายทางที่ซับซ้อน (`forkJoin`, `combineLatest`, `concatMap`)

### ตัวอย่างผสมที่เป็นรูปแบบมาตรฐาน

```ts
export class SearchComponent {
  private http = inject(HttpClient);

  readonly keyword = signal('');                 // state → signal

  readonly results = toSignal(                   // async pipeline → RxJS
    toObservable(this.keyword).pipe(
      debounceTime(300),
      distinctUntilChanged(),
      filter(k => k.length >= 2),
      switchMap(k => this.http.get<Item[]>('/api/search', { params: { q: k } })),
    ),
    { initialValue: [] as Item[] },              // → กลับมาเป็น signal ที่ขอบ
  );

  readonly resultCount = computed(() => this.results().length);
}
```

Template ไม่ต้องรู้เลยว่าข้างในมี RxJS — เห็นแค่ `results()` กับ `resultCount()`

## 6. กับดักที่เจอบ่อย

**ใช้ `effect()` ไปซิงก์ state** — อาการนี้พบบ่อยที่สุด

```ts
// ❌ อย่าทำ
effect(() => this.fullName.set(`${this.first()} ${this.last()}`));

// ✅ ใช้ computed
readonly fullName = computed(() => `${this.first()} ${this.last()}`);
```

`effect` ควรใช้เฉพาะตอนต้อง "ออกไปข้างนอก" เท่านั้น ถ้าเขียน signal ใน effect เมื่อไหร่ ให้ถามตัวเองก่อนว่า `computed` หรือ `linkedSignal` ทำแทนได้ไหม

**แก้ object แบบ mutate** — signal เทียบด้วย `Object.is` ถ้าแก้ของเดิมในที่เดิมมันจะไม่รู้ว่าเปลี่ยน (เมธอด `mutate()` ถูกถอดออกไปแล้ว)

```ts
// ❌ items().push(newItem);
// ✅
items.update(list => [...list, newItem]);
```

**อ่าน signal โดยไม่อยากให้ track** — ใช้ `untracked()` ครอบ

**`effect` ทำงานแบบ async** — ถูกจัดคิวหลัง change detection ไม่ได้รันทันทีที่ set ค่า อย่าเขียนเทสต์หรือ logic ที่พึ่งพาลำดับแบบ synchronous

---

**สรุปสั้น:** signal = state แบบ sync, อ่านง่าย, ไม่มี leak, รองรับ zoneless → ใช้เป็นค่าเริ่มต้นสำหรับ state ทุกอย่างในคอมโพเนนต์และ service ส่วน RxJS = เครื่องมือจัดการเวลาและการยกเลิกงาน ซึ่งยังไม่มีอะไรมาแทนได้ → เก็บไว้ใช้ในชั้น async แล้วแปลงเป็น signal ก่อนส่งเข้า template
