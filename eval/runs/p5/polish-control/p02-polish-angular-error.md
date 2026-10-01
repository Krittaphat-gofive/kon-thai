เกลาให้แล้วครับ เนื้อหา โครงหัวข้อ และโค้ดในบล็อกทั้งหมดคงเดิม (รวมถึงคอมเมนต์ในโค้ด ที่ไม่ได้แตะตามที่สั่งไว้) ที่เปลี่ยนคือสำนวนกับการตัดขีดยาวออกให้อ่านลื่นแบบที่คนไทยเขียนจริง

---

## NG0100 คืออะไร

เวลารัน `ng serve` (dev mode) Angular จะวน change detection **สองรอบ** ต่อหนึ่ง tick

1. รอบจริง: คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจซ้ำ (`checkNoChanges`): คำนวณใหม่อีกครั้งแล้วเทียบว่าได้ค่าเดิมไหม

ถ้าค่าไม่ตรงกัน แปลว่ามีโค้ดไปเปลี่ยน state **หลังจาก** Angular เช็ก view นั้นไปแล้วใน tick เดียวกัน เลยฟ้อง NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าตัวที่มีปัญหาเป็น binding แบบ boolean ส่วนใหญ่ก็หนีไม่พ้น `*ngIf`, `[disabled]`, `[class.xxx]` หรือ flag พวก `isLoading` / `isOpen`

**ข้อควรระวัง:** รอบที่สองมีเฉพาะตอน dev mode พอ build production แล้วจะไม่ขึ้น error ก็จริง แต่ **bug ยังอยู่ครบ** คือ UI อาจค้างค่าเก่าไว้ 1 เฟรม เพราะงั้นอย่าแก้ด้วยการไปรัน production แล้วสรุปว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child เปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิก เจอบ่อยสุด)**

Angular เช็ก parent ก่อน แล้วค่อยรัน `ngOnInit` ของ child พอ child ไปแก้ค่ากลับขึ้นไป Angular ก็เช็ก parent ไปเรียบร้อยแล้ว

```ts
// child.component.ts
ngOnInit() {
  this.loadingChange.emit(true);   // parent ถูก check ไปแล้ว → NG0100
}
```

**2. เปลี่ยน property ที่ bind ไว้ใน `ngAfterViewInit` / `ngAfterViewChecked`**

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

**4. Service / BehaviorSubject ที่ยิง `.next()` แบบ synchronous ตอน component init**

**5. Third-party component** (CDK overlay, ng-bootstrap, PrimeNG) ที่ toggle state เองตอน init

## วิธีไล่หาต้นเหตุ

- กาง stack trace ใน console ให้สุด เฟรมที่อยู่**ถัดลงมาจาก** `checkNoChanges` / `checkNoChangesInternal` คือ component ต้นเหตุ Angular เวอร์ชันใหม่ ๆ จะบอกชื่อ template/component มาให้เลย
- เปิด Angular DevTools ดู component tree
- ถ้ายังไม่เจอ ก็คอมเมนต์ template ออกทีละส่วนเพื่อ bisect หา binding แบบ boolean ที่เป็นตัวปัญหา

## วิธีแก้ (ไล่จากดีที่สุดลงมา)

**1. ขยับจุดที่เปลี่ยนค่าให้เกิดเร็วขึ้น (ดีที่สุด)**

ย้ายไปทำใน `ngOnInit` ของ parent หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงค่ากลับขึ้นไป

**2. ทำให้ค่า derive ออกมาเอง แทนที่จะไล่ mutate**

```ts
// แทนที่จะ set flag ทีหลัง ให้คำนวณจาก source เดียว
get isDisabled() { return this.form.invalid || this.saving; }
```

**3. ถ้าจำเป็นต้องวัด DOM จริง ๆ ให้ใช้ `ChangeDetectorRef.detectChanges()`**

```ts
constructor(private cdr: ChangeDetectorRef) {}

ngAfterViewInit() {
  this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  this.cdr.detectChanges();   // บังคับ re-check view นี้ — ถูกต้องตามหลักสำหรับเคสวัด DOM
}
```
ถ้า component เป็น `OnPush` อาจต้องเปลี่ยนไปใช้ `markForCheck()` แทน

**4. Angular 16+ ใช้ `afterNextRender`** ซึ่งออกแบบมาสำหรับงานที่ต้องรอ DOM โดยเฉพาะ

```ts
import { afterNextRender } from '@angular/core';

constructor() {
  afterNextRender(() => {
    this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  });
}
```

**5. เลื่อนไป tick ถัดไป (ใช้ได้ แต่เป็นการแก้ปลายเหตุ)**

```ts
Promise.resolve().then(() => this.isLoading = true);   // microtask
// หรือ setTimeout(() => ..., 0)
```
ใช้แล้วหายชัวร์ แต่แลกกับ CD ที่เพิ่มมาอีกรอบและอาจเห็นภาพกระพริบแวบหนึ่ง เก็บไว้ใช้ตอนที่แก้ที่โครงสร้างไม่ได้จริง ๆ

**6. ถ้าใช้ Angular 17+ ลองพิจารณา signals** ตัว `signal` + `computed` ตัดปัญหากลุ่มนี้ไปได้เกือบหมด เพราะค่าทุกตัว derive มาจาก source เดียวและนิ่งอยู่ภายใน tick เดียวกัน

## สิ่งที่ไม่ควรทำ

- หว่าน `setTimeout` ไปทั่วโดยไม่หาสาเหตุ
- ปิด dev mode หรือ `enableProdMode()` เพื่อให้ error หายไป เพราะ bug ยังอยู่ แค่ Angular เลิกเตือนเฉย ๆ

---

ถ้าเอาโค้ด component กับ template ที่เป็นต้นเหตุมาแปะให้ดู (ดูจาก stack trace ว่าชี้ไปไฟล์ไหน) เดี๋ยวผมช่วยชี้จุดและแก้ให้ตรงเคสเลยครับ
