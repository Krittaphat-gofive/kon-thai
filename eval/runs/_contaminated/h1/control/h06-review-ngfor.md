มีครับ ปัญหาหลักอยู่ที่เรียก method ใน binding ตรง ๆ แล้วเจอกับ list 3,000 แถว ตรงนี้จะหน่วงชัดเจนเวลาใช้งานจริง

## 1. method ใน template รันใหม่ทุกรอบ change detection

Angular ไม่มีทางรู้ว่าผลของ `formatName` กับ `calculateLeaveBalance` เปลี่ยนตอนไหน เลยต้องเรียกใหม่ทุกครั้งที่ตรวจ view

3,000 แถว × 2 ฟังก์ชัน = 6,000 ครั้งต่อ 1 รอบ แล้ว default change detection ทำงานแทบทุก event: คลิก พิมพ์ scroll, setTimeout, HTTP ตอบกลับ ขยับเมาส์ผ่าน element ที่มี listener ทีเดียวก็ยิงได้หลายรอบติด ๆ กัน

ทางแก้ที่ตรงที่สุดคือคำนวณไว้ก่อนใน component แล้วให้ template อ่านค่าเฉย ๆ

```ts
// Angular 16+ ใช้ signal
readonly rows = computed(() =>
  this.employees().map(emp => ({
    id: emp.id,
    name: this.formatName(emp),
    leaveBalance: this.calculateLeaveBalance(emp),
  }))
);
```

ถ้ายังไม่ได้ใช้ signal ก็ map ตอนรับข้อมูลมาจาก API ได้เหมือนกัน

```ts
this.service.getEmployees().subscribe(list => {
  this.rows = list.map(emp => ({ ... }));
});
```

## 2. *ngFor ไม่มี trackBy

ทุกครั้งที่ assign `employees` ใหม่ เช่น โหลดใหม่หลัง filter หรือ refresh Angular จะทิ้ง DOM 3,000 node แล้วสร้างใหม่ทั้งชุด ทั้งที่ข้อมูลอาจเปลี่ยนแค่แถวเดียว

Angular 17 ขึ้นไป ใช้ `@for` ไปเลย เพราะบังคับใส่ `track` อยู่แล้ว

```html
@for (row of rows(); track row.id) {
  <div>{{ row.name }} - {{ row.leaveBalance }} วัน</div>
}
```

เวอร์ชันเก่ากว่านั้น

```html
<div *ngFor="let row of rows; trackBy: trackById">
  {{ row.name }} - {{ row.leaveBalance }} วัน
</div>
```

```ts
trackById = (_: number, row: EmployeeRow) => row.id;
```

## 3. render 3,000 node พร้อมกันก็หนักอยู่ดี

ต่อให้ไม่คำนวณซ้ำแล้ว browser ก็ยังต้องสร้างและ layout DOM 3,000 ชุด ถ้าหน้านี้เป็นตารางรายชื่อยาว ๆ แนะนำ virtual scroll จะช่วยได้มากที่สุด เพราะ render เฉพาะแถวที่เห็นบนจอ

```html
<cdk-virtual-scroll-viewport itemSize="40" style="height: 600px">
  <div *cdkVirtualFor="let row of rows; trackBy: trackById">
    {{ row.name }} - {{ row.leaveBalance }} วัน
  </div>
</cdk-virtual-scroll-viewport>
```

ถ้า UX รับได้ pagination หรือ server-side paging ก็ตัดปัญหาได้เหมือนกัน และเบากว่าในแง่ data transfer ด้วย

## ถ้าแยกการคำนวณออกมา precompute ไม่ได้จริง ๆ

ให้ย้ายไปเป็น pure pipe แทน method

```ts
@Pipe({ name: 'leaveBalance', standalone: true })
export class LeaveBalancePipe implements PipeTransform {
  transform(emp: Employee): number { /* ... */ }
}
```

```html
{{ emp | leaveBalance }} วัน
```

pure pipe จะ cache ผลไว้ และคำนวณใหม่เฉพาะตอน reference ของ `emp` เปลี่ยน แล้วแต่ละแถวใน loop ได้ instance ของตัวเอง เลยได้ cache แยกรายแถว ดีกว่าเรียก method เยอะ แต่ก็ยังสู้การ precompute ไม่ได้

## เสริมอีกข้อ

ใส่ `changeDetection: ChangeDetectionStrategy.OnPush` ที่ component นี้ด้วย แล้วอัปเดต array แบบสร้างใหม่ทุกครั้งแทนการ push เข้าไปในตัวเดิม จะตัดรอบตรวจที่ไม่จำเป็นออกไปได้อีกเยอะ

ถ้าบอกได้ว่าใช้ Angular เวอร์ชันไหน กับ `calculateLeaveBalance` ไปดึงข้อมูลอย่างอื่นเพิ่มหรือเปล่า เดี๋ยวผมเขียนตัวเต็มให้ดูเป็นตัวอย่างครับ
