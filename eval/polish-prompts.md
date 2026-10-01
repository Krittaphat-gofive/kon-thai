# ชุดทดสอบ skill ขัดเกลา

ข้อความที่ให้เกลาเป็นคำตอบจริงของ Claude จากรอบ baseline (r1) ที่มีร่องรอยภาษาแปลหนาแน่นที่สุด

## p01-polish-async | ขัดเกลา
ช่วยเกลาภาษาไทยในคำอธิบายข้างล่างให้เป็นธรรมชาติแบบที่คนไทยเขียน เนื้อหากับโค้ดให้คงเดิม

-----

## สรุปสั้นๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation** — compiler แปลง method ของคุณเป็น **state machine**

### 1. Compiler แปลงเป็น State Machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

ถูกแปลงเป็น struct ที่ implement `IAsyncStateMachine` คร่าวๆ แบบนี้:

```csharp
struct StateMachine : IAsyncStateMachine {
    public int _state;                      // ตอนนี้อยู่ state ไหน
    public AsyncTaskMethodBuilder<int> _builder;
    public int _a;                          // local var → กลายเป็น field
    TaskAwaiter<int> _awaiter;

    public void MoveNext() {
        switch (_state) {
            case -1:
                _awaiter = FetchAsync().GetAwaiter();
                if (!_awaiter.IsCompleted) {
                    _state = 0;
                    _builder.AwaitUnsafeOnCompleted(ref _awaiter, ref this);
                    return;                 // ← คืน thread กลับไป
                }
                goto case 0;
            case 0:
                _a = _awaiter.GetResult();  // กลับมาทำงานต่อตรงนี้
                _builder.SetResult(_a + 1);
                return;
        }
    }
}
```

**หัวใจคือ:** local variables กลายเป็น fields เพราะ stack หายไปตอน `return` — state ต้องเก็บไว้บน heap

### 2. จุดสำคัญที่คนมักเข้าใจผิด

| เรื่อง | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** — I/O จริงใช้ IOCP (OS callback) ไม่มี thread รออยู่เลย |
| `await` บล็อก thread | **ไม่** — มัน `return` ออกไปเลย thread ไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่** — ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer แล้ว) มันวิ่งต่อแบบ synchronous ไม่ alloc อะไรเลย |

State machine เป็น `struct` และอยู่บน stack **จนกว่า** จะเจอ await ที่ยังไม่เสร็จจริง ถึงจะถูก box ขึ้น heap — เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุน

### 3. กลับมาที่ไหน? → SynchronizationContext

ตอน `AwaitUnsafeOnCompleted` มันจะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ปัจจุบันไว้ พอ operation เสร็จก็ post `MoveNext` กลับไปที่นั่น

- **ASP.NET Core / Console** — ไม่มี context → resume บน thread pool thread ใดก็ได้
- **WPF / WinForms** — มี context → resume บน UI thread (เลยแก้ UI ต่อได้เลย)
- `ConfigureAwait(false)` — สั่งว่า "ไม่ต้อง capture" ลด overhead และกัน deadlock ในไลบรารี

### 4. Exceptions

exception ใน `MoveNext` ถูก catch แล้วส่งเข้า `_builder.SetException(ex)` → เก็บไว้ใน Task → ตอน `GetResult()` จะถูก rethrow ด้วย `ExceptionDispatchInfo` ซึ่ง**รักษา stack trace เดิมไว้** (ไม่เหมือน `throw ex;` ที่ทำ stack trace หาย)

---

**บรรทัดเดียว:** compiler หั่น method ของคุณเป็นชิ้นๆ ตาม `await` แล้วเย็บกลับเป็น state machine ที่เรียก `MoveNext()` ซ้ำๆ — แต่ละครั้งทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรอ

## p02-polish-angular-error | ขัดเกลา
ช่วยเกลาภาษาไทยในคำอธิบายข้างล่างให้เป็นธรรมชาติแบบที่คนไทยเขียน เนื้อหากับโค้ดให้คงเดิม

-----

## NG0100 คืออะไร

ตอนรัน `ng serve` (dev mode) Angular จะรัน change detection **สองรอบ** ต่อหนึ่ง tick:

1. รอบจริง — คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจสอบ (`checkNoChanges`) — คำนวณใหม่อีกครั้งแล้วเทียบว่าค่าเท่าเดิมไหม

