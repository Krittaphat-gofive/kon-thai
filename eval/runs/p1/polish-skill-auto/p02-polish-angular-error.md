เกลาเสร็จแล้วครับ ฉบับใหม่ linter ผ่าน 0 จุด (ของเดิมติด 20 จุด)

---

## NG0100 คืออะไร

ตอนรัน `ng serve` (dev mode) Angular จะรัน change detection **สองรอบ** ต่อหนึ่ง tick

1. รอบจริง: คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจสอบ (`checkNoChanges`): คำนวณใหม่อีกครั้งแล้วเทียบว่าค่าเท่าเดิมไหม

ถ้าค่าต่างกัน แปลว่ามีโค้ดไปเปลี่ยน state **หลังจาก** Angular เช็ก view นั้นไปแล้วใน tick เดียวกัน → โยน NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าเป็น binding แบบ boolean ส่วนใหญ่คือ `*ngIf`, `[disabled]`, `[class.xxx]` หรือ flag พวก `isLoading` / `isOpen`

**สำคัญ:** รอบที่ 2 มีเฉพาะ dev mode ตอน build production จะไม่ error แต่ **bug ยังอยู่** คือ UI อาจแสดงค่าเก่าค้างไว้ 1 เฟรม อย่าใช้วิธีไปรัน production แล้วสรุปว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child เปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิก เจอบ่อยสุด)**

Angular เช็ก parent ก่อน แล้วค่อยรัน `ngOnInit` ของ child ถ้า child ไปแก้ค่ากลับขึ้นไป Angular ก็เช็ก parent ไปแล้ว

```ts
// child.component.ts
ngOnInit() {
  this.loadingChange.emit(true);   // Angular เช็ก parent ไปแล้ว → NG0100
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

- เปิด stack trace ใน console ให้สุด: frame ที่อยู่**ถัดลงไปจาก** `checkNoChanges` / `checkNoChangesInternal` คือ component ที่เป็นต้นเหตุ Angular เวอร์ชันใหม่จะบอกชื่อ template/component มาด้วย
- ใช้ Angular DevTools ดู component tree
- ถ้ายังไม่เจอ: comment template ออกทีละส่วนเพื่อ bisect หา binding ตัวที่เป็น boolean

## วิธีแก้ (เรียงจากดีที่สุดลงมา)

**1. ย้ายจุดที่เปลี่ยนค่าให้เร็วขึ้น (ดีที่สุด)**

ย้ายไป `ngOnInit` ของ parent หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงกลับขึ้นไป

**2. ทำให้ค่าเป็น derived แทนที่จะ mutate เอง**

```ts
// แทนที่จะ set flag ทีหลัง ให้คำนวณจาก source เดียว
get isDisabled() { return this.form.invalid || this.saving; }
```

**3. ถ้าจำเป็นต้องวัด DOM จริง ๆ → `ChangeDetectorRef.detectChanges()`**

```ts
constructor(private cdr: ChangeDetectorRef) {}

ngAfterViewInit() {
  this.isOverflowing = this.box.nativeElement.scrollHeight > 100;
  this.cdr.detectChanges();   // บังคับ re-check view นี้ วิธีนี้ถูกต้องสำหรับเคสวัด DOM
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
ได้ผลแน่นอน แต่เพิ่ม CD cycle และอาจเห็นภาพกระพริบ ควรใช้ต่อเมื่อแก้ที่โครงสร้างไม่ได้จริง ๆ

**6. ถ้าใช้ Angular 17+ ลองใช้ signals** `signal` + `computed` ตัดปัญหาแบบนี้ไปเกือบหมด เพราะค่า derive มาจาก source เดียวและ stable ภายใน tick

## สิ่งที่ไม่ควรทำ

- ใส่ `setTimeout` ไปทั่วโดยไม่หาสาเหตุ
- ปิด dev mode หรือ `enableProdMode()` เพื่อให้ error หาย เพราะ bug ยังอยู่ แค่ไม่เตือน

---

ถ้าแปะโค้ด component + template ที่เป็นต้นเหตุมาให้ดู (ดูจาก stack trace ว่าชี้ไปที่ไฟล์ไหน) ผมช่วยชี้จุดและแก้ให้ตรงเคสได้เลยครับ

---

**สรุปที่แก้**

- **em dash 14 จุด** ภาษาไทยไม่ใช้เครื่องหมายนี้ เปลี่ยนเป็น `:` ในรายการข้อ 1–2 และ bullet แรกของ "วิธีหาจุดที่ผิด" ที่เหลือใช้เว้นวรรคหรือวงเล็บ เช่น "ย้ายจุดที่เปลี่ยนค่าให้เร็วขึ้น (ดีที่สุด)"
- **passive "ถูก" 3 จุด** "view นั้นถูก check ไปแล้ว" → "Angular เช็ก view นั้นไปแล้ว", "parent ก็ถูกเช็คไปแล้ว" → "Angular ก็เช็ก parent ไปแล้ว" รวมถึง comment ในโค้ดบล็อกแรกด้วย (แก้เฉพาะข้อความไทย ตัวโค้ดคงเดิม)
- **สำนวนแปลตรงตัว** "เป็นยาแก้ปวด" (band-aid) → "เป็นการแก้ที่ปลายเหตุ", "โรย setTimeout ทุกที่" (sprinkle) → "ใส่ setTimeout ไปทั่ว", "ปัญหาคลาสนี้" (this class of problems) → "ปัญหาแบบนี้"
- **ตัวสะกด** เช็ค → เช็ก ตามราชบัณฑิตฯ
- **คำที่ฟังเป็นภาษาเขียนทางการเกินไป** "พิจารณา signals" → "ลองใช้ signals", "ทำให้ค่าเป็น derived แทนการ mutate" → "แทนที่จะ mutate เอง", "ถูกต้องตามหลักสำหรับเคสวัด DOM" → "วิธีนี้ถูกต้องสำหรับเคสวัด DOM"
- **เรียงประโยคใหม่** "ดังนั้นอย่าแก้ด้วยการไปรัน production แล้วบอกว่าหายแล้ว" → "อย่าใช้วิธีไปรัน production แล้วสรุปว่าหายแล้ว" และ "เพื่อให้ error หาย — bug ยังอยู่" → ต่อด้วย "เพราะ" แทนขีด
- **จุลภาคแบบอังกฤษ** "ของ parent, หรือคำนวณ" → ใช้เว้นวรรคแทน

เนื้อหาและโค้ดคงเดิมทั้งหมดครับ ยกเว้น comment ภาษาไทยบรรทัดเดียวในโค้ดบล็อกแรกกับบล็อก `detectChanges()` ที่ติด passive เลยเกลาข้อความไทยในนั้นด้วย ถ้าอยากให้คง comment เดิมเป๊ะ ๆ บอกได้ครับ
