มีสามเรื่องที่ควรแก้ครับ เรื่องใหญ่สุดคือเรียกฟังก์ชันใน template

**1. `formatName()` กับ `calculateLeaveBalance()` ทำงานใหม่ทุกรอบ change detection**

Angular ไม่มีทางรู้ว่าสองฟังก์ชันนี้คืนค่าเดิมหรือเปล่า เลยต้องเรียกใหม่ทุกรอบที่เช็ก 3,000 แถว คูณสองฟังก์ชัน ก็ 6,000 ครั้งต่อรอบ และรอบ change detection เกิดบ่อยกว่าที่คิดมาก ทุก click ทุกการพิมพ์ ทุก setTimeout ทุก response ที่กลับมาจาก API ยิงใหม่หมด ถ้าใน `calculateLeaveBalance` มีการวน loop ประวัติการลาอีกชั้น ยิ่งหนักเข้าไปอีก

ทางแก้ที่ตรงที่สุดคือคำนวณครั้งเดียวตอนได้ข้อมูลมา แล้วเก็บเป็น field ไว้เลย

```ts
this.rows = employees.map(emp => ({
  id: emp.id,
  name: this.formatName(emp),
  leaveBalance: this.calculateLeaveBalance(emp),
}));
```

template ก็เหลือแค่อ่านค่า ไม่มีการคำนวณอีก

ถ้าไม่อยากแก้โครงสร้างข้อมูล ใช้ pure pipe แทนได้ Angular จะ cache ผลไว้ให้ ตราบใดที่ input ยังเป็น object อ้างอิงเดิม

**2. ไม่มี trackBy**

พอ array เปลี่ยน reference เช่นโหลดใหม่หรือ filter Angular จะทิ้ง DOM เดิมทั้ง 3,000 แถวแล้วสร้างใหม่หมด ใส่ track ด้วย id ช่วยได้เยอะ

Angular 17 ขึ้นไปใช้ `@for` ซึ่งบังคับใส่ track อยู่แล้ว

```html
@for (row of rows; track row.id) {
  <div>{{ row.name }} - {{ row.leaveBalance }} วัน</div>
}
```

เวอร์ชันเก่ากว่านั้นเขียน `*ngFor="let row of rows; trackBy: trackById"`

**3. 3,000 แถวอยู่ใน DOM พร้อมกัน**

ต่อให้แก้สองข้อบนแล้ว browser ก็ยังต้องวาด node 3,000 ตัวอยู่ดี ถ้ายังรู้สึกหนืดตอน scroll ให้ใช้ `cdk-virtual-scroll-viewport` จาก Angular CDK วาดเฉพาะแถวที่อยู่ในจอ เหลือจริง ๆ ไม่กี่สิบแถว

เสริมอีกนิด ถ้า component นี้รับข้อมูลมาทาง `@Input` แล้วไม่ได้แก้ state เอง ใส่ `changeDetection: ChangeDetectionStrategy.OnPush` ไปด้วย ตัดรอบเช็กที่ไม่จำเป็นออกได้อีกเยอะ

ถ้ามีเวลาแก้ได้แค่ข้อเดียว เอาข้อ 1 ก่อน ได้ผลชัดสุด ส่งโค้ดของ `calculateLeaveBalance` มาดูได้นะครับ เผื่อมีจุดอื่นที่รีดได้อีก