ถ้าค่าต่างกัน แปลว่ามีโค้ดไปเปลี่ยน state **หลังจาก** view นั้นถูก check ไปแล้วใน tick เดียวกัน → โยน NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าเป็น binding แบบ boolean — ส่วนใหญ่คือ `*ngIf`, `[disabled]`, `[class.xxx]`, หรือ flag พวก `isLoading` / `isOpen`

**สำคัญ:** รอบที่ 2 มีเฉพาะ dev mode — build production จะไม่ error แต่ **bug ยังอยู่** คือ UI อาจแสดงค่าเก่าค้างไว้ 1 เฟรม ดังนั้นอย่าแก้ด้วยการไปรัน production แล้วบอกว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child เปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิกที่สุด)**

Angular เช็ค parent ก่อน แล้วค่อยรัน `ngOnInit` ของ child — ถ้า child ไปแก้ค่ากลับขึ้นไป parent ก็ถูกเช็คไปแล้ว

```ts
// child.component.ts
ngOnInit() {
  this.loadingChange.emit(true);   // parent ถูก check ไปแล้ว → NG0100
}
```

**2. เปลี่ยน property ที่ bind ใน `ngAfterViewInit` / `ngAfterViewChecked`**

```ts
@ViewChild('box') box!: ElementRef;

ngAfterViewInit() {
  this.isOverflowing = this.box.nativeElement.scrollHeight > 100;  // NG0100
}
```

**3. Getter / method ใน template ที่คืนค่าใหม่ทุกครั้ง**

```html
<div *ngIf="hasErrors()">   <!-- ถ้า hasErrors() มี side effect หรือค่าไม่ stable -->
```
รวมถึงพวก `new Date()`, `arr.filter(...)` (คืน reference ใหม่), `Math.random()`

**4. Service / BehaviorSubject ที่ `.next()` แบบ synchronous ตอน component init**

**5. Third-party component** (CDK overlay, ng-bootstrap, PrimeNG) ที่ toggle state เองตอน init

## วิธีหาจุดที่ผิด

- เปิด stack trace ใน console ให้สุด — frame ที่อยู่**ถัดลงไปจาก** `checkNoChanges` / `checkNoChangesInternal` คือ component ที่เป็นต้นเหตุ Angular เวอร์ชันใหม่จะบอกชื่อ template/component มาด้วย
- ใช้ Angular DevTools ดู component tree
- ถ้ายังไม่เจอ: comment template ออกทีละส่วนเพื่อ bisect หา binding ตัวที่เป็น boolean

## วิธีแก้ (เรียงจากดีที่สุดลงมา)

**1. ย้ายจุดที่เปลี่ยนค่าให้เร็วขึ้น — ดีที่สุด**

ย้ายไป `ngOnInit` ของ parent, หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงกลับขึ้นไป

**2. ทำให้ค่าเป็น derived แทนการ mutate**

```ts
// แทนที่จะ set flag ทีหลัง ให้คำนวณจาก source เดียว
get isDisabled() { return this.form.invalid || this.saving; }
```

**3. ถ้าจำเป็นต้องวัด DOM จริง ๆ → `ChangeDetectorRef.detectChanges()`**

```ts
constructor(private cdr: ChangeDetectorRef) {}

ngAfterViewInit() {
  this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  this.cdr.detectChanges();   // บังคับ re-check view นี้ — ถูกต้องตามหลักสำหรับเคสวัด DOM
}
```
ถ้าใช้ `OnPush` อาจต้องใช้ `markForCheck()` แทน

**4. Angular 16+ ใช้ `afterNextRender`** — ออกแบบมาสำหรับงานที่ต้องรอ DOM โดยเฉพาะ

```ts
import { afterNextRender } from '@angular/core';

constructor() {
  afterNextRender(() => {
    this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  });
}
```

**5. เลื่อนไป tick ถัดไป — ใช้ได้แต่เป็นยาแก้ปวด**

```ts
Promise.resolve().then(() => this.isLoading = true);   // microtask
// หรือ setTimeout(() => ..., 0)
```
ใช้ได้ผลแน่นอน แต่เพิ่ม CD cycle และอาจเห็นภาพกระพริบ — ควรใช้ต่อเมื่อแก้ที่โครงสร้างไม่ได้จริง ๆ

