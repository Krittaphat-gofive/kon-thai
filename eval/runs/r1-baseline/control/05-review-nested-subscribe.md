รีวิวโค้ดนี้ให้ครับ — มีปัญหาหลักอยู่ 5 จุด เรียงตามความสำคัญ

## 1. Nested subscribe ทั้งที่ request ไม่ได้ขึ้นต่อกัน (สำคัญสุด)

`/api/departments` ไม่ได้ใช้ข้อมูลจาก `/api/employees` เลย แต่โค้ดบังคับให้รอกันเป็นทอด ๆ — เวลาโหลดกลายเป็น `t1 + t2` แทนที่จะเป็น `max(t1, t2)` ควรยิงขนานด้วย `forkJoin`

## 2. ไม่มี error handling

`subscribe(fn)` แบบนี้รับแค่ `next` ถ้า API พัง error จะหลุดไปเป็น unhandled error ใน console และ UI ค้างอยู่ที่หน้าว่าง ๆ โดยผู้ใช้ไม่รู้เรื่อง

## 3. ไม่มี unsubscribe

`HttpClient` complete เองหลังยิงครั้งเดียว จึงไม่ใช่ memory leak ถาวร แต่ถ้า user ออกจากหน้าก่อน response กลับมา: request ไม่ถูก cancel และ callback ยังทำงาน set ค่าให้ component ที่ destroy ไปแล้ว ควรใส่ `takeUntilDestroyed`

## 4. ไม่ระบุ generic type

`this.http.get('/api/employees')` คืน `Observable<Object>` — `res` เลยเป็น `Object` ไม่ใช่ `Employee[]` ทำให้เสีย type safety ทั้งเส้น ควรเป็น `.get<Employee[]>(...)`

## 5. เรียก HTTP ตรงจาก component + hardcode URL

Component ไม่ควรรู้จัก endpoint path ควรย้ายไป service เพื่อให้ test ง่ายและเปลี่ยน base URL ตาม environment ได้

---

## เวอร์ชันที่แนะนำ

**Service:**

```ts
@Injectable({ providedIn: 'root' })
export class EmployeeService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  getEmployees(): Observable<Employee[]> {
    return this.http.get<Employee[]>(`${this.baseUrl}/employees`);
  }

  getDepartments(): Observable<Department[]> {
    return this.http.get<Department[]>(`${this.baseUrl}/departments`);
  }
}
```

**Component:**

```ts
export class EmployeeListComponent implements OnInit {
  private readonly employeeService = inject(EmployeeService);
  private readonly destroyRef = inject(DestroyRef);

  employees: Employee[] = [];
  departments: Department[] = [];
  loading = false;
  error: string | null = null;

  ngOnInit(): void {
    this.loading = true;

    forkJoin({
      employees: this.employeeService.getEmployees(),
      departments: this.employeeService.getDepartments(),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ employees, departments }) => {
          this.employees = employees;
          this.departments = departments;
          this.loading = false;
        },
        error: (err) => {
          this.error = 'โหลดข้อมูลไม่สำเร็จ';
          this.loading = false;
        },
      });
  }
}
```

ข้อควรรู้: `forkJoin` จะ error ทั้งก้อนถ้ามี request ใดพัง ถ้าอยากให้อีกตัวยังแสดงได้ ให้ `.pipe(catchError(() => of([])))` ครอบแต่ละ stream แยกกัน

## ถ้าใช้ Angular เวอร์ชันใหม่

- **ใช้ signal อยู่แล้ว** — `rxResource` / `httpResource` จะจัดการ loading, error, cancel ให้ครบในตัว ไม่ต้องเขียน state สามตัวเอง (ตรวจเวอร์ชันโปรเจกต์ก่อน เพราะ API ชุดนี้เพิ่งนิ่งใน Angular 20)
- **ไม่ได้ใช้ signal** — ยิงด้วย `async` pipe ใน template ไปเลย จะได้ไม่ต้อง subscribe เองและเข้ากับ `OnPush` ได้ทันที

## กรณีที่ nested ถูกต้อง

ถ้าในของจริง departments ต้องใช้ข้อมูลจาก employees (เช่น ส่ง department id ที่ได้จาก employee) nested subscribe ก็ยังผิดอยู่ดี — ให้ใช้ `switchMap` แทน เพื่อให้ยัง cancel ได้และ error รวมอยู่ใน stream เดียว:

```ts
this.employeeService.getEmployees().pipe(
  tap(employees => this.employees = employees),
  switchMap(employees => this.employeeService.getDepartmentsFor(employees)),
  takeUntilDestroyed(this.destroyRef),
).subscribe({ /* ... */ });
```
