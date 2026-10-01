รีวิวให้แล้วครับ ปัญหาหลักคือ nested subscribe ทั้งที่สอง request ไม่ได้ขึ้นต่อกันเลย `/api/departments` ไม่ได้ใช้ค่าจาก `res` สักนิด แต่ต้องรอ `/api/employees` เสร็จก่อนถึงจะยิง เวลาโหลดเลยกลายเป็นผลบวกของทั้งสองตัวแทนที่จะเป็นตัวที่ช้าที่สุด

## ปัญหาที่เจอ เรียงตามความสำคัญ

**1. subscribe ซ้อน subscribe**
นอกจากช้าแล้ว พอมี request ตัวที่สามสี่ โค้ดจะไล่ระดับลงไปเรื่อย ๆ จนอ่านไม่ออก ใช้ `forkJoin` ยิงพร้อมกันจบในที่เดียว

**2. ไม่มี unsubscribe**
ถ้าผู้ใช้เปลี่ยนหน้าก่อน request กลับมา callback ยังทำงานต่อแล้วเขียนค่าใส่ component ที่ destroy ไปแล้ว เคสนี้ `HttpClient` complete เองหลังได้ response ก็จริง แต่ระหว่างที่ยังค้างอยู่ก็ยังเกิด error ได้ และถ้าวันหลังเปลี่ยนไปใช้ stream ที่ไม่ complete เช่น `valueChanges` จะกลายเป็น memory leak เต็ม ๆ

**3. ไม่มี error handling**
ถ้า `/api/employees` พัง `/api/departments` จะไม่ยิงเลย และหน้าจอจะค้างอยู่แบบไม่มีอะไรบอกผู้ใช้ จะเห็นแค่ error ใน console

**4. ไม่ได้ใส่ generic**
`this.http.get('/api/employees')` คืน `Observable<Object>` ถ้า `employees` ประกาศเป็น `Employee[]` ไว้ TypeScript จะฟ้องตั้งแต่ compile ถ้าไม่ฟ้องแปลว่าประกาศเป็น `any` ไว้ ซึ่งก็เสีย type safety ทั้งเส้น

## เขียนใหม่

```ts
private readonly http = inject(HttpClient);
private readonly destroyRef = inject(DestroyRef);

employees: Employee[] = [];
departments: Department[] = [];
loading = true;
error: string | null = null;

ngOnInit() {
  forkJoin({
    employees: this.http.get<Employee[]>('/api/employees'),
    departments: this.http.get<Department[]>('/api/departments'),
  })
    .pipe(takeUntilDestroyed(this.destroyRef))
    .subscribe({
      next: ({ employees, departments }) => {
        this.employees = employees;
        this.departments = departments;
        this.loading = false;
      },
      error: (err: HttpErrorResponse) => {
        this.error = 'โหลดข้อมูลไม่สำเร็จ';
        this.loading = false;
      },
    });
}
```

ข้อควรรู้ของ `forkJoin` คือถ้าตัวใดตัวหนึ่ง error ทั้งชุด error หมด ถ้าอยากให้ departments พังแล้ว employees ยังแสดงได้ ให้ใส่ `catchError(() => of([]))` คร่อมเฉพาะตัวที่ยอมให้พังได้

## ถ้าอยากตัด subscribe ออกไปเลย

ให้ template จัดการผ่าน async pipe แทน ไม่ต้องมี `ngOnInit` ไม่ต้องห่วงเรื่อง unsubscribe และถ้าใช้ `OnPush` ก็ไม่ต้องเรียก `markForCheck` เอง

```ts
readonly data$ = forkJoin({
  employees: this.http.get<Employee[]>('/api/employees'),
  departments: this.http.get<Department[]>('/api/departments'),
});
```

```html
@if (data$ | async; as data) {
  <app-employee-list [employees]="data.employees" [departments]="data.departments" />
} @else {
  <app-spinner />
}
```

ถ้าโปรเจกต์ไปทาง signal แล้ว ใช้ `toSignal(this.data$)` ครอบอีกชั้นก็ได้ จะได้อ่านค่าตรง ๆ ใน template โดยไม่ต้องผ่าน async pipe

## กรณีที่สองตัวนี้ขึ้นต่อกันจริง

ถ้าในของจริง departments ต้องใช้ค่าจาก employees เช่นส่ง id ไปด้วย การ subscribe ซ้อนก็ยังไม่ใช่วิธีที่ควรใช้อยู่ดี ให้ต่อด้วย `switchMap` แทน จะได้ยกเลิก request เก่าอัตโนมัติเวลามีค่าใหม่เข้ามา

```ts
this.http.get<Employee[]>('/api/employees').pipe(
  tap(employees => this.employees = employees),
  switchMap(employees => this.http.get<Department[]>(`/api/departments?ids=${...}`)),
  takeUntilDestroyed(this.destroyRef),
).subscribe(departments => this.departments = departments);
```

ถ้าบอกมาว่าโปรเจกต์ใช้ Angular เวอร์ชันไหนและเปิด `OnPush` ไว้หรือเปล่า ผมจะปรับตัวอย่างให้ตรงกับที่ใช้อยู่จริงได้ครับ