**6. ถ้าใช้ Angular 17+ พิจารณา signals** — `signal` + `computed` ตัดปัญหาคลาสนี้ไปเกือบหมด เพราะค่า derive มาจาก source เดียวและ stable ภายใน tick

## สิ่งที่ไม่ควรทำ

- โรย `setTimeout` ทุกที่โดยไม่หาสาเหตุ
- ปิด dev mode / `enableProdMode()` เพื่อให้ error หาย — bug ยังอยู่ แค่ไม่เตือน

---

ถ้าแปะโค้ด component + template ที่เป็นต้นเหตุมาให้ดู (ดูจาก stack trace ว่าชี้ไปที่ไฟล์ไหน) ผมช่วยชี้จุดและแก้ให้ตรงเคสได้เลยครับ

## p03-polish-cqrs | ขัดเกลา
ช่วยเกลาภาษาไทยในคำอธิบายข้างล่างให้เป็นธรรมชาติแบบที่คนไทยเขียน เนื้อหากับโค้ดให้คงเดิม

-----

ไดเรกทอรีงานว่างเปล่า ผมเลยยังไม่เห็นโค้ดระบบ HR ของคุณ — จะอธิบาย CQRS ให้ก่อน แล้วให้เกณฑ์ตัดสินว่าเคสไหนคุ้ม/ไม่คุ้ม พร้อมคำถามที่ต้องรู้เพื่อฟันธงได้จริง

## CQRS คืออะไร

**Command Query Responsibility Segregation** = แยก "ทางเขียน" กับ "ทางอ่าน" ออกจากกันเป็นคนละโมเดล

แบบ CRUD ปกติ เราใช้โมเดลเดียวทำทุกอย่าง — `Employee` entity ตัวเดียวกัน ทั้งตอนบันทึก ตอนดึงไปโชว์ ตอนทำรายงาน ปัญหาคือความต้องการของสองฝั่งมันสวนทางกัน ฝั่งเขียนอยากได้โมเดลที่รักษา business rule ได้แน่น (เช่น "วันลาคงเหลือห้ามติดลบ") ส่วนฝั่งอ่านแค่อยากได้ข้อมูลแบนๆ ตรงกับหน้าจอ ไม่ต้อง join 8 ตาราง

CQRS แยกเป็น:
- **Command side** — รับคำสั่ง (`ApproveLeaveRequest`, `AdjustSalary`) → validate → เปลี่ยน state ผ่าน domain model ปกติไม่คืนข้อมูลกลับนอกจาก success/fail
- **Query side** — อ่านจาก read model ที่ปั้นมาเพื่อหน้าจอนั้นโดยเฉพาะ ข้าม domain model ไปเลย ยิง SQL ตรงเข้า view หรือตาราง denormalized ได้

## มันมี 3 ระดับ ซึ่งคนมักเหมารวมเป็นอันเดียว

| ระดับ | ทำอะไร | ต้นทุน |
|---|---|---|
| 1. แยกแค่ในโค้ด | แยก `CommandHandler` / `QueryHandler` ใช้ DB เดียวกัน (สไตล์ MediatR) | ต่ำมาก ได้ความชัดเจนของโค้ดฟรีๆ |
| 2. แยก read model ใน DB เดียวกัน | ทำ materialized view / ตาราง denormalized สำหรับ query หนักๆ | ปานกลาง ยังอยู่ใน transaction เดียวกันได้ |
| 3. แยก datastore คนละที่ | เขียนลง Postgres อ่านจาก Elasticsearch/Redis sync ด้วย event | สูง ได้ **eventual consistency** มาเป็นของแถม |

ที่เจ็บคือระดับ 3 — eventual consistency แปลว่า user กดบันทึกแล้ว refresh อาจยังไม่เห็นข้อมูลใหม่ ใน HR เรื่องนี้พังง่าย เพราะ HR มี flow อนุมัติเยอะ ("ผมอนุมัติไปแล้วทำไมยังขึ้นรอดำเนินการ") ต้องออกแบบ UX รองรับ ไม่ใช่แค่เรื่อง backend

อีกอย่าง: **CQRS ≠ Event Sourcing** สองตัวนี้มักมาคู่กันจนคนเข้าใจผิดว่าต้องใช้ด้วยกัน จริงๆ แยกกันได้

