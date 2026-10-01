รีวิวให้ครับ โค้ดสั้นแต่มีประเด็นที่ควรแก้อยู่หลายข้อ เรียงตามความสำคัญนะครับ

## ปัญหาหลัก

**1. Nested subscribe ทั้งที่สองคำขอไม่ได้ขึ้นต่อกัน** (สำคัญสุด)

`/api/departments` ไม่ได้ใช้ผลลัพธ์จาก `/api/employees` เลย แต่โค้ดบังคับให้รอกันเป็นทอด ๆ — เวลาโหลดกลายเป็น latency ของสองคำขอบวกกัน ทั้งที่ยิงขนานกันได้ และยิ่งซ้อนลึกก็ยิ่งกลายเป็น callback hell

**2. ไม่มี error handling**

ไม่มี `error` callback เลย ถ้า `/api/employees` พัง → `departments` ไม่ถูกเรียกเลยสักครั้ง และผู้ใช้เห็นหน้าว่างโดยไม่รู้สาเหตุ error จะหลุดไปที่ global `ErrorHandler` เงียบ ๆ

**3. ไม่ unsubscribe**

`HttpClient` complete เองหลัง emit ครั้งเดียวจริง แต่ถ้า component ถูก destroy ก่อน response กลับมา (ผู้ใช้กดเปลี่ยนหน้าเร็ว ๆ) callback จะยังทำงานและไปเซ็ต state ของ component ที่ตายแล้ว — ควรผูกกับ lifecycle ด้วย `takeUntilDestroyed`

**4. ไม่มี type**

`this.http.get('/api/employees')` คืน `Observable<Object>` ซึ่งหมายความว่า `this.employees` น่าจะถูกประกาศเป็น `any` อยู่ (ไม่งั้นใน strict mode คอมไพล์ไม่ผ่าน) เสียประโยชน์ของ TypeScript ไปทั้งหมด

**5. เรียก HttpClient ตรงจาก component**

URL ถูก hardcode ในชั้น UI ทำให้เทสยาก reuse ไม่ได้ และไม่มีที่ให้ใส่ base URL / mapping ควรย้ายไปไว้ใน service

**6. ไม่มี loading / empty state**

ช่วงรอ response ผู้ใช้ไม่เห็นอะไรเลย

## เวอร์ชันที่ปรับแล้ว

ย้าย HTTP ไปไว้ใน service ก่อน:

```ts
@Injectable({ providedIn: 'root' })
export class EmployeeApiService {
  private readonly http = inject(HttpClient);

  getEmployees(): Observable<Employee[]> {
    return this.http.get<Employee[]>('/api/employees');
  }

  getDepartments(): Observable<Department[]> {
    return this.http.get<Department[]>('/api/departments');
  }
}
```

แล้วใน component ใช้ `forkJoin` ยิงขนาน:

```ts
export class EmployeeListComponent implements OnInit {
  private readonly api = inject(EmployeeApiService);
  private readonly destroyRef = inject(DestroyRef);

  employees: Employee[] = [];
  departments: Department[] = [];
  loading = false;
  error: string | null = null;

  ngOnInit(): void {
    this.loading = true;
    this.error = null;

    forkJoin({
      employees: this.api.getEmployees(),
      departments: this.api.getDepartments(),
    })
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ employees, departments }) => {
          this.employees = employees;
          this.departments = departments;
        },
        error: (err: HttpErrorResponse) => {
          this.error = 'โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่อีกครั้ง';
          console.error(err);
        },
      });
  }
}
```

`forkJoin` รอให้ครบทั้งคู่แล้วค่อย emit ทีเดียว ถ้าอยากให้ส่วนไหนแสดงผลทันทีที่มาถึง ใช้ `combineLatest` กับ `startWith` แทนได้

## ทางเลือกที่สะอาดกว่า

ถ้าโปรเจกต์อยู่บน Angular เวอร์ชันใหม่ ลองพิจารณา `httpResource` + signals ครับ ตัดเรื่อง subscribe/unsubscribe และ loading state ออกไปได้ทั้งหมด:

```ts
readonly employees = httpResource<Employee[]>(() => '/api/employees');
readonly departments = httpResource<Department[]>(() => '/api/departments');
// template: employees.value() / employees.isLoading() / employees.error()
```

หรือถ้ายังอยู่กับ RxJS ก็ใช้ `async` pipe รับ observable ตรง ๆ ใน template แทนการ `subscribe` เองใน `ngOnInit` — Angular จะจัดการ unsubscribe ให้ และเข้ากับ `OnPush` ได้ดีกว่า

## ข้อยกเว้นที่ควรเช็ก

ถ้าจริง ๆ แล้ว `/api/departments` **ต้อง** ใช้ข้อมูลจาก employees (เช่นส่ง department ids ไปด้วย) การยิงเรียงกันก็ถูกต้องแล้ว — แต่ให้เปลี่ยนจาก nested subscribe เป็น `switchMap` แทน เพื่อให้ยกเลิกคำขอเก่าได้และ error handling รวมอยู่ที่เดียว
