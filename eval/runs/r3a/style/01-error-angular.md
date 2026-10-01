แปลว่ามีค่าที่ผูกไว้กับ template เปลี่ยนไปหลังจาก Angular เช็ก component นั้นไปแล้วในรอบเดียวกันครับ

## ทำไมถึงขึ้น

ตอน dev mode Angular จะรัน change detection สองรอบต่อหนึ่ง cycle รอบแรกเช็กแล้ว update view รอบสองเช็กซ้ำว่าค่ายังเท่าเดิมไหม ถ้าไม่เท่า แปลว่ามีโค้ดไปแก้ค่าหลังรอบแรกจบ Angular เลยเตือนว่า view กับ state ไม่ตรงกัน

เคสนี้ previous `false` current `true` ส่วนใหญ่จะเป็น boolean พวก `*ngIf`, `[disabled]`, `isLoading`, `showPanel`

สาเหตุที่เจอบ่อยสุด
1. component ลูกไปแก้ค่าของ parent ใน `ngAfterViewInit` หรือ `ngAfterContentInit` ตอนนั้น Angular เช็ก parent ไปแล้ว
2. getter หรือ method ใน template ที่คืนค่าใหม่ทุกครั้งที่เรียก
3. `@Output().emit()` จากลูกตอน init แล้ว parent เอาไป set flag ต่อ
4. subscribe Observable ที่ยิงค่าออกมาทันทีแบบ synchronous เช่น `BehaviorSubject`, `of()`, `startWith()`

## วิธีแก้

**1. ย้าย logic ให้ทำเร็วขึ้น** ทางที่ดีที่สุดถ้าทำได้

```ts
// ตัวที่พัง
ngAfterViewInit() {
  this.isReady = true;   // NG0100
}

// ย้ายมา ngOnInit ถ้า logic ไม่ได้ต้องรอ view จริง ๆ
ngOnInit() {
  this.isReady = true;
}
```

**2. สั่ง detectChanges เอง** กรณีที่ต้องรอ view จริง ๆ เช่น ต้องวัดขนาด element ก่อน

```ts
private cdr = inject(ChangeDetectorRef);

ngAfterViewInit() {
  this.isReady = this.el.nativeElement.scrollHeight > 400;
  this.cdr.detectChanges();
}
```

**3. เปลี่ยนมาใช้ signal** ถ้าอยู่ Angular 16+ ย้าย flag พวกนี้เป็น `signal()` หรือ `computed()` ตัด error แบบนี้ไปได้เกือบหมด เพราะ Angular จัดการ sync ให้เอง

**4. setTimeout หรือ Promise.resolve().then()** ใช้ได้ แต่เป็นการแก้ที่ปลายเหตุ แค่เลื่อนไปทำ cycle หน้าเฉย ๆ ถ้าใส่ไปทั่วโปรเจกต์จะกลายเป็นหนี้ทางเทคนิค เก็บไว้ใช้ตอนจนปัญญาจริง ๆ

## วิธีหาว่าพังตรงไหน

ดู stack trace ใน console บรรทัดบน ๆ จะบอกชื่อ component กับ template ที่พัง ถ้ายังไม่ชัดให้ comment binding ที่เป็น boolean ออกทีละตัวจนกว่า error จะหาย

อีกเรื่องที่ต้องรู้ไว้ ตอน build prod Angular ไม่รันรอบสอง error ตัวนี้เลยหายไปเอง แต่ปัญหายังอยู่ view อาจค้างค่าเก่าอยู่หนึ่ง cycle ก่อนจะ update เลยอย่าปล่อยผ่าน

ถ้าแปะโค้ด component ที่ error ชี้มาให้ดู เดี๋ยวช่วยหาจุดให้ครับ
