เกลาให้แล้วครับ เนื้อหาและโค้ดคงเดิมทุกจุด ปรับเฉพาะสำนวน

---

## NG0100 คืออะไร

เวลารัน `ng serve` (dev mode) Angular จะรัน change detection **สองรอบ** ต่อหนึ่ง tick

1. รอบจริง: คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจสอบ (`checkNoChanges`): คำนวณใหม่อีกรอบแล้วเทียบว่าได้ค่าเท่าเดิมไหม

ถ้าค่าไม่ตรงกัน แปลว่ามีโค้ดไปแก้ state **หลังจาก** ที่ Angular เช็ก view นั้นไปแล้วใน tick เดียวกัน → โยน NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าเป็น binding แบบ boolean ส่วนใหญ่หนีไม่พ้น `*ngIf`, `[disabled]`, `[class.xxx]` หรือ flag พวก `isLoading` / `isOpen`

**สำคัญ:** รอบที่ 2 มีเฉพาะ dev mode เท่านั้น build production แล้วจะไม่ error แต่ **bug ยังอยู่ครบ** คือ UI มีโอกาสค้างค่าเก่าไว้ 1 เฟรม ดังนั้นอย่าแก้ด้วยการไป build production แล้วสรุปว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child ไปเปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิกที่สุด)**

Angular เช็ก parent ก่อน แล้วค่อยรัน `ngOnInit` ของ child พอ child แก้ค่าย้อนขึ้นไป parent ก็ผ่านการเช็กไปเรียบร้อยแล้ว

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
รวมถึงพวก `new Date()`, `arr.filter(...)` (คืน reference ใหม่ทุกรอบ), `Math.random()`

**4. Service / BehaviorSubject ที่ยิง `.next()` แบบ synchronous ตอน component init**

**5. Third-party component** (CDK overlay, ng-bootstrap, PrimeNG) ที่ toggle state ของตัวเองตอน init

## วิธีหาจุดที่ผิด

- กาง stack trace ใน console ให้สุด frame ที่อยู่**ถัดลงไปจาก** `checkNoChanges` / `checkNoChangesInternal` คือ component ต้นเหตุ Angular เวอร์ชันใหม่ ๆ จะบอกชื่อ template/component มาให้ด้วย
- เปิด Angular DevTools ดู component tree ประกอบ
- ถ้ายังหาไม่เจอ ลอง comment template ออกทีละส่วนเพื่อ bisect หา binding ตัวที่เป็น boolean

## วิธีแก้ (เรียงจากดีที่สุดลงมา)

**1. ขยับจุดที่เปลี่ยนค่าให้เกิดเร็วขึ้น (ทางที่ดีที่สุด)**

ย้ายไปไว้ใน `ngOnInit` ของ parent หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงค่ากลับขึ้นไป

**2. ทำให้ค่าเป็น derived แทนการ mutate**

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
ถ้าใช้ `OnPush` อาจต้องเปลี่ยนไปใช้ `markForCheck()` แทน

**4. Angular 16+ ใช้ `afterNextRender`** ตัวนี้ออกแบบมาสำหรับงานที่ต้องรอ DOM โดยเฉพาะ

```ts
import { afterNextRender } from '@angular/core';

constructor() {
  afterNextRender(() => {
    this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  });
}
```

**5. เลื่อนไป tick ถัดไป (ใช้ได้อยู่ แต่เป็นแค่ยาแก้ปวด)**

```ts
Promise.resolve().then(() => this.isLoading = true);   // microtask
// หรือ setTimeout(() => ..., 0)
```
ได้ผลแน่นอน แต่แลกมากับ CD cycle ที่เพิ่มขึ้น และบางทีเห็น UI กระพริบ ควรใช้ตอนที่แก้ที่โครงสร้างไม่ได้จริง ๆ เท่านั้น

**6. ถ้าอยู่บน Angular 17+ ลองพิจารณา signals** `signal` + `computed` ตัดปัญหากลุ่มนี้ไปได้เกือบหมด เพราะค่าทุกตัว derive มาจาก source เดียว และนิ่งอยู่แล้วภายใน tick เดียวกัน

## สิ่งที่ไม่ควรทำ

- โรย `setTimeout` ไปทั่วโดยไม่หาสาเหตุ
- ปิด dev mode หรือเรียก `enableProdMode()` เพื่อให้ error เงียบไป bug ยังอยู่ แค่ไม่มีใครเตือนแล้ว

---

ถ้าแปะโค้ด component + template ที่เป็นต้นเหตุมาให้ดู (ดูจาก stack trace ว่าชี้ไปไฟล์ไหน) ผมช่วยไล่จุดที่พังแล้วแก้ให้ตรงเคสได้เลยครับ

---

สิ่งที่ปรับ:

- ตัดเครื่องหมาย em dash ออกทั้งหมด เปลี่ยนเป็น colon วงเล็บ หรือเว้นวรรคแทน
- ตัดรูป "ถูก..." ที่ไม่จำเป็นออก เช่น "view นั้นถูก check ไปแล้ว" → "Angular เช็ก view นั้นไปแล้ว", "parent ก็ถูกเช็คไปแล้ว" → "parent ก็ผ่านการเช็กไปเรียบร้อยแล้ว"
- สะกดตามราชบัณฑิตฯ: เช็ค → เช็ก, เว้นวรรคหน้าไม้ยมก (จริง ๆ, ใหม่ ๆ)
- เกลาคำกริยาให้เป็นภาษาที่ dev ไทยใช้จริง: เปิด stack trace → กาง, ที่ `.next()` → ที่ยิง `.next()`, ย้ายให้เร็วขึ้น → ขยับให้เกิดเร็วขึ้น
- ในบล็อกโค้ดไม่แตะอะไรเลยตามที่สั่ง ดังนั้นคอมเมนต์ `// parent ถูก check ไปแล้ว` กับ `// บังคับ re-check view นี้ — ...` ยังมี ถูก-passive และ em dash ค้างอยู่ ถ้าอยากให้เกลาส่วนนี้ด้วยบอกได้ครับ
