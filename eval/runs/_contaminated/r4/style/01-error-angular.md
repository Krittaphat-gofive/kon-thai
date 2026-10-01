เป็น error ที่ Angular เตือนว่าค่าใน binding เปลี่ยนหลังจากรอบ change detection เช็กไปแล้วครับ ไม่ใช่ error ที่ทำให้แอปพัง แต่แปลว่ามี logic เปลี่ยน state ผิดจังหวะ

## ทำไมถึงเกิด

ตอนรันใน dev mode Angular จะรัน change detection สองรอบต่อหนึ่ง cycle รอบแรกคืออัปเดต view จริง รอบสองคือรันซ้ำเพื่อเช็กว่าค่าทุกตัวยังเท่าเดิมไหม ถ้าไม่เท่า แปลว่ามีโค้ดไปแก้ค่าหลังรอบแรกจบแล้ว Angular ก็เลยโยน NG0100 ออกมา

ที่ Angular ต้องเช็กเพราะ one-way data flow ข้อมูลควรไหลจาก parent ลง child ทางเดียวต่อหนึ่งรอบ ถ้าค่าเด้งกลับขึ้นไปแก้ parent ระหว่างรอบเดียวกัน view กับ state จะไม่ตรงกัน

ที่สำคัญคือ `ng build --configuration production` จะไม่รันรอบเช็กนี้ error เลยหายไปเฉย ๆ แต่ปัญหายังอยู่ UI อาจแสดงค่าเก่าค้างไปหนึ่ง frame

## เคสที่เจอบ่อย

ค่าในข้อความเป็น `'false'` → `'true'` แสดงว่าเป็น binding ที่เป็น boolean เช่น `*ngIf`, `[disabled]`, `[class.active]` หรือพวก flag `isLoading` ลองไล่ดูตามนี้

1. แก้ค่าใน `ngAfterViewInit` หรือ `ngAfterViewChecked` สองตัวนี้ทำงานหลัง Angular เช็ก template เสร็จแล้ว แก้ตรงนี้คือแก้สาย
2. child `@Output()` emit ค่ากลับไปหา parent ตอน `ngOnInit` หรือ `ngAfterViewInit`
3. getter ใน template ที่คืนค่าใหม่ทุกครั้ง เช่น `get items() { return this.list.filter(...) }` หรือพวกที่ใช้ `Date.now()`
4. subscribe ค่าจาก service แล้วเซ็ตเข้า field ตรง ๆ ระหว่างรอบ change detection
5. directive ที่ไปแก้ `@Input` ของตัวเอง

## วิธีแก้ เรียงจากดีที่สุด

**ย้าย logic ขึ้นไป `ngOnInit`** ถ้าค่านั้นไม่ได้ต้องรอ DOM หรือ `@ViewChild` ย้ายไป `ngOnInit` จบเลย เพราะ hook นี้ทำงานก่อน Angular เช็ก template

**ถ้าต้องอยู่ใน `ngAfterViewInit` จริง ๆ ให้สั่ง detect เอง**

```ts
constructor(private cdr: ChangeDetectorRef) {}

ngAfterViewInit() {
  this.showSpinner = true;
  this.cdr.detectChanges();   // sync view ให้ตรงก่อน Angular รันรอบเช็ก
}
```

ใช้ `detectChanges()` ไม่ใช่ `markForCheck()` เพราะ `markForCheck()` แค่ mark ว่า view นี้ dirty ไว้รอบหน้า ค่ายังไม่ตรงกันในรอบปัจจุบันอยู่ดี

**ทำให้ getter คืนค่าเดิม** ถ้าต้นเหตุคือ getter ใน template ให้คำนวณไว้ล่วงหน้าแล้วเก็บเป็น field หรือใช้ `computed()` ถ้าโปรเจกต์ใช้ signal อยู่แล้ว

**ออกแบบให้ state อยู่ที่ parent** เคส child emit กลับหา parent ทางที่สะอาดกว่าคือให้ parent ถือ state ตัวนั้นตั้งแต่แรก แล้วส่งลงมาเป็น `@Input` แทนที่จะให้ child เป็นคนบอก

**`setTimeout` กับ `Promise.resolve().then()`** สองตัวนี้ใช้ได้ เพราะเลื่อนการเซ็ตค่าไปรอบถัดไป แต่เป็นการแก้ที่ปลายเหตุ ไม่ควรใส่ไปทั่วโปรเจกต์ ถ้าจะใช้ ใส่ comment กำกับไว้ด้วยว่าทำไมต้องเลื่อน

## วิธีหาว่าบรรทัดไหนเป็นต้นเหตุ

Angular เวอร์ชันใหม่จะใส่ชื่อ component กับ template ที่เกิดปัญหามาใน console ให้ด้วย ถ้าข้อความไม่ชัดพอ ให้ไล่แบบนี้

- เปิด console แล้วกาง stack trace ดูตัวบนสุดที่เป็นไฟล์ในโปรเจกต์เรา ไม่ใช่ไฟล์ของ Angular
- ค้นหา `ngAfterView` ทั้งโปรเจกต์ก่อน เจอบ่อยสุด
- ไล่ดู binding ที่เป็น boolean ในหน้าจอที่กำลังเปิดอยู่ แล้วเช็กว่ามีใครเซ็ตค่านั้นนอก `ngOnInit` บ้าง

ถ้าส่ง stack trace กับโค้ด component ที่เกิดปัญหามาให้ดู เดี๋ยวผมชี้จุดที่ต้องแก้ให้ตรง ๆ ได้ครับ
