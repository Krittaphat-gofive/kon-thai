ปัญหาหลักคือ subscribe ซ้อน subscribe ทั้งที่สอง request ไม่ได้ขึ้นต่อกันเลยครับ

### ประเด็นที่เจอ

**1. โหลดช้ากว่าที่ควร**
`/api/departments` ต้องรอ `/api/employees` ตอบกลับมาก่อน ทั้งที่ไม่ได้ใช้ข้อมูลจากกัน ยิงพร้อมกันได้ เวลารวมจะเหลือเท่า request ที่ช้าที่สุดแทนที่จะเป็นผลบวกของสองตัว

**2. ไม่มี unsubscribe**
`HttpClient` complete เองหลังได้ response ก็จริง แต่ถ้าผู้ใช้เปลี่ยนหน้าก่อน response กลับมา callback ยังทำงานและไป set field ของ component ที่ destroy ไปแล้ว ถ้าข้างในมี logic อย่าง `router.navigate` หรือเปิด dialog ต่อ จะเห็นอาการชัดเลย

**3. ไม่มี error handling**
ถ้า request พัง จะ error หลุดไปที่ global handler แล้วหน้าจอค้างอยู่สถานะ loading โดยไม่บอกอะไรผู้ใช้

**4. ไม่มี type**
`res` เป็น `Object` แล้วเอาไป assign ให้ `this.employees` ตรง ๆ TypeScript ช่วยอะไรไม่ได้เลย ควรใส่ generic `get<Employee[]>(...)`

**5. component เรียก HttpClient ตรง**
path `/api/employees` ฝังอยู่ใน component ทำให้ reuse ไม่ได้และ test ยาก ย้ายไปไว้ service จะดีกว่า

### เขียนใหม่

```ts
private readonly destroyRef = inject(DestroyRef);

ngOnInit() {
  forkJoin({
    employees: this.employeeService.getAll(),
    departments: this.departmentService.getAll(),
  })
    .pipe(takeUntilDestroyed(this.destroyRef))
    .subscribe({
      next: ({ employees, departments }) => {
        this.employees = employees;
        this.departments = departments;
      },
      error: () => (this.loadError = true),
    });
}
```

`forkJoin` ยิงพร้อมกันแล้วรอครบค่อยปล่อยค่าออกมาทีเดียว ส่วน `takeUntilDestroyed` ตัด subscription ทิ้งตอน component ตาย

ถ้าไม่อยาก subscribe เองเลย เก็บเป็น field แล้วให้ template จัดการก็ได้

```ts
readonly data$ = forkJoin({ ... });
```

```html
@if (data$ | async; as data) { ... }
```

### ข้อสังเกตเพิ่ม

ถ้าวันหลังเจอเคสที่ request ที่สองต้องใช้ค่าจาก request แรกจริง ๆ อย่ากลับไป subscribe ซ้อน ให้ใช้ `switchMap` แทน จะได้ยกเลิกของเก่าอัตโนมัติเวลามี request ใหม่เข้ามา

อีกเรื่องคือถ้าโปรเจกต์อยู่ Angular 19 ขึ้นไปและย้ายไป signal แล้ว `rxResource` กับ `httpResource` จัดการ loading, error และการยกเลิกให้ครบในตัวเดียว แต่ API ยังอยู่ช่วง experimental อยู่ ต้องรับความเสี่ยงเรื่อง breaking change ด้วย

บอกได้ว่าโปรเจกต์ใช้ Angular เวอร์ชันไหนและเป็น signal-based หรือยัง เดี๋ยวปรับตัวอย่างให้ตรงกว่านี้ครับ
