มีสองเรื่องที่ควรแก้ครับ เรื่องใหญ่คือเรียก method ใน template ส่วนอีกเรื่องคือ `*ngFor` ไม่มี `trackBy`

## ทำไมเรียก method ใน template ถึงแพง

Angular ไม่ cache ค่าที่ได้จาก method ในทุก change detection cycle ทุกบรรทัดจะเรียก `formatName` กับ `calculateLeaveBalance` ใหม่หมด พนักงาน 3,000 คนก็เท่ากับ 6,000 ครั้งต่อรอบ

ที่หนักคือ change detection ไม่ได้รันแค่ตอนข้อมูลเปลี่ยน แต่รันทุกครั้งที่มี event เช่น คลิก พิมพ์ scroll `setTimeout` หรือ HTTP response กลับมา พิมพ์ในช่องค้นหาทีเดียวก็ได้หลายหมื่นครั้งแล้ว ถ้า `calculateLeaveBalance` วนลูปประวัติการลาด้วยยิ่งช้าเข้าไปอีก

## ทางแก้หลัก: คำนวณไว้ล่วงหน้าใน component

แปลงข้อมูลเป็น view model ที่คำนวณเสร็จแล้วตั้งแต่ตอนโหลด template เหลือแค่อ่านค่า

```ts
interface EmployeeRow {
  id: number;
  displayName: string;
  leaveBalance: number;
}

readonly rows = computed<EmployeeRow[]>(() =>
  this.employees().map(emp => ({
    id: emp.id,
    displayName: this.formatName(emp),
    leaveBalance: this.calculateLeaveBalance(emp),
  }))
);

trackById = (_: number, row: EmployeeRow) => row.id;
```

```html
<div *ngFor="let row of rows(); trackBy: trackById">
  {{ row.displayName }} - {{ row.leaveBalance }} วัน
</div>
```

ถ้าใช้ Angular 17 ขึ้นไป เขียนเป็น `@for` ได้เลย มี track บังคับอยู่แล้ว

```html
@for (row of rows(); track row.id) {
  <div>{{ row.displayName }} - {{ row.leaveBalance }} วัน</div>
}
```

## ถ้าอยากแก้น้อยที่สุด ใช้ pure pipe

pure pipe จะ cache ผลลัพธ์ตาม reference ของ input ตราบใดที่ object `emp` ยังเป็นตัวเดิม Angular จะไม่เรียก `transform` ซ้ำ

```ts
@Pipe({ name: 'empName', standalone: true })
export class EmpNamePipe implements PipeTransform {
  transform(emp: Employee): string {
    return formatName(emp);
  }
}
```

วิธีนี้แก้ปัญหาการคำนวณซ้ำได้ แต่ยังเป็นการแก้ที่ปลายเหตุเมื่อเทียบกับการคำนวณไว้ล่วงหน้า เพราะ logic ยังกระจายอยู่ใน template

## อีกสองอย่างที่ควรทำที่ 3,000 แถว

**OnPush** ใส่ `changeDetection: ChangeDetectionStrategy.OnPush` ใน component ตัดรอบ change detection ที่ไม่จำเป็นออกไปเยอะ

**Virtual scroll** 3,000 `<div>` ใน DOM พร้อมกันทำให้ browser หน่วงตั้งแต่ตอน render ครั้งแรก ใช้ CDK virtual scroll จะ render เฉพาะแถวที่อยู่ในจอ

```html
<cdk-virtual-scroll-viewport itemSize="40" style="height: 600px">
  <div *cdkVirtualFor="let row of rows(); trackBy: trackById">
    {{ row.displayName }} - {{ row.leaveBalance }} วัน
  </div>
</cdk-virtual-scroll-viewport>
```

ลำดับความคุ้ม: ย้ายการคำนวณออกจาก template ก่อน แล้วค่อย virtual scroll ส่วน `trackBy` กับ OnPush ใส่ไปเลยเพราะแทบไม่มีต้นทุน

อยากรู้ว่า `calculateLeaveBalance` ข้างในทำอะไรบ้างครับ ถ้าวนลูปประวัติการลาหรือเรียก service เพิ่ม อาจจะย้ายไปคำนวณที่ backend แล้วส่งมาพร้อมข้อมูลพนักงานเลยคุ้มกว่าครับ
