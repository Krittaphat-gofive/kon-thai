## มันหมายความว่าอะไร

ในโหมด dev, Angular จะรัน change detection **สองรอบต่อหนึ่ง tick** — รอบแรกอัปเดต DOM จริง รอบที่สองเป็นรอบ "ตรวจทาน" ว่าค่าทุก binding ยังเท่าเดิมไหม

ถ้าค่าของ binding เปลี่ยนระหว่างสองรอบนี้ แปลว่ามีโค้ดไปแก้ state **หลังจาก Angular เช็ค binding นั้นไปแล้วในรอบเดียวกัน** → Angular โยน NG0100 ทิ้ง เพราะถ้าปล่อยไว้ DOM กับ model จะไม่ตรงกัน (view จะค้างค่าเก่าอยู่ 1 tick)

ข้อความ `Previous: 'false' → Current: 'true'` บอกว่าเป็น binding แบบ boolean — เดาได้ว่าพวก `isLoading`, `disabled`, `*ngIf="showX"`, `[class.active]`

> ⚠️ error นี้ **ขึ้นเฉพาะ dev mode** — prod จะเงียบ แต่บั๊กยังอยู่ (view อาจแสดงค่าเก่า 1 เฟรม) อย่าแก้ด้วยการ build prod แล้วบอกว่าหายนะครับ

## สาเหตุที่เจอบ่อย เรียงตามความถี่

1. **เซ็ตค่าใน `ngAfterViewInit`** ที่ template ผูกอยู่ — ตัวนี้คลาสสิกที่สุด เพราะ `ngAfterViewInit` ทำงาน *หลัง* Angular เช็ค binding ของ view ไปแล้ว
2. **Child component แก้ state ของ parent** ตอน `ngOnInit`/`ngAfterViewInit` (ผ่าน `@Output`, shared service, หรือ `BehaviorSubject`)
3. **Getter / method ใน template** ที่คืนค่า object/array ใหม่ทุกครั้ง — identity เปลี่ยนทุกรอบ CD
4. **Subscribe แล้ว emit แบบ synchronous** ระหว่าง CD pass
5. **ชน third-party / CDK overlay** (tooltip, virtual scroll, dialog)

## วิธีหาตัวต้นเหตุ

ขยาย stack trace ใน console — เฟรมที่ชี้ไปที่ `*_Template` หรือชื่อ component ของคุณคือจุดที่ binding อยู่ แล้วหาว่าใครไปเซ็ตค่านั้น ถ้ายังไม่เจอ ใส่ setter ดัก:

```ts
private _isLoading = false;
get isLoading() { return this._isLoading; }
set isLoading(v: boolean) {
  console.trace('isLoading =', v);   // stack trace จะบอกว่าใครเรียก
  this._isLoading = v;
}
```

## วิธีแก้ เรียงจากดีที่สุดไปแย่สุด

### 1. ย้าย logic ให้เกิดก่อน CD pass (ดีที่สุด)

ถ้าไม่ได้ต้องการ DOM จริง ให้ย้ายจาก `ngAfterViewInit` → `ngOnInit` หรือ constructor:

```ts
// ❌ สาย: Angular เช็ค binding ไปแล้ว
ngAfterViewInit() { this.isLoading = true; }

// ✅ ทันรอบแรก
ngOnInit() { this.isLoading = true; }
```

### 2. ใช้ signals (ถ้าโปรเจกต์ขึ้น signal แล้ว)

Derived state ที่เป็น `computed()` จะไม่เกิดปัญหานี้ เพราะไม่ได้ "เซ็ต" ระหว่าง CD แต่คำนวณตาม dependency:

```ts
isLoading = signal(false);
canSubmit = computed(() => !this.isLoading() && this.form().valid);
```

และเลิกใช้ getter แบบนี้ใน template:

```ts
// ❌ คืน array ใหม่ทุกรอบ CD
get activeItems() { return this.items.filter(i => i.active); }

// ✅
activeItems = computed(() => this.items().filter(i => i.active));
```

### 3. `cdr.detectChanges()` — กรณีต้องวัด DOM จริง

ถ้าเลี่ยงไม่ได้เพราะต้องอ่านขนาด element ก่อน (เคสนี้ถือว่า legitimate):

```ts
private cdr = inject(ChangeDetectorRef);

ngAfterViewInit() {
  this.showScrollButton = this.el.nativeElement.scrollWidth > this.el.nativeElement.clientWidth;
  this.cdr.detectChanges();   // สั่งรัน CD รอบใหม่ให้ค่าตรงกันก่อนรอบตรวจทาน
}
```

Angular 17+ มีทางที่สะอาดกว่า — `afterNextRender()` ซึ่งรันหลัง render เสร็จ นอกรอบ CD:

```ts
constructor() {
  afterNextRender(() => {
    this.showScrollButton = /* วัด DOM */;
  });
}
```

### 4. เลื่อนไป microtask (ทางหนีทีไล่)

```ts
Promise.resolve().then(() => this.isLoading = true);
```

ใช้ `Promise.resolve()` ดีกว่า `setTimeout(..., 0)` เพราะเป็น microtask → รันก่อน browser paint จึงไม่เห็นภาพกระพริบ แต่ถือเป็นการปิดอาการ ไม่ใช่แก้ root cause — ควรใช้เมื่อปัญหามาจาก third-party lib ที่แก้ไม่ได้

---

ถ้าบอกได้ว่า binding ตัวไหน (จาก stack trace) และ lifecycle hook ไหนที่เซ็ตค่า ผมช่วยดูให้เจาะจงกว่านี้ได้ครับ
