มีครับ ปัญหาหลักคือ**เรียก method ใน template** ซึ่งพอมี 3,000 แถวจะเจ็บมาก

## ปัญหา

**1. method ใน template รันใหม่ทุกรอบ change detection**

Angular ไม่รู้ว่า `formatName()` กับ `calculateLeaveBalance()` คืนค่าเดิมไหม เลยต้องเรียกซ้ำทุกครั้งที่ CD ทำงาน = 3,000 × 2 = **6,000 ครั้งต่อรอบ** และ CD มันไม่ได้ทำงานแค่ตอนข้อมูลเปลี่ยน — คลิกเมาส์ พิมพ์คีย์บอร์ด `setTimeout` HTTP response ที่ไหนก็ได้ในแอป ก็ trigger หมด เลื่อนเมาส์ทีเดียวอาจเรียกไปหลายหมื่นครั้ง

ยิ่ง `calculateLeaveBalance()` ถ้าข้างในวน loop ประวัติการลา จะยิ่งหนัก

**2. ไม่มี trackBy** — พอ reload ข้อมูลแล้ว assign array ใหม่ Angular จะทิ้ง DOM เดิมทั้ง 3,000 แถวแล้วสร้างใหม่หมด ทั้งที่ข้อมูลอาจเหมือนเดิม

**3. เรนเดอร์ 3,000 แถวพร้อมกัน** — DOM node เยอะเกินจำเป็น ทั้งที่ผู้ใช้เห็นแค่ ~20 แถว

## แก้

คำนวณไว้ล่วงหน้าตอนได้ข้อมูลมา แล้ว template แค่อ่านค่า

```ts
// signal-based (Angular 16+)
readonly rows = computed(() =>
  this.employees().map(emp => ({
    id: emp.id,
    name: formatName(emp),
    leave: calculateLeaveBalance(emp),
  }))
);

trackById = (_: number, row: { id: string }) => row.id;
```

ถ้าเป็น RxJS ก็ `map()` ใน pipe แล้วใช้ `| async` แทน

```html
<cdk-virtual-scroll-viewport itemSize="40" class="viewport">
  @for (row of rows(); track row.id) {
    <div>{{ row.name }} - {{ row.leave }} วัน</div>
  }
</cdk-virtual-scroll-viewport>
```

แล้วใส่ `changeDetection: ChangeDetectionStrategy.OnPush` ที่ component ด้วย

## หมายเหตุ

- `@for` ใช้ได้ตั้งแต่ Angular 17 ถ้าเวอร์ชันเก่ากว่านั้นใช้ `*ngFor="let row of rows; trackBy: trackById"` ผลเหมือนกัน
- virtual scroll ต้องรู้ความสูงแถวแน่นอน (`itemSize`) ถ้าแถวสูงไม่เท่ากันต้องใช้ autosize ซึ่งยังเป็น experimental — กรณีนั้นใช้ pagination แทนจะคุมง่ายกว่า
- ถ้าแก้ไม่ได้ทั้งหมดตอนนี้ เอาแค่ย้าย method ออกจาก template อย่างเดียวก็ได้ผลเยอะสุดแล้ว ส่วน virtual scroll ค่อยตามมาทีหลัง

ถ้าอยากให้ช่วยดู `calculateLeaveBalance()` ว่าข้างในหนักแค่ไหน ส่งโค้ดมาได้ครับ
