ไม่ได้รันคำสั่งเช็ค skill (ติด permission) เลยทำให้เลยครับ — งานนี้เป็นงานเกลาภาษาล้วน ๆ ทำได้ตรง ๆ อยู่แล้ว

เกลาแล้วตามนี้ (เนื้อหา โครงสร้าง และโค้ดคงเดิมทุกจุด):

---

## NG0100 คืออะไร

เวลารัน `ng serve` (dev mode) Angular จะรัน change detection **สองรอบ** ต่อหนึ่ง tick

1. รอบจริง — คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจซ้ำ (`checkNoChanges`) — คำนวณใหม่อีกที แล้วเทียบว่าค่ายังเท่าเดิมอยู่ไหม

ถ้าค่าไม่ตรงกัน แปลว่ามีโค้ดไปเปลี่ยน state **หลังจาก** Angular เช็ค view นั้นไปแล้วใน tick เดียวกัน Angular ก็เลยโยน NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าตัวที่มีปัญหาเป็น binding แบบ boolean ซึ่งส่วนใหญ่ก็หนีไม่พ้น `*ngIf`, `[disabled]`, `[class.xxx]` หรือพวก flag อย่าง `isLoading` / `isOpen`

**สำคัญ:** รอบที่ 2 มีแค่ใน dev mode — build production แล้วจะไม่ error ก็จริง แต่ **bug ยังอยู่** คือ UI อาจค้างแสดงค่าเก่าอยู่ 1 เฟรม เพราะงั้นอย่าแก้ด้วยการไป build prod แล้วบอกว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child ไปเปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิกสุด)**

Angular เช็ค parent เสร็จก่อน แล้วค่อยรัน `ngOnInit` ของ child พอ child ยิงค่ากลับขึ้นไป parent ก็เช็คผ่านไปแล้ว

```ts
// child.component.ts
ngOnInit() {
  this.loadingChange.emit(true);   // parent ถูก check ไปแล้ว → NG0100
}
```

**2. ไปเปลี่ยน property ที่ bind ไว้ใน `ngAfterViewInit` / `ngAfterViewChecked`**

```ts
@ViewChild('box') box!: ElementRef;

ngAfterViewInit() {
  this.isOverflowing = this.box.nativeElement.scrollHeight > 100;  // NG0100
}
```

**3. Getter / method ใน template ที่คืนค่าใหม่ทุกครั้งที่เรียก**

```html
<div *ngIf="hasErrors()">   <!-- ถ้า hasErrors() มี side effect หรือค่าไม่ stable -->
```
รวมถึงพวก `new Date()`, `arr.filter(...)` (คืน reference ใหม่ทุกครั้ง), `Math.random()`

**4. Service / BehaviorSubject ที่ `.next()` แบบ synchronous ตอน component init**

**5. Third-party component** (CDK overlay, ng-bootstrap, PrimeNG) ที่ toggle state ของตัวเองตอน init

## วิธีไล่หาจุดที่ผิด

- กาง stack trace ใน console ให้สุด — frame ที่อยู่**ถัดลงมาจาก** `checkNoChanges` / `checkNoChangesInternal` คือ component ต้นเหตุ Angular เวอร์ชันใหม่ ๆ จะบอกชื่อ template/component มาให้ด้วย
- ใช้ Angular DevTools ไล่ดู component tree
- ถ้ายังไม่เจอ ก็ comment template ออกทีละส่วนเพื่อ bisect หา binding ตัวที่เป็น boolean

## วิธีแก้ (ไล่จากดีที่สุดลงมา)

**1. ย้ายจุดที่เปลี่ยนค่าให้เกิดเร็วขึ้น — ทางที่ดีที่สุด**

ย้ายไปไว้ใน `ngOnInit` ของ parent หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงกลับขึ้นไป

**2. ทำให้ค่าเป็น derived แทนที่จะ mutate**

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
ถ้าใช้ `OnPush` อาจต้องเปลี่ยนไปใช้ `markForCheck()` แทน

**4. Angular 16+ ใช้ `afterNextRender`** — ตัวนี้ออกแบบมาสำหรับงานที่ต้องรอ DOM โดยเฉพาะ

```ts
import { afterNextRender } from '@angular/core';

constructor() {
  afterNextRender(() => {
    this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  });
}
```

**5. เลื่อนไป tick ถัดไป — ใช้ได้ แต่เป็นแค่ยาแก้ปวด**

```ts
Promise.resolve().then(() => this.isLoading = true);   // microtask
// หรือ setTimeout(() => ..., 0)
```
ได้ผลแน่นอน แต่แลกมาด้วย CD cycle ที่เพิ่มขึ้น แล้วก็อาจเห็นภาพกระพริบ ควรใช้ต่อเมื่อแก้ที่โครงสร้างไม่ได้จริง ๆ

**6. ถ้าใช้ Angular 17+ ลองพิจารณา signals** — `signal` + `computed` ตัดปัญหาแนวนี้ไปได้เกือบหมด เพราะค่า derive มาจาก source เดียวและนิ่งอยู่ภายใน tick เดียวกัน

## สิ่งที่ไม่ควรทำ

- โรย `setTimeout` ไปทั่วโดยไม่หาสาเหตุ
- ปิด dev mode / `enableProdMode()` เพื่อให้ error หาย — bug ยังอยู่ แค่ไม่มีใครเตือนแล้วเฉย ๆ

---

ถ้าแปะโค้ด component + template ที่เป็นต้นเหตุมาให้ดู (ดูจาก stack trace ว่าชี้ไปไฟล์ไหน) เดี๋ยวผมช่วยชี้จุดแล้วแก้ให้ตรงเคสเลยครับ

---

**สิ่งที่ปรับหลัก ๆ:**
- ลดรูปประโยคแบบแปล: "ตอนรัน" → "เวลารัน", "รอบตรวจสอบ" → "รอบตรวจซ้ำ", "ถูก check ไปแล้ว" (passive) → "Angular เช็ค...ไปแล้ว"
- "ปัญหาคลาสนี้" (จาก *this class of problem*) → "ปัญหาแนวนี้"
- เติมคำเชื่อมที่คนไทยใช้จริงเวลาอธิบายเทคนิค: "ก็เลย", "เพราะงั้น", "พอ...ก็...", "ก็หนีไม่พ้น", "ไล่ดู", "กาง stack trace"
- "ดีที่สุดลงมา" → "ไล่จากดีที่สุดลงมา", "วิธีหาจุดที่ผิด" → "วิธีไล่หาจุดที่ผิด"
- ปิดท้ายข้อ "ไม่ควรทำ" ให้มีน้ำเสียงพูดจริงมากขึ้น ("แค่ไม่มีใครเตือนแล้วเฉย ๆ")
