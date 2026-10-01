เกลาแล้วครับ เนื้อหากับโค้ดคงเดิมทุกจุด

---

## NG0100 คืออะไร

ตอนรัน `ng serve` (dev mode) Angular จะรัน change detection **สองรอบ** ต่อหนึ่ง tick:

1. รอบจริง: คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจสอบ (`checkNoChanges`): คำนวณใหม่อีกครั้งแล้วเทียบว่าค่าเท่าเดิมไหม

ถ้าค่าต่างกัน แปลว่ามีโค้ดไปเปลี่ยน state **หลังจาก** ที่ Angular check view นั้นไปแล้วใน tick เดียวกัน Angular ก็เลยโยน NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าเป็น binding แบบ boolean ส่วนใหญ่ก็เป็นพวก `*ngIf`, `[disabled]`, `[class.xxx]` หรือ flag อย่าง `isLoading` / `isOpen`

**สำคัญ:** รอบที่ 2 มีเฉพาะ dev mode พอ build production แล้วจะไม่ error แต่ **bug ยังอยู่** คือ UI อาจแสดงค่าเก่าค้างไว้ 1 เฟรม เพราะงั้นอย่าไปรัน production แล้วบอกว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child เปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิกที่สุด)**

Angular เช็ก parent ก่อน แล้วค่อยรัน `ngOnInit` ของ child ถ้า child ไปแก้ค่ากลับขึ้นไป Angular ก็เช็ก parent ไปแล้ว

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

- เปิด stack trace ใน console ให้สุด frame ที่อยู่**ถัดลงไปจาก** `checkNoChanges` / `checkNoChangesInternal` คือ component ที่เป็นต้นเหตุ ส่วน Angular เวอร์ชันใหม่ ๆ จะบอกชื่อ template/component มาให้ด้วย
- ใช้ Angular DevTools ดู component tree
- ถ้ายังไม่เจอ: comment template ออกทีละส่วนเพื่อ bisect หา binding ตัวที่เป็น boolean

## วิธีแก้ (เรียงจากดีที่สุดลงมา)

**1. ย้ายจุดที่เปลี่ยนค่าให้เร็วขึ้น (ดีที่สุด)**

ย้ายไป `ngOnInit` ของ parent หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงกลับขึ้นไป

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

**4. Angular 16+ ใช้ `afterNextRender`** ตัวนี้ออกแบบมาสำหรับงานที่ต้องรอ DOM โดยเฉพาะ

```ts
import { afterNextRender } from '@angular/core';

constructor() {
  afterNextRender(() => {
    this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  });
}
```

**5. เลื่อนไป tick ถัดไป (ใช้ได้ แต่เป็นการแก้ที่ปลายเหตุ)**

```ts
Promise.resolve().then(() => this.isLoading = true);   // microtask
// หรือ setTimeout(() => ..., 0)
```
วิธีนี้ได้ผลแน่นอน แต่เพิ่ม CD cycle และอาจเห็นภาพกระพริบ ควรใช้ต่อเมื่อแก้ที่โครงสร้างไม่ได้จริง ๆ

**6. ถ้าใช้ Angular 17+ ลองย้ายไปใช้ signals** `signal` คู่กับ `computed` ตัดปัญหาแบบนี้ไปได้เกือบหมด เพราะค่า derive มาจาก source เดียวและ stable ภายใน tick

## สิ่งที่ไม่ควรทำ

- ใส่ `setTimeout` ไปทั่วโดยไม่หาสาเหตุ
- ปิด dev mode / `enableProdMode()` เพื่อให้ error หาย bug ยังอยู่ แค่ไม่มีใครเตือนแล้ว

---

ถ้าแปะโค้ด component + template ที่เป็นต้นเหตุมาให้ดู (ดูจาก stack trace ว่าชี้ไปที่ไฟล์ไหน) ผมช่วยชี้จุดและแก้ให้ตรงเคสได้เลยครับ

---

## สิ่งที่แก้

- em dash ในเนื้อความ 11 จุด เปลี่ยนเป็นเว้นวรรค วงเล็บ หรือ :
- "ถูก check ไปแล้ว" กับ "ถูกเช็คไปแล้ว" เปลี่ยนเป็นยก Angular ขึ้นมาเป็นประธาน
- เช็ค เปลี่ยนเป็น เช็ก ตามราชบัณฑิตฯ
- สำนวนแปล: ยาแก้ปวด เป็น แก้ที่ปลายเหตุ, โรย setTimeout ทุกที่ เป็น ใส่ setTimeout ไปทั่ว, ตัดปัญหาคลาสนี้ เป็น ตัดปัญหาแบบนี้
- ในโค้ดคงไว้ทุกตัวอักษร รวมถึง em dash ใน comment บรรทัด `this.cdr.detectChanges()` ถ้าอยากให้เกลา comment ในโค้ดด้วยบอกได้ครับ