## ระบบ HR เหมาะไหม

ลักษณะที่ HR มักเป็น และตีความได้ว่า:

**เข้าทาง CQRS**
- read-heavy ชัดเจน — org chart, ค้นหาพนักงาน, dashboard, รายงาน ปริมาณอ่านมากกว่าเขียนหลายสิบเท่า
- รายงานกับ payroll ต้อง join หนักและ aggregate ข้าม period — พวกนี้ทำ read model แยกแล้วดีขึ้นเห็นๆ
- ต้องการ audit trail เข้ม (ประวัติปรับเงินเดือน เลื่อนตำแหน่ง โอนย้าย) — ตรงนี้ event sourcing เฉพาะ aggregate นั้นน่าสนใจ เพราะ HR ต้องตอบได้ว่า "ณ วันที่ 1 ม.ค. ปีที่แล้ว คนนี้สังกัดแผนกไหน เงินเดือนเท่าไร"

**ไม่เข้าทาง**
- transaction volume ปกติต่ำ พนักงานหลักพันถึงหลักหมื่น ไม่ใช่ระบบ e-commerce ที่ยิงวินาทีละพัน request — เหตุผลเรื่อง scale ที่คนมักอ้างเพื่อใช้ CQRS แทบไม่เกิดกับ HR
- หลายส่วนเป็น CRUD ตรงๆ จริงๆ — แก้ที่อยู่ แก้เบอร์โทร ตั้งค่า master data ประเภทการลา ทำ CQRS ตรงนี้คือเพิ่มไฟล์ 4 ไฟล์เพื่องานที่ `UPDATE` บรรทัดเดียวจบ
- บาง flow ต้องการ read-after-write ทันที — ยอดวันลาคงเหลือ, สถานะอนุมัติ, ผลคำนวณ payroll ถ้า eventual consistency เข้ามาตรงนี้คือหายนะ

## คำแนะนำ

**อย่าใช้ทั้งระบบ** — ใช้เป็นราย bounded context นี่คือจุดที่โปรเจกต์ส่วนใหญ่พลาด คือตัดสินใจระดับสถาปัตยกรรมทั้งก้อนแทนที่จะเลือกเฉพาะที่มีปัญหาจริง

แนวที่ผมจะทำกับระบบ HR:
1. **ระดับ 1 ทั้งระบบ** — แยก command/query handler ถือเป็นการจัดระเบียบโค้ดที่ดี ต้นทุนเกือบเป็นศูนย์ ไม่มี eventual consistency เข้ามาเกี่ยว
2. **ระดับ 2 เฉพาะรายงาน/dashboard/search** — ทำ read model แยกตรงที่ query ช้าจริง วัดก่อนค่อยทำ
3. **ระดับ 3 เก็บไว้ก่อน** — จนกว่าจะมีเหตุผลที่วัดได้ เช่น รายงาน lock ตาราง production จนคนลางานไม่ได้
4. **Event sourcing เฉพาะ aggregate ที่ต้องการประวัติ** — employment history, compensation ส่วนอื่นไม่ต้อง

## ขอข้อมูลเพิ่มเพื่อฟันธงให้ชัด

คำตอบข้างบนเป็นกรอบทั่วไป จะชี้เฉพาะเจาะจงได้ต้องรู้:

1. **ตอนนี้เจอปัญหาอะไร** — query ช้า? รายงานทำ DB ตาย? โค้ดรก business logic กระจาย? หรือกำลังจะเขียนใหม่? คำตอบต่างกันคนละเรื่องเลย
2. **stack อะไร** — .NET / Node / Java และใช้ ORM อะไร
3. **ขนาด** — พนักงานกี่คน กี่ tenant concurrent user ช่วง peak (ต้นเดือน/ปิด payroll) ประมาณเท่าไร
4. **ทีมกี่คน** และเคยทำ CQRS มาก่อนไหม — ตัวนี้สำคัญพอๆ กับเรื่องเทคนิค เพราะ CQRS ที่ทีมไม่คุ้นมักกลายเป็น CRUD ที่มีไฟล์เยอะขึ้นเฉยๆ

ถ้าชี้ path โค้ดระบบ HR มาให้ได้ ผมอ่านแล้วบอกได้เลยว่าจุดไหนควรแยก read model ก่อน
