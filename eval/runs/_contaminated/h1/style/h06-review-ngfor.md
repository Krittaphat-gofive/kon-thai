มีครับ ตัวนี้เป็นเคสคลาสสิกของ Angular เลย ปัญหาหลักคือเรียก method ใน template

## ทำไมถึงเป็นปัญหา

ทุกครั้งที่ Angular รัน change detection จะเรียก `formatName()` กับ `calculateLeaveBalance()` ใหม่ทุกแถว ไม่สนว่าข้อมูลเปลี่ยนหรือเปล่า เพราะ Angular ไม่มีทางรู้ว่า method คืนค่าเดิมไหม

3,000 แถว × 2 method = 6,000 ครั้งต่อ 1 รอบ CD

แล้ว CD รันบ่อยกว่าที่คิดเยอะ พิมพ์ 1 ตัวอักษรในช่องค้นหา คลิกปุ่ม เลื่อน scroll ที่มี event binding หรือ HTTP response กลับมา 1 ก้อน ก็รันหมด พิมพ์ชื่อพนักงาน 10 ตัวอักษรคือ 60,000 calls ถ้า `calculateLeaveBalance` มี loop วันลาข้างในอีก ก็หนักกว่านั้น

อีกเรื่องคือ `*ngFor` ไม่มี `trackBy` พอ assign `employees` ใหม่ (เช่นหลัง filter หรือ reload) Angular จะ destroy DOM ทั้ง 3,000 แถวแล้วสร้างใหม่หมด ทั้งที่ข้อมูลอาจเหมือนเดิมเกือบทั้งหมด

เรื่องที่สามคือ render 3,000 node พร้อมกัน ต่อให้คำนวณเร็วแค่ไหน browser ก็อืดอยู่ดี

## แก้ยังไง

ย้ายการคำนวณออกจาก template ไปทำครั้งเดียวตอนข้อมูลเปลี่ยน แล้วให้ template อ่านค่าที่คำนวณไว้แล้ว

```ts
interface EmployeeRow {
  id: number
  displayName: string
  leaveBalance: number
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  // ...
})
export class EmployeeListComponent {
  employees = signal<Employee[]>([])

  rows = computed<EmployeeRow[]>(() =>
    this.employees().map(emp => ({
      id: emp.id,
      displayName: this.formatName(emp),
      leaveBalance: this.calculateLeaveBalance(emp),
    }))
  )
}
```

```html
@for (row of rows(); track row.id) {
  <div>{{ row.displayName }} - {{ row.leaveBalance }} วัน</div>
}
```

`computed` จะคำนวณใหม่เฉพาะตอน `employees` เปลี่ยนจริง ส่วน `track row.id` ทำให้ Angular เอา DOM แถวเดิมมาใช้ซ้ำแทนที่จะสร้างใหม่ทั้งชุด

ถ้าโปรเจกต์ยังเป็น Angular เวอร์ชันเก่าที่ยังไม่มี signal กับ control flow ใหม่ ใช้แนวเดียวกันได้

```html
<div *ngFor="let row of rows; trackBy: trackById">
  {{ row.displayName }} - {{ row.leaveBalance }} วัน
</div>
```

```ts
trackById = (_: number, row: EmployeeRow) => row.id
```

แล้ว set `this.rows = ...` ตอนโหลดข้อมูลเสร็จหรือตอน filter

## 3,000 แถวยังเยอะอยู่

ต่อให้ไม่คำนวณซ้ำแล้ว การวาง 3,000 div ใน DOM ก็ยังทำให้หน้าหนัก แนะนำ virtual scroll จาก CDK วาดเฉพาะแถวที่มองเห็น

```html
<cdk-virtual-scroll-viewport itemSize="40" style="height: 600px">
  <div *cdkVirtualFor="let row of rows(); trackBy: trackById">
    {{ row.displayName }} - {{ row.leaveBalance }} วัน
  </div>
</cdk-virtual-scroll-viewport>
```

ข้อแม้คือทุกแถวต้องสูงเท่ากันตามที่ใส่ใน `itemSize` ถ้าความสูงไม่เท่ากันต้องใช้ `autosize` strategy ซึ่งทำงานหนักกว่า หรือถ้าหน้านี้เป็นตารางจริง ๆ ลองดู table component ที่มี virtual scroll ในตัวจะง่ายกว่า

## ทางเลือกถ้าไม่อยาก refactor เยอะ

ถ้าแก้โครงสร้างไม่ได้ตอนนี้ ใช้ pure pipe แทนการเรียก method ได้

```ts
@Pipe({ name: 'employeeName', pure: true })
export class EmployeeNamePipe implements PipeTransform {
  transform(emp: Employee): string {
    return formatName(emp)
  }
}
```

```html
{{ emp | employeeName }}
```

pure pipe จะ cache ผลไว้ และคำนวณใหม่ต่อเมื่อ reference ของ input เปลี่ยน แต่ข้อควรระวังคือถ้าโค้ดแก้ field ข้างใน object เดิมโดยไม่สร้าง object ใหม่ pipe จะไม่รู้ตัวและคืนค่าเก่า ตรงนี้เลยต้องยึดหลัก immutable ให้ตลอด ผมเลยมองว่าวิธีแรกสะอาดกว่าถ้ามีเวลาแก้

## สรุปลำดับความสำคัญ

1. เอา method call ออกจาก template คำนวณล่วงหน้าเก็บเป็น view model
2. ใส่ `track` / `trackBy`
3. เปิด `OnPush`
4. ใส่ virtual scroll

ข้อ 1 กับ 2 ได้ผลเยอะที่สุดและแก้ไม่นาน ถ้าส่งโค้ดของ `calculateLeaveBalance` มาดูด้วย เดี๋ยวผมช่วยเช็กให้ว่าข้างในมีอะไรที่หนักเกินจำเป็นไหมครับ
