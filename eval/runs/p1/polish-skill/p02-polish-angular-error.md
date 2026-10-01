ผ่าน linter แล้วครับ จาก 18 จุดเหลือ 0

---

## NG0100 คืออะไร

ตอนรัน `ng serve` (dev mode) Angular จะรัน change detection **สองรอบ** ต่อหนึ่ง tick:

1. รอบจริง: คำนวณค่า binding แล้วอัปเดต DOM
2. รอบตรวจสอบ (`checkNoChanges`): คำนวณใหม่อีกครั้งแล้วเทียบว่าค่าเท่าเดิมไหม

ถ้าค่าต่างกัน แปลว่ามีโค้ดไปเปลี่ยน state **หลังจาก** Angular check view นั้นไปแล้วใน tick เดียวกัน → โยน NG0100 ออกมา

`Previous value: 'false'. Current value: 'true'` บอกว่าเป็น binding แบบ boolean ส่วนใหญ่คือ `*ngIf`, `[disabled]`, `[class.xxx]` หรือ flag พวก `isLoading` / `isOpen`

**สำคัญ:** รอบที่ 2 มีเฉพาะ dev mode ตอน build production จะไม่ error แต่ **bug ยังอยู่** คือ UI อาจแสดงค่าเก่าค้างไว้ 1 เฟรม ดังนั้นอย่ารัน production แล้วสรุปว่าหายแล้ว

## สาเหตุที่เจอบ่อย

**1. Child เปลี่ยนค่าที่ parent bind อยู่ (เคสคลาสสิกที่สุด)**

Angular เช็ก parent ก่อน แล้วค่อยรัน `ngOnInit` ของ child พอ child แก้ค่ากลับขึ้นไป Angular ก็เช็ก parent ไปแล้ว

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

- เปิด stack trace ใน console ให้สุด แล้วดู frame ที่อยู่**ถัดลงไปจาก** `checkNoChanges` / `checkNoChangesInternal` นั่นคือ component ต้นเหตุ Angular เวอร์ชันใหม่จะบอกชื่อ template/component มาด้วย
- ใช้ Angular DevTools ดู component tree
- ถ้ายังไม่เจอ: comment template ออกทีละส่วนเพื่อ bisect หา binding ตัวที่เป็น boolean

## วิธีแก้ (เรียงจากดีที่สุดลงมา)

**1. ย้ายจุดที่เปลี่ยนค่าให้เร็วขึ้น (ดีที่สุด)**

ย้ายไป `ngOnInit` ของ parent หรือคำนวณที่ parent แล้วส่งลงมาเป็น `@Input()` แทนที่จะให้ child ยิงกลับขึ้นไป

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
ใช้ได้ผลแน่นอน แต่เพิ่ม CD cycle และอาจเห็นภาพกระพริบ ควรใช้ต่อเมื่อแก้ที่โครงสร้างไม่ได้จริง ๆ

**6. ถ้าใช้ Angular 17+ ลองดู signals** `signal` + `computed` ตัดปัญหาแบบนี้ไปเกือบหมด เพราะค่า derive มาจาก source เดียวและ stable ภายใน tick

## สิ่งที่ไม่ควรทำ

- ใส่ `setTimeout` ไปทั่วโดยไม่หาสาเหตุ
- ปิด dev mode / `enableProdMode()` เพื่อให้ error หาย bug ไม่ได้หายไปด้วย แค่ไม่มีใครเตือน

---

ถ้าแปะโค้ด component + template ที่เป็นต้นเหตุมาให้ดู (ดูจาก stack trace ว่าชี้ไปที่ไฟล์ไหน) ผมช่วยชี้จุดและแก้ให้ตรงเคสได้เลยครับ

---

## แก้อะไรไปบ้าง

**em dash 12 จุด** — เป็นเครื่องหมายของภาษาอังกฤษ ภาษาไทยไม่ใช้ เปลี่ยนเป็น `:` ในหัวข้อย่อย เป็นวงเล็บในหัวข้อ bold และเป็นเว้นวรรคในประโยคปกติ

**passive "ถูก" 2 จุด** — ภาษาไทยใช้ "ถูก" กับเรื่องไม่ดี เรื่องกลาง ๆ ให้บอกว่าใครทำ
- "view นั้นถูก check ไปแล้ว" → "Angular check view นั้นไปแล้ว"
- "parent ก็ถูกเช็คไปแล้ว" → "Angular ก็เช็ก parent ไปแล้ว"

**ตัวสะกด** — เช็ค → เช็ก (ราชบัณฑิตฯ) 2 จุด

**สำนวนแปลตรงตัว 3 จุด**
- "เป็นยาแก้ปวด" (band-aid) → "เป็นการแก้ที่ปลายเหตุ"
- "ปัญหาคลาสนี้" (this class of problems) → "ปัญหาแบบนี้"
- "โรย setTimeout ทุกที่" (sprinkle) → "ใส่ setTimeout ไปทั่ว"

**โครงประโยคที่ไม่ได้มาจาก linter**
- "อย่าแก้ด้วยการไปรัน production" → "อย่ารัน production แล้วสรุปว่าหายแล้ว" (ตัด "ด้วยการ" ที่ทำให้กริยากลายเป็นคำนาม)
- "แทนการ mutate" → "แทนที่จะ mutate"
- "พิจารณา signals" → "ลองดู signals" (ทางการเกินระดับของบทความ)
- bullet แรกในหัวข้อ "วิธีหาจุดที่ผิด" เรียงใหม่ทั้งประโยค ให้อ่านต่อเนื่องแทนที่จะหักด้วย em dash
- ตัดจุลภาคหน้า "หรือ" ที่คั่นวลีภาษาไทย (`[class.xxx]`, หรือ flag → `[class.xxx]` หรือ flag) และ (`ngOnInit` ของ parent, หรือ → `ngOnInit` ของ parent หรือ)

**ที่คงไว้ตามเดิม:** โค้ดทุก block ไม่แตะเลยตามที่สั่ง รวมถึงคอมเมนต์ไทยในนั้นด้วย — ซึ่งยังมี `// parent ถูก check ไปแล้ว` (passive) กับ em dash ใน `// บังคับ re-check view นี้ — ถูกต้องตามหลัก...` ถ้าอยากให้เกลาคอมเมนต์ในโค้ดด้วยบอกได้ครับ
