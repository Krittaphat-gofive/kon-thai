มีสามจุดที่ควรแก้ครับ เรียงตามผลกระทบ

## 1. เรียกฟังก์ชันใน template

จุดนี้หนักสุด `formatName()` กับ `calculateLeaveBalance()` รันใหม่ทุกรอบ change detection ไม่ใช่แค่ตอนข้อมูลเปลี่ยน แค่คลิกที่ไหนก็ได้ในหน้า พิมพ์ใน input หรือ HTTP response กลับมา Angular ก็รันรอบใหม่ 3,000 แถว × 2 ฟังก์ชัน = 6,000 ครั้งต่อรอบ และรอบพวกนี้เกิดถี่มาก

ถ้า `calculateLeaveBalance` วน loop ดูประวัติการลาข้างในด้วย ยิ่งคูณเข้าไปอีก

แก้โดยคำนวณครั้งเดียวตอนรับข้อมูลมา แล้วให้ template อ่านค่าที่คำนวณไว้แล้ว

```ts
interface EmployeeRow {
  id: string;
  displayName: string;
  leaveBalance: number;
}

this.rows = employees.map(emp => ({
  id: emp.id,
  displayName: this.formatName(emp),
  leaveBalance: this.calculateLeaveBalance(emp),
}));
```

```html
<div *ngFor="let row of rows; trackBy: trackById">
  {{ row.displayName }} - {{ row.leaveBalance }} วัน
</div>
```

อีกทางคือทำเป็น pure pipe ซึ่ง Angular จะ cache ผลไว้ให้ตราบที่ input ไม่เปลี่ยน แต่ map เป็น view model ตั้งแต่ต้นอ่านง่ายกว่าและ test ง่ายกว่า

## 2. ไม่มี trackBy

พอโหลด employees ชุดใหม่มาหรือ filter แล้ว assign array ใหม่ Angular เทียบแต่ละ item ด้วย object identity ถ้าได้ object ใหม่หมด (เช่นมาจาก API รอบใหม่) จะลบ DOM ทั้ง 3,000 แถวแล้วสร้างใหม่ทั้งหมด ทั้งที่ข้อมูลอาจเหมือนเดิมเกือบหมด

```ts
trackById(index: number, row: EmployeeRow) {
  return row.id;
}
```

ถ้าเป็น Angular 17 ขึ้นไป ย้ายมาใช้ `@for` ได้เลย เพราะบังคับใส่ `track` อยู่แล้ว

```html
@for (row of rows; track row.id) {
  <div>{{ row.displayName }} - {{ row.leaveBalance }} วัน</div>
}
```

## 3. render 3,000 แถวพร้อมกัน

ต่อให้แก้สองข้อบนแล้ว DOM node 3,000 ชุดก็ยังกินแรมและทำให้หน้าแรกโหลดช้า ใช้ CDK virtual scroll ให้ render เฉพาะแถวที่อยู่ในจอ

```html
<cdk-virtual-scroll-viewport itemSize="40" class="h-96">
  <div *cdkVirtualFor="let row of rows; trackBy: trackById">
    {{ row.displayName }} - {{ row.leaveBalance }} วัน
  </div>
</cdk-virtual-scroll-viewport>
```

ข้อแม้คือต้องกำหนดความสูง viewport และ `itemSize` ให้ตรงกับความสูงจริงของแถว ถ้าแถวสูงไม่เท่ากันต้องใช้ `autosize` ซึ่งยังอยู่ใน experimental

## เสริม

ถ้า component นี้รับข้อมูลมาทาง `@Input` ล้วน ๆ ใส่ `changeDetection: ChangeDetectionStrategy.OnPush` ไปด้วย จะตัดรอบ change detection ที่ไม่เกี่ยวออกไปได้อีกเยอะ

แต่ก่อนทำสามข้อนี้ ถ้า `calculateLeaveBalance` ต้องยิง query เพิ่มต่อคน ควรย้ายไปคำนวณที่ backend แล้วส่งมาพร้อม list เลย ถ้าส่งโค้ดฟังก์ชันนั้นมาดู เดี๋ยวช่วยดูให้ว่าควรแก้ทางไหนครับ
