แปลว่า Angular เช็ก binding ของ component ไปรอบหนึ่งแล้ว พอวนกลับมาตรวจทานซ้ำ ค่ากลับเปลี่ยนไปแล้วครับ

ใน dev mode Angular จะรัน change detection สองรอบต่อหนึ่ง cycle รอบแรกคือรอบจริงที่เอาค่าไปใส่ DOM รอบสองเป็นรอบตรวจทานว่าค่ายังเหมือนเดิมไหม ถ้าไม่เหมือน แปลว่ามีโค้ดไปแก้ค่าหลังจากเช็กไปแล้ว ซึ่งผิดกฎ one-way data flow ที่ Angular ยึดอยู่ คือข้อมูลต้องไหลจาก parent ลง child ทางเดียวต่อหนึ่งรอบ

อีกเรื่องที่ควรรู้คือ prod build จะไม่ขึ้น error นี้ เพราะไม่มีรอบตรวจทาน แต่ไม่ได้แปลว่าหาย ของจริงคือ UI มีจังหวะที่แสดงค่าไม่ตรงกับ state อยู่แวบหนึ่ง

## สาเหตุที่เจอบ่อย

ข้อความ `Previous value: 'false'. Current value: 'true'` บอกว่าเป็นค่า boolean เกือบทั้งหมดจะเป็นพวก flag อย่าง `isLoading`, `disabled`, `*ngIf` เรียงตามความถี่ที่เจอ

1. แก้ค่าใน `ngAfterViewInit` หรือ `ngAfterViewChecked` ตอนนั้น Angular เช็ก template ไปเรียบร้อยแล้ว
2. parent bind ค่าที่มาจาก child เช่น อ่านผ่าน `@ViewChild` แล้วเอาไปใช้ใน template ของตัวเอง เพราะ change detection ไหลจากบนลงล่าง กว่า child จะมีค่า parent ก็เช็กผ่านไปแล้ว
3. getter ใน template ที่คืน reference ใหม่ทุกครั้งที่เรียก เช่น สร้าง array ใหม่ หรือ `new Date()`
4. service กลางที่ component อื่น set ค่าตอน init เช่น loading service, breadcrumb, page title
5. `BehaviorSubject` ที่ emit ทันทีแบบ synchronous ตอน subscribe ใน lifecycle hook ที่สายเกินไป

## วิธีหาตัวต้นเหตุ

stack trace ของ error นี้มักไม่ค่อยช่วย ให้ไล่จาก template แทน หา binding ที่เป็น boolean ทั้งหมด (`*ngIf`, `[disabled]`, `[class.xxx]`) แล้วดูว่าตัวไหนมีโค้ดไปเซ็ตใน `ngAfterViewInit` หรือใน subscribe วิธีเร็วสุดคือ comment ทีละตัวดูว่าตัวไหนทำให้ error หาย

## วิธีแก้

**ย้าย logic ไป `ngOnInit`** เคสส่วนใหญ่จบตรงนี้ ถ้าโค้ดที่เซ็ต flag ไม่ได้ต้องการ DOM จริง ๆ ก็ไม่มีเหตุผลต้องรอถึง `ngAfterViewInit`

**ถ้าจำเป็นต้องรอ view จริง ๆ** เช่น ต้องวัดขนาด element หรืออ่านค่าจาก `@ViewChild` ให้สั่งเช็กใหม่อีกรอบ เป็นการบอก Angular ตรง ๆ ว่ารู้ตัวว่าเปลี่ยนค่า

```ts
constructor(private cdr: ChangeDetectorRef) {}

ngAfterViewInit() {
  this.hasOverflow = this.content.nativeElement.scrollHeight > 300;
  this.cdr.detectChanges();
}
```

ถ้า component ใช้ `OnPush` ให้ใช้ `markForCheck()` แทน

**เลี่ยง getter ที่สร้าง reference ใหม่** ย้ายไปคำนวณตอนที่ค่าเปลี่ยนจริง หรือทำเป็น pure pipe

**`setTimeout` หรือ `Promise.resolve().then()`** ใช้ได้ แต่เป็นการแก้ที่ปลายเหตุ คือแค่เลื่อนการเซ็ตค่าไป tick ถัดไปให้พ้นรอบตรวจทาน เก็บไว้ใช้ตอนที่แก้โครงสร้างไม่ได้จริง ๆ อย่าใส่ไปทั่วทั้งโปรเจกต์

อีกทางถ้าอยู่ Angular 16 ขึ้นไป ลองย้าย flag พวกนี้ไปเป็น `signal` กับ `computed` ดู ค่าที่อ่านได้จะตรงกันทั้ง cycle ตัดปัญหาแบบนี้ไปได้เกือบหมด

ถ้าส่งโค้ด component กับ template ที่เจอมาให้ดู เดี๋ยวชี้บรรทัดที่เป็นต้นเหตุให้ครับ
