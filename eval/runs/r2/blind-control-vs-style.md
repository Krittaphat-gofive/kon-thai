# เทียบแบบ blind (r2)

อ่านแต่ละข้อแล้วเขียน A หรือ B หลังคำว่า `เลือก:` ว่าอันไหนฟังเป็นคนไทยกว่า
ถ้าพอ ๆ กันให้เขียน = เสร็จแล้วรัน `reveal`

## 01-error-angular

> รัน ng serve แล้วเจอ error นี้ใน console หมายความว่าอะไร แก้ยังไง
> 
> ```
> NG0100: ExpressionChangedAfterItHasBeenCheckedError: Expression has changed after it was checked. Previous value: 'false'. Current value: 'true'.
> ```

### A

## มันหมายความว่าอะไร

ในโหมด dev, Angular จะรัน change detection **สองรอบต่อหนึ่ง tick** — รอบแรกอัปเดต DOM จริง รอบที่สองเป็นรอบ "ตรวจทาน" ว่าค่าทุก binding ยังเท่าเดิมไหม

ถ้าค่าของ binding เปลี่ยนระหว่างสองรอบนี้ แปลว่ามีโค้ดไปแก้ state **หลังจาก Angular เช็ค binding นั้นไปแล้วในรอบเดียวกัน** → Angular โยน NG0100 ทิ้ง เพราะถ้าปล่อยไว้ DOM กับ model จะไม่ตรงกัน (view จะค้างค่าเก่าอยู่ 1 tick)

ข้อความ `Previous: 'false' → Current: 'true'` บอกว่าเป็น binding แบบ boolean — เดาได้ว่าพวก `isLoading`, `disabled`, `*ngIf="showX"`, `[class.active]`

> ⚠️ error นี้ **ขึ้นเฉพาะ dev mode** — prod จะเงียบ แต่บั๊กยังอยู่ (view อาจแสดงค่าเก่า 1 เฟรม) อย่าแก้ด้วยการ build prod แล้วบอกว่าหายนะครับ

## สาเหตุที่เจอบ่อย เรียงตามความถี่

1. **เซ็ตค่าใน `ngAfterViewInit`** ที่ template ผูกอยู่ — ตัวนี้คลาสสิกที่สุด เพราะ `ngAfterViewInit` ทำงาน *หลัง* Angular เช็ค binding ของ view ไปแล้ว
2. **Child component แก้ state ของ parent** ตอน `ngOnInit`/`ngAfterViewInit` (ผ่าน `@Output`, shared service, หรือ `BehaviorSubject`)
3. **Getter / method ใน template** ที่คืนค่า object/array ใหม่ทุกครั้ง — identity เปลี่ยนทุกรอบ CD
4. **Subscribe แล้ว emit แบบ synchronous** ระหว่าง CD pass
5. **ชน third-party / CDK overlay** (tooltip, virtual scroll, dialog)

## วิธีหาตัวต้นเหตุ

ขยาย stack trace ใน console — เฟรมที่ชี้ไปที่ `*_Template` หรือชื่อ component ของคุณคือจุดที่ binding อยู่ แล้วหาว่าใครไปเซ็ตค่านั้น ถ้ายังไม่เจอ ใส่ setter ดัก:

```ts
private _isLoading = false;
get isLoading() { return this._isLoading; }
set isLoading(v: boolean) {
  console.trace('isLoading =', v);   // stack trace จะบอกว่าใครเรียก
  this._isLoading = v;
}
```

## วิธีแก้ เรียงจากดีที่สุดไปแย่สุด

### 1. ย้าย logic ให้เกิดก่อน CD pass (ดีที่สุด)

ถ้าไม่ได้ต้องการ DOM จริง ให้ย้ายจาก `ngAfterViewInit` → `ngOnInit` หรือ constructor:

```ts
// ❌ สาย: Angular เช็ค binding ไปแล้ว
ngAfterViewInit() { this.isLoading = true; }

// ✅ ทันรอบแรก
ngOnInit() { this.isLoading = true; }
```

### 2. ใช้ signals (ถ้าโปรเจกต์ขึ้น signal แล้ว)

Derived state ที่เป็น `computed()` จะไม่เกิดปัญหานี้ เพราะไม่ได้ "เซ็ต" ระหว่าง CD แต่คำนวณตาม dependency:

```ts
isLoading = signal(false);
canSubmit = computed(() => !this.isLoading() && this.form().valid);
```

และเลิกใช้ getter แบบนี้ใน template:

```ts
// ❌ คืน array ใหม่ทุกรอบ CD
get activeItems() { return this.items.filter(i => i.active); }

// ✅
activeItems = computed(() => this.items().filter(i => i.active));
```

### 3. `cdr.detectChanges()` — กรณีต้องวัด DOM จริง

ถ้าเลี่ยงไม่ได้เพราะต้องอ่านขนาด element ก่อน (เคสนี้ถือว่า legitimate):

```ts
private cdr = inject(ChangeDetectorRef);

ngAfterViewInit() {
  this.showScrollButton = this.el.nativeElement.scrollWidth > this.el.nativeElement.clientWidth;
  this.cdr.detectChanges();   // สั่งรัน CD รอบใหม่ให้ค่าตรงกันก่อนรอบตรวจทาน
}
```

Angular 17+ มีทางที่สะอาดกว่า — `afterNextRender()` ซึ่งรันหลัง render เสร็จ นอกรอบ CD:

```ts
constructor() {
  afterNextRender(() => {
    this.showScrollButton = /* วัด DOM */;
  });
}
```

### 4. เลื่อนไป microtask (ทางหนีทีไล่)

```ts
Promise.resolve().then(() => this.isLoading = true);
```

ใช้ `Promise.resolve()` ดีกว่า `setTimeout(..., 0)` เพราะเป็น microtask → รันก่อน browser paint จึงไม่เห็นภาพกระพริบ แต่ถือเป็นการปิดอาการ ไม่ใช่แก้ root cause — ควรใช้เมื่อปัญหามาจาก third-party lib ที่แก้ไม่ได้

---

ถ้าบอกได้ว่า binding ตัวไหน (จาก stack trace) และ lifecycle hook ไหนที่เซ็ตค่า ผมช่วยดูให้เจาะจงกว่านี้ได้ครับ

### B

แปลว่า Angular เช็ก binding ของ component ไปรอบหนึ่งแล้ว พอวนกลับมาตรวจทานซ้ำ ค่ากลับเปลี่ยนไปแล้วครับ

ใน dev mode Angular จะรัน change detection สองรอบต่อหนึ่ง cycle รอบแรกคือรอบจริงที่เอาค่าไปใส่ DOM รอบสองเป็นรอบตรวจทานว่าค่ายังเหมือนเดิมไหม ถ้าไม่เหมือน แปลว่ามีโค้ดไปแก้ค่าหลังจากเช็กไปแล้ว ซึ่งผิดกฎ one-way data flow ที่ Angular ยึดอยู่ คือข้อมูลต้องไหลจาก parent ลง child ทางเดียวต่อหนึ่งรอบ

อีกเรื่องที่ควรรู้คือ prod build จะไม่ขึ้น error นี้ เพราะไม่มีรอบตรวจทาน แต่ไม่ได้แปลว่าหาย ของจริงคือ UI มีจังหวะที่แสดงค่าไม่ตรงกับ state อยู่แวบหนึ่ง

## สาเหตุที่เจอบ่อย

ข้อความ `Previous value: 'false'. Current value: 'true'` บอกว่าเป็นค่า boolean เกือบทั้งหมดจะเป็นพวก flag อย่าง `isLoading`, `disabled`, `*ngIf` เรียงตามความถี่ที่เจอ

1. แก้ค่าใน `ngAfterViewInit` หรือ `ngAfterViewChecked` ตอนนั้น Angular เช็ก template ไปเรียบร้อยแล้ว
2. parent bind ค่าที่มาจาก child เช่น อ่านผ่าน `@ViewChild` แล้วเอาไปใช้ใน template ของตัวเอง เพราะ change detection ไหลจากบนลงล่าง กว่า child จะมีค่า parent ก็เช็กผ่านไปแล้ว
3. getter ใน template ที่คืน reference ใหม่ทุกครั้งที่เรียก เช่น สร้าง array ใหม่ หรือ `new Date()`
4. service กลางที่ component อื่น set ค่าตอน init เช่น loading service, breadcrumb, page title
5. `BehaviorSubject` ที่ emit ทันทีแบบ synchronous ตอน subscribe ใน lifecycle hook ที่สายเกินไป

## วิธีหาตัวต้นเหตุ

stack trace ของ error นี้มักไม่ค่อยช่วย ให้ไล่จาก template แทน หา binding ที่เป็น boolean ทั้งหมด (`*ngIf`, `[disabled]`, `[class.xxx]`) แล้วดูว่าตัวไหนมีโค้ดไปเซ็ตใน `ngAfterViewInit` หรือใน subscribe วิธีเร็วสุดคือ comment ทีละตัวดูว่าตัวไหนทำให้ error หาย

## วิธีแก้

**ย้าย logic ไป `ngOnInit`** เคสส่วนใหญ่จบตรงนี้ ถ้าโค้ดที่เซ็ต flag ไม่ได้ต้องการ DOM จริง ๆ ก็ไม่มีเหตุผลต้องรอถึง `ngAfterViewInit`

**ถ้าจำเป็นต้องรอ view จริง ๆ** เช่น ต้องวัดขนาด element หรืออ่านค่าจาก `@ViewChild` ให้สั่งเช็กใหม่อีกรอบ เป็นการบอก Angular ตรง ๆ ว่ารู้ตัวว่าเปลี่ยนค่า

```ts
constructor(private cdr: ChangeDetectorRef) {}

ngAfterViewInit() {
  this.hasOverflow = this.content.nativeElement.scrollHeight > 300;
  this.cdr.detectChanges();
}
```

ถ้า component ใช้ `OnPush` ให้ใช้ `markForCheck()` แทน

**เลี่ยง getter ที่สร้าง reference ใหม่** ย้ายไปคำนวณตอนที่ค่าเปลี่ยนจริง หรือทำเป็น pure pipe

**`setTimeout` หรือ `Promise.resolve().then()`** ใช้ได้ แต่เป็นการแก้ที่ปลายเหตุ คือแค่เลื่อนการเซ็ตค่าไป tick ถัดไปให้พ้นรอบตรวจทาน เก็บไว้ใช้ตอนที่แก้โครงสร้างไม่ได้จริง ๆ อย่าใส่ไปทั่วทั้งโปรเจกต์

อีกทางถ้าอยู่ Angular 16 ขึ้นไป ลองย้าย flag พวกนี้ไปเป็น `signal` กับ `computed` ดู ค่าที่อ่านได้จะตรงกันทั้ง cycle ตัดปัญหาแบบนี้ไปได้เกือบหมด

ถ้าส่งโค้ด component กับ template ที่เจอมาให้ดู เดี๋ยวชี้บรรทัดที่เป็นต้นเหตุให้ครับ

เลือก: 

---

## 02-error-dotnet

> API ตอบ 500 แล้วใน log มีแบบนี้ ช่วยอธิบายหน่อยว่าเกิดจากอะไร
> 
> ```
> System.InvalidOperationException: A second operation was started on this context instance before a previous operation completed. This is usually caused by different threads concurrently using the same instance of DbContext.
> ```

### A

เกิดจากการเอา DbContext ตัวเดียวไปยิง query พร้อมกันสองงานครับ

ตัว DbContext ออกแบบมาให้ทำงานทีละอย่าง ไม่ได้ thread-safe พอมี operation ที่สองเริ่มตอนที่ตัวแรกยังไม่เสร็จ EF Core ก็โยน exception ตัวนี้ออกมาเลย แล้ว API ก็ตอบ 500

## เคสที่เจอบ่อย

**1. ลืม await**

```csharp
_context.Orders.ToListAsync();                      // ไม่มี await
var users = await _context.Users.ToListAsync();     // ชนกับตัวบน
```

**2. `Task.WhenAll` บน context เดียว**

```csharp
var t1 = _context.Orders.ToListAsync();
var t2 = _context.Users.ToListAsync();
await Task.WhenAll(t1, t2);
```

อ่านแล้วเหมือนจะเร็วขึ้น แต่จริง ๆ พังเพราะสอง task แชร์ context ตัวเดียวกัน

**3. `Parallel.ForEach` หรือ `Task.Run` ที่ข้างในเรียก repository ตัวเดิม**

**4. DI lifetime ผิด**

ลงทะเบียน DbContext เป็น Singleton หรือ inject เข้าไปใน singleton service เช่น `BackgroundService` พอมีหลาย request เข้ามาพร้อมกัน ก็ใช้ instance เดียวกันหมด อาการของข้อนี้คือบางทีพัง บางทีไม่พัง ขึ้นกับจังหวะ traffic

**5. วน loop บน `IQueryable` ที่ยังไม่ materialize**

```csharp
foreach (var order in _context.Orders.Where(x => x.IsActive))   // ยัง stream อยู่
{
    var user = await _context.Users.FindAsync(order.UserId);    // ยิงซ้อนเข้าไป
}
```

## ไล่หาจุดที่พังยังไง

ดู stack trace ว่าหลุดมาจาก method ไหน แล้วไล่ขึ้นไปหา `Task.WhenAll`, `Parallel.`, `Task.Run` และ async call ที่ไม่มี `await` นำหน้า

ถ้าอยากกวาดทีเดียว ให้ปรับ warning CS4014 (call is not awaited) เป็น error ใน csproj จะเจอจุดที่ลืม await ครบทั้ง solution

## วิธีแก้

- ใส่ `await` ให้ครบทุก async call
- ถ้าต้องการยิงขนานจริง ๆ ให้แต่ละ task มี context ของตัวเอง ใช้ `IDbContextFactory`

```csharp
builder.Services.AddDbContextFactory<AppDbContext>(opt => ...);

await using var ctx = await _factory.CreateDbContextAsync();
```

- ใน background service ให้สร้าง scope เองทุกรอบ อย่าเก็บ DbContext ไว้เป็น field

```csharp
using var scope = _scopeFactory.CreateScope();
var ctx = scope.ServiceProvider.GetRequiredService<AppDbContext>();
```

- ปิด query ด้วย `ToListAsync()` ก่อน แล้วค่อยวน loop

อีกเรื่องที่ควรรู้คือปัญหานี้ reproduce ยากบนเครื่องตัวเอง เพราะยิงทีละ request พอขึ้น production ที่ request ชนกันถึงจะโผล่ ถ้าเจอเฉพาะบน production ให้สงสัยข้อ 4 ก่อนเลย

ถ้าแปะ stack trace กับโค้ดของ method ที่พังมา เดี๋ยวชี้บรรทัดให้ครับ

### B

## สาเหตุของ error นี้

`DbContext` ของ EF Core **ไม่ thread-safe และรองรับได้แค่ 1 operation ต่อครั้ง** (มี internal lock ตัวหนึ่งคอยกัน) ตัว instance หนึ่งจะทำ query/SaveChanges ได้ทีละอันเท่านั้น ถ้ามี operation ที่ 2 เข้ามาตอนที่อันแรกยังไม่จบ → โยน `InvalidOperationException` ตัวนี้ทันที แล้ว API เลยกลายเป็น 500

ประเด็นคือ "operation แรกยังไม่จบ" ไม่ได้แปลว่าต้องมีหลาย thread จริง ๆ เสมอไป — แค่ `Task` ที่ยัง pending อยู่ก็นับแล้ว

## สาเหตุที่พบบ่อย เรียงจากเจอมากสุด

**1. ลืม `await`** (เจอบ่อยที่สุด)

```csharp
// ผิด - method ส่ง Task กลับไปโดยยังทำงานไม่เสร็จ
_db.SaveChangesAsync();              // ลืม await
var user = GetUserAsync(id);         // ลืม await แล้วเอาไปใช้ต่อ

// ผิด - fire and forget
_ = Task.Run(() => _logService.WriteAsync(...));  // ใช้ DbContext ตัวเดียวกับ request
```
ลองไล่ดู warning **CS4014** ใน build output ก่อนเลย ปกติมันฟ้องไว้แล้ว

**2. ยิง query พร้อมกันด้วย `Task.WhenAll`**

```csharp
// ผิด - ทุก task ใช้ _db ตัวเดียวกัน
var results = await Task.WhenAll(
    _db.Orders.CountAsync(),
    _db.Customers.CountAsync(),
    _db.Products.CountAsync());

// ผิดแบบเดียวกัน
var tasks = ids.Select(id => _db.Items.FirstOrDefaultAsync(x => x.Id == id));
await Task.WhenAll(tasks);
```

**3. `Parallel.ForEach` / `Task.Run` หลายตัว ที่แชร์ DbContext เดียวกัน**

**4. DbContext ถูกลงทะเบียนเป็น Singleton หรือโดน singleton ถือไว้ (captive dependency)**

```csharp
// ผิด
services.AddDbContext<AppDbContext>(opt => ..., ServiceLifetime.Singleton);
```
หรือ service ที่เป็น Singleton / `BackgroundService` ไป inject `AppDbContext` ตรง ๆ แล้วใช้ร่วมกันทุก request → 2 request พร้อมกันเมื่อไหร่ก็พัง (อาการคลาสสิกคือ "เทสคนเดียวไม่เป็น พอขึ้น prod คนใช้เยอะแล้วเป็น")

**5. ยิง query ซ้อนตอนกำลัง stream ผลลัพธ์อยู่**

```csharp
// ผิด - query นอกยังไม่ปิด reader แล้วยิงอันในเข้าไป
foreach (var order in _db.Orders.Where(x => x.IsActive))   // ยังไม่ได้ ToList
{
    order.Customer = await _db.Customers.FindAsync(order.CustomerId);
}
```
รวมถึง **lazy loading** (`UseLazyLoadingProxies`) ที่เผลอ trigger navigation property ระหว่าง loop ลักษณะนี้

**6. Blazor Server / SignalR** — scope มีอายุยาวเท่า circuit แล้ว event หลายตัวยิงพร้อมกัน

## วิธีแก้

| กรณี | วิธีแก้ |
|---|---|
| ลืม await | ใส่ `await` ให้ครบ, เปิด warning CS4014 เป็น error |
| ต้องยิงขนาน | ใช้ `IDbContextFactory<T>` สร้าง context แยกต่อ task |
| Background job | `using var scope = _scopeFactory.CreateScope();` แล้ว resolve DbContext ในนั้น |
| Singleton | เปลี่ยนเป็น Scoped (default ของ `AddDbContext` อยู่แล้ว) |
| query ซ้อน loop | `ToListAsync()` ให้จบก่อนเข้า loop หรือใช้ `Include()` |

ตัวอย่างแบบ factory:

```csharp
// Program.cs
builder.Services.AddDbContextFactory<AppDbContext>(opt =>
    opt.UseSqlServer(conn));

// ใช้งาน
var tasks = ids.Select(async id =>
{
    await using var db = await _factory.CreateDbContextAsync();
    return await db.Items.FirstOrDefaultAsync(x => x.Id == id);
});
var items = await Task.WhenAll(tasks);
```

ถ้ายังแยกขนานไม่ได้จริง ๆ ก็เปลี่ยนเป็น sequential ไปก่อน แล้วค่อย optimize ทีหลัง — ปลอดภัยกว่า

## วิธีหาจุดเกิดเหตุ

ดู **stack trace เต็ม ๆ** จะเห็น frame ของ method ตัวเองที่เรียก query — ไล่ย้อนจากตรงนั้นว่าใครเรียกซ้อน ถ้าแปะ stack trace กับโค้ด method นั้นมา ช่วยชี้จุดให้ได้ตรงกว่านี้ครับ

อีกจุดที่ควรเช็ก: อาการ "เป็นบ้างไม่เป็นบ้าง" + เกิดตอนคนใช้เยอะ มักชี้ไปที่ข้อ 4 (lifetime ผิด) มากกว่าข้อ 1

เลือก: 

---

## 03-concept-signal

> อธิบาย signal ใน Angular ให้หน่อย ต่างจาก RxJS Observable ยังไง แล้วควรใช้อะไรตอนไหน

### A

## Signal คืออะไร

Signal คือ "กล่องเก็บค่า" ที่รู้ว่าใครอ่านมันอยู่บ้าง เวลาค่าเปลี่ยนมันจะไปบอกคนที่อ่านให้คำนวณใหม่เอง — เป็น reactive primitive ที่ Angular ทำขึ้นมาเองเพื่อแทนที่กลไก change detection แบบเดิม (Zone.js)

```ts
const count = signal(0);           // writable signal
const double = computed(() => count() * 2);  // derived, lazy + memoized

count();        // อ่านค่า — synchronous, ได้ค่าทันที
count.set(5);
count.update(c => c + 1);

effect(() => console.log(count(), double()));  // side effect, track dependency อัตโนมัติ
```

จุดสำคัญที่คนมักมองข้าม: **ไม่ต้องประกาศ dependency** Angular ดูจากว่าในฟังก์ชันเรียก signal ตัวไหนบ้างตอน runtime แล้วสร้างกราฟ dependency ให้เอง และ `computed` เป็น **lazy** — ถ้าไม่มีใครอ่าน มันไม่คำนวณเลย

API ที่เกี่ยวข้องในระบบนิเวศนี้: `input()` / `model()` / `viewChild()` / `contentChild()` (signal-based แทน decorator), `linkedSignal()` (state ที่ reset ตาม source ได้), `resource()` / `httpResource()` (async loading เป็น signal) — ตัวหลัง ๆ มาใน v19–v20 ควรเช็กเวอร์ชันที่โปรเจกต์ใช้ก่อน

---

## ต่างจาก Observable ยังไง

| | Signal | Observable |
|---|---|---|
| ค่าปัจจุบัน | มีเสมอ อ่านแบบ sync ได้ | ไม่มีจนกว่าจะ emit (ยกเว้น `BehaviorSubject`) |
| เวลา / async | ไม่รู้จักเวลา — เป็น snapshot ของ state | ออกแบบมาเพื่อ stream ที่ไหลตามเวลา |
| Operators | น้อยมาก (`computed`, `effect`) | 100+ ตัว: `debounce`, `retry`, `switchMap`, ... |
| การ cleanup | อัตโนมัติตาม injection context | ต้อง unsubscribe / `takeUntilDestroyed` เอง |
| ซ้ำค่าเดิม | ตัดทิ้งให้ด้วย `Object.is` | emit ทุกครั้ง จนกว่าจะใส่ `distinctUntilChanged` |
| Cold / Hot | เป็นค่าเดียวที่แชร์กัน (hot เสมอ) | cold by default — subscribe ใหม่ = รันใหม่ |
| Error / Complete | ไม่มี channel พวกนี้ | มีครบ |
| Change detection | ผูกกับ CD โดยตรง → zoneless ได้ | ต้องผ่าน `async` pipe หรือ `markForCheck` |

### สองเรื่องที่ต่างกันเชิงแนวคิดจริง ๆ

**1. Push vs. push-pull**
Observable *ผลัก* ค่าออกมาทุกครั้งที่มี ส่วน signal แค่ผลัก "สัญญาณว่าเปลี่ยนแล้ว" ออกไป แล้วปลายทางค่อย *ดึง* ค่าตอนที่ต้องใช้จริง ผลคือ chain ยาว ๆ ของ `computed` ที่ไม่มีใครอ่านจะไม่ถูกคำนวณเลย

**2. Glitch-free**
อันนี้คือข้อได้เปรียบที่ชัดที่สุดของ signal

```ts
// RxJS — combineLatest ยิง 2 ครั้ง ครั้งแรกเป็นค่า inconsistent
const total$ = combineLatest([price$, qty$]).pipe(map(([p, q]) => p * q));
// เปลี่ยน price จาก source เดียวกัน → total$ emit ค่ากลางที่ผิดก่อน 1 ครั้ง

// Signal — computed เห็นค่าที่ consistent เสมอ คำนวณครั้งเดียว
const total = computed(() => price() * qty());
```

Signal แก้ปัญหา diamond dependency ให้ในตัว ส่วน RxJS ต้องจัดการเอง

---

## ควรใช้อะไรตอนไหน

กฎที่ใช้ได้จริงที่สุด: **state → signal, event → observable**

### ใช้ Signal เมื่อ

- **State ของ component** ที่ template ต้องแสดง — แทน `BehaviorSubject` ได้เกือบทั้งหมด
- **ค่าที่ derive จาก state อื่น** — `computed` ชนะ `combineLatest + map` ขาดลอยทั้งเรื่องอ่านง่ายและ performance
- **Input / query ของ component**
- **State ใน service ที่แชร์กันทั้งแอป** (store เล็ก ๆ)

```ts
@Component({
  template: `
    @for (u of visible(); track u.id) { <li>{{ u.name }}</li> }
    <p>เจอ {{ visible().length }} จาก {{ users().length }} คน</p>
  `
})
export class UserList {
  users = signal<User[]>([]);
  keyword = signal('');
  visible = computed(() =>
    this.users().filter(u => u.name.includes(this.keyword()))
  );
}
```

ไม่มี `async` pipe ซ้ำ ๆ ไม่มี subscription ให้ลืม และอ่าน `visible()` กี่รอบก็คำนวณครั้งเดียว

### ใช้ RxJS เมื่อ

- **ต้องจัดการเวลา** — `debounceTime`, `throttleTime`, `interval`, `timer`
- **ต้องยกเลิกงานเก่า** — `switchMap` คือ type-ahead search ที่ถูกต้อง ไม่มีอะไรใน signal แทนได้ตรง ๆ
- **ต้อง retry / error handling** — `retry({ delay })`, `catchError`
- **Stream ที่ไหลต่อเนื่อง** — WebSocket, SSE, mouse/scroll event
- **ประสาน async หลายเส้น** — `forkJoin`, `concatMap`, `race`

```ts
// เคสนี้ signal ทำไม่ได้สวยเท่า
search = new FormControl('');
results = toSignal(
  this.search.valueChanges.pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap(q => this.api.search(q)),   // ยกเลิก request เก่าให้อัตโนมัติ
  ),
  { initialValue: [] }
);
```

### เชื่อมสองโลกที่ขอบ

แนวทางที่ใช้กันจริงคือ **RxJS ทำ pipeline, signal เก็บผลลัพธ์, template อ่าน signal**

```ts
import { toSignal, toObservable } from '@angular/core/rxjs-interop';

user = toSignal(this.http.get<User>('/api/me'));          // Observable → Signal
query$ = toObservable(this.keyword);                       // Signal → Observable
```

`toSignal` จัดการ unsubscribe ตอน destroy ให้เอง — ถ้าไม่ใส่ `initialValue` ค่าแรกจะเป็น `undefined` (type ก็จะติด `| undefined` มาด้วย) ส่วน HTTP ล้วน ๆ ที่ไม่ต้องการ operator อะไรเลย ลองดู `httpResource()` ซึ่งให้ `value` / `isLoading` / `error` เป็น signal มาในชุดเดียว

---

## ข้อควรระวัง

**อย่าใช้ `effect` sync state** — นี่คือความผิดพลาดที่เจอบ่อยที่สุด

```ts
// ❌ ผิด
effect(() => this.total.set(this.price() * this.qty()));
// ✅ ถูก
total = computed(() => this.price() * this.qty());
```

`effect` มีไว้สำหรับ side effect ที่ออกนอกระบบ reactive เท่านั้น เช่น logging, localStorage, จัดการ DOM นอก Angular, ส่ง analytics ถ้าจะ "เขียน state ตาม state อื่นแต่ต้องแก้มือได้" ให้ใช้ `linkedSignal`

**การแก้ object/array ต้องสร้างใหม่** — signal เทียบด้วย `Object.is`

```ts
items.update(arr => { arr.push(x); return arr; });  // ❌ ไม่ trigger
items.update(arr => [...arr, x]);                   // ✅
```

**`untracked()`** ใช้เมื่อต้องอ่าน signal ใน `computed`/`effect` โดยไม่อยาก subscribe มัน

**ไม่ต้องรีบ migrate ทั้งหมด** — ทั้งสองอย่างอยู่ร่วมกันได้ดี ทีมส่วนใหญ่ย้าย component state ไป signal ก่อน แล้วปล่อย HTTP/event stream ไว้กับ RxJS ตามเดิม ซึ่งเป็นจุดที่ RxJS ยังแข็งแรงกว่ามาก

### B

ต่างกันที่ตัวตั้งต้นเลยครับ signal คือ "ค่า" ที่รู้ตัวว่าใครอ่านมันอยู่ ส่วน Observable คือ "สายน้ำของเหตุการณ์" ที่ไหลมาตามเวลา

## signal คืออะไร

```ts
import { signal, computed, effect } from '@angular/core';

const count = signal(0);
const double = computed(() => count() * 2);

count();            // อ่านค่าปัจจุบัน ได้ 0 ทันที
count.set(5);
count.update(n => n + 1);
double();           // 12 คำนวณตอนอ่าน แล้ว cache ไว้

effect(() => console.log('count =', count()));  // ยิงทุกครั้งที่ count เปลี่ยน
```

จุดสำคัญคือตอนเรียก `count()` ใน template หรือใน `computed` Angular จะจดไว้ว่าใครพึ่งค่านี้อยู่ พอค่าเปลี่ยน ก็ไปอัปเดตเฉพาะจุดนั้น ไม่ต้องไล่เช็กทั้งต้นไม้ นี่คือเหตุผลที่ signal มาคู่กับ zoneless

## ต่างกันตรงไหน

| | signal | Observable |
|---|---|---|
| ค่าปัจจุบัน | มีเสมอ อ่านได้ทันที | ไม่มี ต้องรอค่าไหลมา |
| จำนวนค่า | ค่าเดียว ณ เวลาหนึ่ง | ไหลมาได้เรื่อย ๆ |
| sync / async | sync ล้วน | รองรับ async |
| การใช้งาน | อ่านตรง ๆ `count()` | ต้อง subscribe |
| memory leak | แทบไม่ต้องกังวล | ต้องเคลียร์เอง |
| จัดการเวลา | ไม่มี | debounce, throttle, retry, switchMap |
| ยกเลิกงานกลางคัน | ไม่ได้ | ได้ |
| error / complete | ไม่มีแนวคิดนี้ | มี |

## เรื่องที่คนมักไม่รู้: signal ไม่ยิงค่ากลาง ๆ

```ts
const firstName = signal('สมชาย');
const lastName  = signal('ใจดี');
const fullName  = computed(() => `${firstName()} ${lastName()}`);
```

ถ้าเปลี่ยนทั้งสองตัวในจังหวะเดียวกัน `fullName` จะคำนวณรอบเดียว ได้ค่าที่ถูกต้องเลย เทียบกับ `combineLatest` ที่จะยิงค่าระหว่างทางออกมาด้วย เช่น "สมหญิง ใจดี" ก่อนจะกลายเป็นค่าจริง ปัญหาแบบนี้ใน RxJS ต้องแก้ด้วย operator เพิ่ม แต่ signal ตัดไปได้ตั้งแต่ต้น

อีกข้อที่พลาดกันบ่อย อย่าใช้ `effect` ไปเซ็ต signal ตัวอื่น ถ้าอยากได้ค่าที่คำนวณจากค่าอื่นให้ใช้ `computed` หรือ `linkedSignal` เมื่อต้องการให้แก้ทับได้ `effect` เอาไว้ทำงานที่ออกไปนอกระบบ reactive เช่น เขียน localStorage หรือสั่ง chart วาดใหม่

## เลือกยังไง

ใช้ signal เมื่อโจทย์คือ "ค่า"
- state ใน component: loading flag, โหมดฟอร์ม, แถวที่เลือกอยู่, ค่า filter
- ค่าที่คำนวณจาก state อื่น ใช้ `computed`
- `@Input()` เปลี่ยนมาใช้ `input()` ได้เลย ได้ `computed` ต่อฟรี
- อะไรก็ตามที่ template ต้องอ่าน

ใช้ RxJS เมื่อโจทย์คือ "เหตุการณ์ตามเวลา"
- search box ที่ต้อง debounce แล้วยกเลิก request เก่า
- websocket, SSE, polling, `interval`
- event stream: scroll, drag, keyboard
- HTTP ที่ต้อง retry หรือต่อคิวหลายสเต็ปตามลำดับ
- `router.events`, `form.valueChanges` ที่ Angular ยังคืนเป็น Observable

สรุปสั้น ๆ ถ้าเวลาเป็นส่วนหนึ่งของโจทย์ ใช้ RxJS ถ้าแค่อยากรู้ว่าตอนนี้ค่าเป็นอะไร ใช้ signal

## ใช้ร่วมกันคือคำตอบจริง ๆ

ของจริงไม่ต้องเลือกข้าง `@angular/core/rxjs-interop` ให้สะพานไว้แล้ว

```ts
import { toSignal, toObservable } from '@angular/core/rxjs-interop';

query = signal('');

results = toSignal(
  toObservable(this.query).pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap(q => this.api.search(q)),
  ),
  { initialValue: [] as Item[] },
);
```

รูปแบบนี้ใช้ได้เกือบทุกหน้า: signal เป็นหน้าบ้านให้ template อ่าน RxJS อยู่ตรงกลางรับหน้าที่คุมจังหวะเวลา แล้วแปลงกลับเป็น signal ด้วย `toSignal` ซึ่ง unsubscribe ให้ตอน component ตายอยู่แล้ว

ย้ำอีกที signal ไม่ได้มาแทน RxJS แต่มาแทน `BehaviorSubject` ที่เราใช้เก็บ state ใน component กับ zone.js มากกว่า

ถ้าบอกมาว่าโปรเจกต์ใช้ Angular เวอร์ชันไหนและตอนนี้เขียน state แบบไหนอยู่ เดี๋ยวช่วยดูให้ว่าตรงไหนย้ายมา signal แล้วคุ้มครับ

เลือก: 

---

## 04-concept-rebase

> git rebase กับ git merge ต่างกันยังไง ทีมเราควรใช้แบบไหน

### A

ต่างกันที่วิธีรวมประวัติครับ merge เก็บประวัติจริงไว้ทั้งหมดแล้วสร้าง merge commit ขึ้นมาหนึ่งอัน ส่วน rebase ยกชุด commit ของเราไปต่อท้าย branch ปลายทาง ได้ประวัติเป็นเส้นตรง แต่ commit ถูกสร้างใหม่หมด hash เปลี่ยน

## เทียบกันตรง ๆ

| | merge | rebase |
|---|---|---|
| ประวัติ | เห็นว่า branch แตกตอนไหน รวมตอนไหน | เส้นตรง อ่านง่าย เหมือนทำต่อกันมา |
| commit hash | ของเดิมคงอยู่ | สร้างใหม่ทั้งชุด |
| แก้ conflict | ครั้งเดียวจบ | อาจต้องแก้ทีละ commit |
| ปลอดภัยกับ branch ที่แชร์กัน | ปลอดภัย | อันตราย ต้อง force push |

## ที่ทีมส่วนใหญ่ใช้กันแล้วเวิร์ก

แบ่งตามว่า branch นั้นเป็นของใคร

- **branch ตัวเอง ยังไม่มีใครใช้ร่วม**: ใช้ rebase เอา main ล่าสุดมาไว้ใต้งานเรา ก่อนเปิด PR `git pull --rebase origin main` ทำให้ PR อ่านง่าย reviewer เห็นแต่ diff ที่เราเขียนจริง ๆ ไม่มี merge commit มากวน
- **เอางานเข้า main**: ใช้ merge ผ่าน PR ไม่ต้อง rebase เข้าไปตรง ๆ จะเลือก squash merge ให้ได้ 1 feature = 1 commit ก็ดี หรือจะ merge commit ปกติเพื่อเก็บรายละเอียดไว้ก็ได้ แล้วแต่ทีมชอบ

กฎเหล็กข้อเดียวที่ห้ามพลาด: **อย่า rebase branch ที่คนอื่น pull ไปแล้ว** เพราะ hash เปลี่ยนหมด พอเพื่อน pull ครั้งต่อไปจะเจอ conflict มั่วไปหมด ถ้าจำเป็นจริง ๆ ต้องบอกกันก่อน แล้วใช้ `git push --force-with-lease` ไม่ใช่ `--force` เฉย ๆ

## ตั้งค่าไว้กันพลาด

ให้ทุกคนรันครั้งเดียว

```bash
git config --global pull.rebase true
```

จะได้ไม่เผลอสร้าง merge commit งง ๆ ตอน `git pull` ซึ่งเป็นสาเหตุที่ประวัติ repo รกที่สุด

ส่วนเรื่อง squash หรือไม่ squash ตอน merge เข้า main อันนี้ต้องตกลงกันในทีมแล้วล็อกไว้ที่ setting ของ repo เลย จะได้ไม่ขึ้นกับว่าใครกดปุ่มไหน

ถ้าบอกได้ว่าทีมกี่คน แล้วตอนนี้ทำงานกันบน branch แบบไหน เดี๋ยวแนะนำ branching model ที่เหมาะกว่านี้ให้ครับ

### B

## สรุปความต่างแบบสั้น

**merge** = เอาประวัติสองสายมาบรรจบกัน แล้วสร้าง merge commit ที่มี parent สองตัว ประวัติเดิมไม่ถูกแตะต้องเลย

**rebase** = ยกคอมมิตของเราไปวางต่อท้าย base ใหม่ โดย "เขียนใหม่" ทุกคอมมิต (SHA เปลี่ยนหมด แม้เนื้อหาเหมือนเดิม) ได้ประวัติเป็นเส้นตรง

ภาพประกอบ — สมมติแตก `feature` จาก `main` แล้ว `main` เดินหน้าไป:

```
# ก่อน
A---B---C  main
     \
      D---E  feature

# git merge main (ยืนอยู่บน feature)
A---B---C-------M  main/feature
     \         /
      D-------E

# git rebase main
A---B---C---D'---E'  feature   (D' E' เป็นคอมมิตใหม่คนละตัวกับ D E)
```

| | merge | rebase |
|---|---|---|
| ประวัติ | จริงตามที่เกิด แตกกิ่งเยอะ | เส้นตรง อ่านง่าย |
| SHA เดิม | คงอยู่ | เปลี่ยนใหม่หมด |
| conflict | แก้ครั้งเดียวตอน merge | อาจต้องแก้ทีละคอมมิต |
| ปลอดภัยกับ branch ที่แชร์ | ปลอดภัย | **อันตราย** ต้อง force push |
| `git bisect` / `git blame` | รกกว่านิดหน่อย | สะอาดกว่า |
| ย้อนกลับ | `git revert -m 1` | ใช้ `git reflog` |

## กฎเหล็กข้อเดียวที่ต้องจำ

**ห้าม rebase branch ที่คนอื่นดึงไปใช้แล้ว** — เพราะ SHA เปลี่ยน คนอื่น pull มาจะเจอประวัติซ้อนกันพังทั้งทีม  
rebase ได้เฉพาะคอมมิตที่ยังอยู่ใน local หรือ feature branch ที่มีเราคนเดียวทำ

## ที่ผมแนะนำสำหรับทีมส่วนใหญ่: ใช้ทั้งคู่ คนละหน้าที่

**1. ซิงก์งานตัวเอง → rebase**
```powershell
git config --global pull.rebase true   # ตั้งครั้งเดียว กัน merge commit ขยะจาก pull
git fetch origin
git rebase origin/main                 # อัปเดต feature branch ให้ทันก่อนเปิด PR
```
ช่วยกำจัด merge commit ประเภท "Merge branch 'main' into 'main'" ที่ไม่มีความหมายอะไรเลย

**2. เอางานเข้า main → merge ผ่าน PR** (`--no-ff` หรือ squash merge)  
จะได้เห็นชัดว่า feature นี้เข้ามาตอนไหน ประกอบด้วยอะไรบ้าง และ revert ทั้งก้อนได้ง่าย

**3. ก่อนเปิด PR ให้จัดคอมมิตตัวเองให้สวย**
```powershell
git rebase -i origin/main   # ยุบ "fix typo", "wip", "แก้อีกรอบ" ให้เหลือคอมมิตที่สื่อความหมาย
```

**เลือก merge strategy บน PR ยังไง:**
- **Squash merge** — เหมาะที่สุดถ้าทีมยังไม่ชินกับการเขียน commit message ดีๆ ได้ main ที่สะอาด 1 PR = 1 คอมมิต revert ง่ายมาก (ผมแนะนำอันนี้เป็น default ถ้าไม่แน่ใจ)
- **Merge commit (`--no-ff`)** — เหมาะเมื่อทีมเขียนคอมมิตเป็นระเบียบอยู่แล้ว และอยากเก็บรายละเอียดระหว่างทาง
- **Rebase merge** — ได้เส้นตรงสวยสุด แต่เสียความสามารถในการ revert ทั้ง feature ด้วยคำสั่งเดียว

## ข้อควรรู้เพิ่มเติม

- ถ้า rebase แล้วต้อง push ใช้ `git push --force-with-lease` **ห้ามใช้** `--force` เฉยๆ เพราะ `--force-with-lease` จะไม่ทับงานคนอื่นที่เพิ่ง push เข้ามา
- เปิด `git config --global rerere.enabled true` — Git จะจำวิธีแก้ conflict ที่เคยแก้แล้ว ช่วยได้มากเวลา rebase branch ยาวๆ
- ล็อก branch `main` / `develop` ไว้ใน GitHub/GitLab (ห้าม force push) จะกันอุบัติเหตุได้เกือบหมด
- rebase พลาดไม่ใช่จุดจบ — `git reflog` แล้ว `git reset --hard HEAD@{n}` กู้คืนได้เสมอ

**ถ้าทีมยังใหม่กับ Git** ให้เริ่มจาก merge อย่างเดียวก่อนก็ได้ครับ ประวัติรกหน่อยแต่ไม่มีใครทำงานหาย พอทุกคนเข้าใจ reflog กับ force-with-lease แล้วค่อยเพิ่ม rebase เข้ามา — ต้นทุนความผิดพลาดของ rebase สูงกว่าชัดเจน

เลือก: 

---

## 05-review-nested-subscribe

> ช่วยรีวิวโค้ดนี้หน่อย
> 
> ```ts
> ngOnInit() {
>   this.http.get('/api/employees').subscribe(res => {
>     this.employees = res;
>     this.http.get('/api/departments').subscribe(d => {
>       this.departments = d;
>     });
>   });
> }
> ```

### A

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

### B

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

เลือก: 

---

## 06-review-sql

> query นี้ช้ามาก ตาราง Employee มีประมาณ 2 ล้าน row ช่วยดูหน่อยว่าน่าจะติดตรงไหน
> 
> ```sql
> SELECT * FROM Employee e
> WHERE YEAR(e.StartDate) = 2026
>   AND e.CompanyId = @CompanyId
> ORDER BY e.FirstName
> ```

### A

ตัวการหลักคือ `YEAR(e.StartDate)` ครับ พอเอาคอลัมน์ไปห่อด้วยฟังก์ชัน แบบนี้ทำให้ query ใช้ index ไม่ได้ SQL Server ต้องคำนวณ `YEAR()` ทีละแถวให้ครบ 2 ล้านแถวก่อน ถึงจะรู้ว่าแถวไหนผ่าน สุดท้ายเลยลงเอยที่ clustered index scan ทุกรอบ

## จุดที่ช้า เรียงตามน้ำหนัก

**1. เงื่อนไขปี ไม่ SARGable**

เขียนเป็นช่วงวันแทน optimizer จะ seek ได้ทันที

```sql
AND e.StartDate >= '2026-01-01'
AND e.StartDate <  '2027-01-01'
```

ใช้ `<` วันที่ 1 ม.ค. ปีถัดไป ไม่ใช่ `<= '2026-12-31'` เพราะถ้าคอลัมน์เป็น `datetime` แถวที่เวลา 2026-12-31 08:30 จะหลุดหายไป

**2. น่าจะไม่มี index ที่ครอบเงื่อนไขนี้**

ต่อให้แก้ข้อ 1 แล้ว ถ้าไม่มี index รองรับก็ยัง scan อยู่ดี ตัวที่ควรมีคือ

```sql
CREATE NONCLUSTERED INDEX IX_Employee_CompanyId_StartDate
ON dbo.Employee (CompanyId, StartDate)
INCLUDE (FirstName, LastName, /* คอลัมน์ที่ใช้จริง */);
```

เอา `CompanyId` ไว้หน้าเพราะเป็นเงื่อนไขแบบ equality แล้วค่อยตามด้วย `StartDate` ที่เป็น range ถ้าสลับลำดับ index จะช่วยได้ไม่เต็มที่

**3. `SELECT *` กินแรงสองต่อ**

ต่อให้สร้าง nonclustered index แล้ว การดึงทุกคอลัมน์บังคับให้ต้องวิ่ง key lookup กลับไปที่ clustered index ทีละแถว พอจำนวนแถวเยอะพอ optimizer จะมองว่า scan ทั้งตารางถูกกว่า แล้วทิ้ง index ที่เพิ่งสร้างไปเฉย ๆ

อีกต่อคือ sort ข้อถัดไปจะต้องแบกข้อมูลทุกคอลัมน์ไปด้วย เสี่ยง spill ลง tempdb

ให้ระบุเฉพาะคอลัมน์ที่ใช้จริง แล้วเอาคอลัมน์พวกนั้นไปใส่ `INCLUDE` ให้ index ครอบคลุม จะได้ไม่ต้อง lookup เลย

**4. `ORDER BY FirstName` กับการไม่มี paging**

ถ้าผลลัพธ์หลังกรองเหลือหลักพัน sort ก็ไม่หนักเท่าไหร่ แต่ถ้าเหลือหลักแสนแล้วส่งกลับหมด ตรงนี้จะกลายเป็นคอขวดแทน

## query หลังแก้

```sql
SELECT e.EmployeeId, e.FirstName, e.LastName, e.StartDate   -- เอาเท่าที่ใช้
FROM dbo.Employee e
WHERE e.CompanyId = @CompanyId
  AND e.StartDate >= @YearStart      -- DATE/DATETIME ให้ตรง type กับคอลัมน์
  AND e.StartDate <  @NextYearStart
ORDER BY e.FirstName
OFFSET @Skip ROWS FETCH NEXT @Take ROWS ONLY;
```

## สองเรื่องที่อยากให้เช็กเพิ่ม

**type ของ `@CompanyId`** ถ้า declare ไม่ตรงกับคอลัมน์ เช่นคอลัมน์เป็น `int` แต่ส่ง `nvarchar` มา หรือคอลัมน์เป็น `varchar` แล้วส่ง `nvarchar` (EF Core ชอบทำแบบนี้) จะเกิด implicit conversion แล้ว index seek หายไปทันที ดูในแผนจะเห็น warning `CONVERT_IMPLICIT`

**ถ้ามี paging และต้องการเลี่ยง sort** ลองอีกแบบคือ index `(CompanyId, FirstName) INCLUDE (StartDate, ...)` แบบนี้อ่านตามลำดับ `FirstName` ได้เลย ไม่ต้อง sort แล้วกรองปีเป็น residual predicate เหมาะกับกรณีดึงแค่ 50 แถวแรก แต่ถ้าดึงทั้งชุด ตัวแรกจะดีกว่า

ลองรันพร้อม actual execution plan แล้วส่งมาดูได้ครับ จะได้ยืนยันว่าติดที่ scan จริงหรือมีอย่างอื่นแทรกอยู่

### B

ดูจาก syntax แล้วน่าจะเป็น SQL Server ครับ — มีจุดที่น่าสงสัย 3 จุด เรียงตามผลกระทบ

## 1. `YEAR(e.StartDate) = 2026` ทำให้ใช้ index ไม่ได้ (ตัวหลัก)

พอเอาฟังก์ชันไปครอบคอลัมน์ มันจะกลายเป็น non-sargable คือ SQL Server ต้องคำนวณ `YEAR()` ทีละแถวครบทั้ง 2 ล้านแถวก่อน ถึงจะรู้ว่าแถวไหนผ่าน — ใช้ index seek ไม่ได้เลย ต้อง scan ทั้งตาราง

เขียนใหม่เป็น range แทน:

```sql
WHERE e.StartDate >= '2026-01-01'
  AND e.StartDate <  '2027-01-01'
```

ใช้แบบ half-open (`>=` กับ `<`) ไม่ใช้ `BETWEEN '2026-01-01' AND '2026-12-31'` เพราะถ้า `StartDate` เป็น `datetime`/`datetime2` แถวที่เป็นวันที่ 31 ธ.ค. เวลา 10:00 จะหลุดไป

## 2. ไม่มี composite index ที่ตรงกับ predicate

```sql
CREATE INDEX IX_Employee_CompanyId_StartDate
ON Employee (CompanyId, StartDate)
INCLUDE (FirstName, LastName, /* คอลัมน์อื่นที่ใช้จริง */);
```

เอา `CompanyId` ขึ้นก่อนเพราะเป็นเงื่อนไข equality ส่วน `StartDate` เป็น range ต้องตามหลัง (ถ้าสลับกัน จะ seek ได้แค่ช่วง StartDate แล้วต้องกรอง CompanyId ทีหลัง)

## 3. `SELECT *` ทำให้ index ที่สร้างมาอาจไม่ถูกใช้อยู่ดี

อันนี้คนมักมองข้าม — พอดึงทุกคอลัมน์ ต่อให้มี index ข้างบน optimizer ก็ยังต้องทำ key lookup กลับไปที่ clustered index ทีละแถวเพื่อเอาคอลัมน์ที่เหลือ ถ้าผลลัพธ์เกิน tipping point (ประมาณ 1-2% ของตาราง) มันจะตัดสินใจ scan ทั้งตารางแทนเลย คือ index ที่สร้างไว้เสียเปล่า

ให้ระบุเฉพาะคอลัมน์ที่ใช้จริง แล้วเอาคอลัมน์เหล่านั้นใส่ `INCLUDE` เพื่อให้เป็น covering index

## รวมเป็น

```sql
SELECT e.EmployeeId, e.FirstName, e.LastName, e.StartDate  -- เท่าที่ใช้จริง
FROM Employee e
WHERE e.CompanyId = @CompanyId
  AND e.StartDate >= '2026-01-01'
  AND e.StartDate <  '2027-01-01'
ORDER BY e.FirstName;
```

## จุดที่ควรเช็คเพิ่ม

**ชนิดข้อมูลของ `@CompanyId`** — ถ้าคอลัมน์เป็น `varchar` แต่ parameter ประกาศเป็น `nvarchar` (ตัวนี้เจอบ่อยมากเวลาเรียกผ่าน Entity Framework / Dapper) จะเกิด implicit conversion ฝั่งคอลัมน์ แล้วก็ non-sargable เหมือนข้อ 1 เลย ลองดูใน execution plan ว่ามี `CONVERT_IMPLICIT` ตรง predicate ไหม

**`ORDER BY e.FirstName`** — ตัวนี้ยังไงก็ต้องมี Sort operator เพราะ index เรียงตาม `StartDate` ไม่ได้เรียงตามชื่อ แต่ถ้าหลังกรองแล้วเหลือหลักพันแถวก็ไม่ใช่ปัญหา จะหนักก็ต่อเมื่อบริษัทนั้นมีพนักงานเข้าปี 2026 เยอะมากจริง ๆ

**มี pagination หรือยัง** — ถ้าหน้าจอแสดงแค่ 50 แถวแรก การดึงมาทั้งหมดแล้วค่อยตัดฝั่ง application เป็นต้นทุนที่เสียเปล่า ใช้ `OFFSET ... FETCH NEXT` แทน

ถ้าแก้ตามนี้แล้วยังช้า ขอ actual execution plan มาดูได้ครับ จะได้เห็นว่าติดที่ scan, sort หรือ key lookup กันแน่ และจำนวนแถวที่ประมาณไว้ (estimated) ต่างจากของจริง (actual) มากแค่ไหน — ถ้าต่างกันมากอาจเป็นเรื่อง statistics เก่าหรือ parameter sniffing ซึ่งแก้คนละแบบ

เลือก: 

---

## 07-pr-description

> ช่วยเขียน PR description ให้หน่อย งานคือเพิ่ม validation ตอนพนักงานขอลาเกินโควตา ฝั่ง API เช็กโควตาก่อนบันทึก ฝั่งเว็บแสดง error ใต้ช่องวันลา และเพิ่ม unit test 6 เคส

### A

นี่คือ PR description ที่เขียนไว้ให้ครับ — ส่วนที่เป็น `[...]` คือจุดที่ต้องเติมข้อมูลจริงของโปรเจกต์

---

## เพิ่ม validation กรณีขอลาเกินโควตา

### สรุป
เดิมระบบยอมให้พนักงานส่งคำขอลาได้แม้วันลาที่ขอจะเกินโควตาคงเหลือ ทำให้ต้องไปตรวจพบทีหลังตอนอนุมัติ PR นี้เพิ่มการตรวจสอบโควตาตั้งแต่ตอนยื่นคำขอ ทั้งฝั่ง API และแสดงผลข้อผิดพลาดบนหน้าเว็บ

### การเปลี่ยนแปลง

**API**
- เพิ่มการตรวจสอบโควตาคงเหลือใน `[LeaveRequestService.Create]` ก่อนบันทึกลงฐานข้อมูล
- ถ้าจำนวนวันที่ขอเกินโควตาคงเหลือ จะ return `[400 Bad Request]` พร้อม error code `[LEAVE_QUOTA_EXCEEDED]` และข้อมูลโควตาคงเหลือ เพื่อให้ฝั่ง client นำไปแสดงผลได้
- การตรวจสอบอยู่ใน service layer จึงครอบคลุมทุก entry point ที่เรียกสร้างคำขอลา

**Web**
- แสดงข้อความ error ใต้ช่องเลือกวันลา เมื่อ API ตอบกลับว่าเกินโควตา
- ปุ่มส่งคำขอยังคงกดได้ตามปกติ validation จะเกิดขึ้นหลังเรียก API (ไม่ได้ทำ client-side pre-check เพราะโควตาอาจเปลี่ยนจากคำขออื่นที่ถูกอนุมัติระหว่างนั้น)

**Tests**
เพิ่ม unit test 6 เคส:
1. ขอลาน้อยกว่าโควตาคงเหลือ → สร้างคำขอสำเร็จ
2. ขอลาเท่ากับโควตาคงเหลือพอดี → สร้างคำขอสำเร็จ
3. ขอลาเกินโควตาคงเหลือ → throw `[QuotaExceededException]`
4. โควตาคงเหลือเป็น 0 → throw `[QuotaExceededException]`
5. ลาครึ่งวัน → คำนวณเป็น 0.5 วันและเทียบกับโควตาถูกต้อง
6. `[ประเภทการลาที่ไม่จำกัดโควตา]` → ข้ามการตรวจสอบ

### วิธีทดสอบ
1. เข้าหน้ายื่นคำขอลาด้วยบัญชีที่มีโควตาคงเหลือ `[N]` วัน
2. เลือกช่วงวันลาที่มากกว่า `[N]` วัน แล้วกดส่ง
3. ควรเห็นข้อความ error ใต้ช่องเลือกวันลา และคำขอต้องไม่ถูกบันทึก
4. ลองเลือกช่วงวันที่ไม่เกินโควตา → ต้องส่งได้ตามปกติ

### หมายเหตุ
- ไม่มี breaking change ต่อ API contract เดิม เพิ่มเฉพาะ error case ใหม่
- ยังไม่ครอบคลุมกรณี `[แก้ไขคำขอที่ยื่นไปแล้ว]` จะแยกทำใน `[ticket ถัดไป]`

---

ปรับความยาวได้ตามต้องการครับ ถ้า PR template ของทีมมีหัวข้อบังคับ (เช่น ticket link, screenshot, checklist) บอกมาได้ เดี๋ยวจัดให้ตรงฟอร์แมต

### B

ร่างให้ตามนี้ครับ ส่วนที่ไม่ได้บอกมา เช่น status code ชื่อ endpoint และรายละเอียด test ทั้ง 6 เคส ผมเติมไว้ตามที่น่าจะเป็น แก้ให้ตรงของจริงได้เลย

---

**Title:** `feat: เพิ่ม validation ตรวจโควตาวันลาก่อนบันทึกใบลา`

```markdown
## สรุป

เพิ่มการตรวจสอบโควตาวันลาก่อนบันทึกใบลา เดิมระบบรับใบลาได้แม้จำนวนวันที่ขอจะเกินโควตาคงเหลือ
ทำให้ยอดคงเหลือติดลบ และ HR ต้องตามแก้ข้อมูลย้อนหลัง

## การเปลี่ยนแปลง

### API
- เพิ่มการเช็กโควตาคงเหลือใน `LeaveRequestService` ก่อนเขียนลง database
- ถ้าจำนวนวันที่ขอมากกว่าโควตาคงเหลือ จะไม่บันทึกรายการ และคืน `400 Bad Request`
  พร้อม error code `LEAVE_QUOTA_EXCEEDED` และจำนวนวันคงเหลือใน response body
- คำนวณโควตาคงเหลือจากโควตาทั้งปี หักใบลาที่อนุมัติแล้วและที่รออนุมัติ

### Web
- แสดงข้อความ error ใต้ช่องเลือกวันลา ระบุจำนวนวันที่ขอและจำนวนวันคงเหลือ
- map error code จาก API เป็นข้อความภาษาไทย
- ข้อความ error จะหายเมื่อผู้ใช้แก้ช่วงวันลาใหม่

### Test
เพิ่ม unit test 6 เคสที่ฝั่ง API

| # | เคส | ผลที่คาดหวัง |
|---|---|---|
| 1 | ขอน้อยกว่าโควตาคงเหลือ | บันทึกสำเร็จ |
| 2 | ขอเท่าโควตาคงเหลือพอดี | บันทึกสำเร็จ |
| 3 | ขอเกินโควตาคงเหลือ 1 วัน | คืน error ไม่บันทึก |
| 4 | โควตาคงเหลือเป็น 0 | คืน error ไม่บันทึก |
| 5 | มีใบลารออนุมัติอยู่แล้ว และรวมกับใบใหม่แล้วเกินโควตา | คืน error ไม่บันทึก |
| 6 | พนักงานยังไม่มีข้อมูลโควตาในปีนั้น | คืน error ไม่บันทึก |

## วิธีทดสอบ

1. ตั้งโควตาวันลาพักร้อนของพนักงานทดสอบเป็น 5 วัน
2. ยื่นใบลา 3 วัน ต้องบันทึกได้ปกติ
3. ยื่นใบลาอีก 4 วัน ต้องขึ้น error ใต้ช่องวันลา และไม่มีรายการใหม่ใน database
4. แก้เป็น 2 วัน error ต้องหาย และบันทึกได้

## หมายเหตุ

- ยังไม่ครอบคลุมกรณีลาคร่อมปีงบประมาณ แยกเป็นงานต่างหาก
- ไม่มีการแก้ schema ของ database
```

สองจุดที่อยากให้ตัดสินใจก่อน merge

- **เคสที่ 6** พนักงานไม่มีข้อมูลโควตา ผมให้เป็น error ไว้ ถ้าทีมตกลงว่าให้ fallback เป็นโควตาตั้งต้นแทน ต้องแก้ทั้งโค้ดและ test
- **ใบลาที่รออนุมัติ** ร่างนี้นับรวมเข้าไปในยอดที่ใช้ไปแล้ว ถ้าธุรกิจนับเฉพาะใบที่อนุมัติแล้ว เคสที่ 5 จะเปลี่ยนผลลัพธ์

ถ้าบอกชื่อ class หรือ endpoint จริงมา เดี๋ยวปรับให้ตรงกับ repo ครับ

เลือก: 

---

## 08-commit-message

> ช่วยเขียน commit message ภาษาไทยให้หน่อย แก้บั๊กหน้ารายงานเงินเดือนที่คำนวณ OT ผิดเวลาพนักงานทำงานข้ามเที่ยงคืน

### A

เขียนให้สองแบบ เลือกตามที่ repo ใช้อยู่ครับ

**แบบ conventional commit**

```
fix(payroll): แก้คำนวณ OT ผิดเมื่อพนักงานทำงานข้ามเที่ยงคืน

หน้ารายงานเงินเดือนคิดชั่วโมง OT จากเวลาออกลบเวลาเข้าโดยไม่ดูวันที่
กะที่เข้างานก่อนเที่ยงคืนแล้วออกหลังเที่ยงคืนจึงได้ผลต่างติดลบ
และถูกปัดเป็น 0

เปลี่ยนไปคำนวณจาก timestamp เต็ม ถ้าเวลาออกน้อยกว่าเวลาเข้า
ให้นับเป็นวันถัดไปก่อนหาส่วนต่าง
```

**แบบไม่มี prefix**

```
แก้บั๊กหน้ารายงานเงินเดือนคำนวณ OT ผิดกรณีทำงานข้ามเที่ยงคืน

เดิมคิดชั่วโมงจากเวลาออกลบเวลาเข้าโดยไม่ดูวันที่ ทำให้กะข้ามคืนได้ค่าติดลบ
เปลี่ยนไปคิดจากวันที่และเวลาพร้อมกัน
```

ย่อหน้าที่สองผมเดาสาเหตุจากอาการที่เล่ามานะครับ ถ้า root cause จริงเป็นอย่างอื่น เช่น timezone หรือการ group record ตามวัน ก็แก้ตรงนั้นให้ตรงกับของจริง ส่งโค้ดส่วนที่แก้มาให้ดูได้ เดี๋ยวปรับ body ให้ตรงครับ

### B

เนื่องจากยังไม่ได้เห็นโค้ดที่แก้ ผมเดารายละเอียดสาเหตุ/วิธีแก้ไว้ตามรูปแบบบั๊กที่พบบ่อย — ปรับส่วนเนื้อหาให้ตรงกับการแก้จริงได้เลยครับ

```
fix: แก้การคำนวณ OT ผิดพลาดในหน้ารายงานเงินเดือน กรณีทำงานข้ามเที่ยงคืน

เดิมคำนวณชั่วโมง OT จากผลต่างของเวลาเข้า-ออกภายในวันเดียวกัน
ทำให้พนักงานที่ทำงานคาบเกี่ยวข้ามเที่ยงคืน (เช่น 22:00-02:00)
ได้ชั่วโมง OT ติดลบหรือคำนวณขาด ส่งผลให้ยอดเงินในรายงานไม่ถูกต้อง

แก้ไขโดยตรวจสอบกรณีเวลาออกงานน้อยกว่าเวลาเข้างาน
แล้วบวกเพิ่ม 1 วันให้เวลาออกงานก่อนนำไปคำนวณผลต่าง
```

แบบสั้นบรรทัดเดียว ถ้าไม่อยากใส่คำอธิบาย:

```
fix: แก้การคำนวณ OT ผิดเมื่อพนักงานทำงานข้ามเที่ยงคืนในหน้ารายงานเงินเดือน
```

ถ้ามีเลขที่ issue หรือ ticket ก็ต่อท้าย body ได้ เช่น `Refs: #1234`

เลือก: 

---

## 09-slack-release

> เขียนข้อความอัปเดตลง Slack ให้ทีมหน่อย ว่า deploy เวอร์ชัน 3.2 ขึ้น production แล้ว มีฟีเจอร์ใหม่คือ export รายงานเป็น Excel และแก้บั๊ก login ค้างบน Safari

### A

ร่างให้แล้วครับ

```
🚀 Deploy เวอร์ชัน 3.2 ขึ้น production เรียบร้อยแล้ว

ของใหม่รอบนี้
• export รายงานเป็นไฟล์ Excel ได้แล้ว
• แก้บั๊ก login ค้างบน Safari

รบกวนช่วยลองใช้งานดู ถ้าเจออะไรผิดปกติทักมาได้เลย 🙏
```

ถ้าอยากได้สั้นกว่านี้แบบบรรทัดเดียว ใช้แบบนี้ก็ได้

```
Deploy v3.2 ขึ้น production แล้วนะครับ 🚀 รอบนี้มี export รายงานเป็น Excel + แก้บั๊ก login ค้างบน Safari เจออะไรแปลก ๆ แจ้งได้เลย
```

อยากให้ใส่ลิงก์ release note หรือ changelog เพิ่มไหมครับ

### B

ได้เลยครับ นี่คือข้อความสำหรับโพสต์ลง Slack

---

🚀 **Deploy v3.2 ขึ้น Production เรียบร้อยแล้ว**

สวัสดีทุกคน เราได้ deploy เวอร์ชัน 3.2 ขึ้น production เรียบร้อยแล้วครับ

**✨ ฟีเจอร์ใหม่**
• Export รายงานเป็นไฟล์ Excel ได้แล้ว

**🐛 Bug Fix**
• แก้ปัญหา login ค้างบน Safari

รบกวนทุกคนช่วยลองใช้งานดู ถ้าเจออะไรผิดปกติแจ้งในแชนแนลนี้ได้เลยครับ 🙏

---

ปรับเพิ่มได้ตามสะดวกนะครับ — ถ้าอยากให้ละเอียดขึ้น อาจเติมส่วนเหล่านี้:

- **เวลา deploy** และ downtime (ถ้ามี)
- **ลิงก์ release note / changelog** หรือหมายเลข ticket (เช่น JIRA)
- **ชื่อคนที่ติดต่อได้** หากเจอปัญหาเร่งด่วน
- **วิธีใช้ฟีเจอร์ export** สั้น ๆ ถ้าตำแหน่งปุ่มไม่ชัดเจน

บอกมาได้ว่าอยากได้โทนทางการกว่านี้ หรือเป็นภาษาอังกฤษ เดี๋ยวปรับให้ครับ

เลือก: 

---

## 10-incident-customer

> ช่วยร่างข้อความแจ้งลูกค้าหน่อย เมื่อเช้าระบบล่มไป 40 นาทีเพราะ disk ของ database เต็ม ตอนนี้กลับมาใช้งานได้แล้ว และเราตั้ง alert เพิ่มแล้ว

### A

ร่างให้สองเวอร์ชันครับ ตัวหลักเป็นอีเมล/ประกาศทางการ กับเวอร์ชันสั้นไว้โพสต์ในกลุ่มไลน์หรือหน้าสถานะระบบ

## เวอร์ชันอีเมล

**เรื่อง: แจ้งเหตุขัดข้องของระบบ [ชื่อระบบ] วันที่ 1 ตุลาคม 2569 และการแก้ไข**

เรียน ลูกค้าผู้ใช้บริการทุกท่าน

เมื่อเช้าวันนี้ เวลาประมาณ [HH:MM] ถึง [HH:MM] ระบบ [ชื่อระบบ] ไม่สามารถใช้งานได้เป็นเวลาประมาณ 40 นาที ทางเราต้องขออภัยในความไม่สะดวกที่เกิดขึ้นมา ณ ที่นี้

**สาเหตุ**
พื้นที่จัดเก็บข้อมูลของเซิร์ฟเวอร์ฐานข้อมูลเต็ม ทำให้ระบบไม่สามารถบันทึกและอ่านข้อมูลได้ตามปกติ

**สถานะปัจจุบัน**
ทีมงานได้เพิ่มพื้นที่จัดเก็บข้อมูลและตรวจสอบความถูกต้องของข้อมูลเรียบร้อยแล้ว ขณะนี้ระบบกลับมาให้บริการได้ตามปกติ [ยืนยันก่อนส่ง: ข้อมูลที่บันทึกในช่วงดังกล่าวครบถ้วนหรือไม่ ถ้าครบให้ระบุชัดว่าไม่มีข้อมูลสูญหาย ถ้ามีรายการที่ต้องส่งซ้ำ ให้บอกลูกค้าตรงนี้ว่าต้องทำอะไร]

**การป้องกันไม่ให้เกิดซ้ำ**
ทีมงานได้ตั้งระบบแจ้งเตือนพื้นที่จัดเก็บข้อมูลเพิ่มเติม เพื่อให้ทราบและเข้าแก้ไขได้ตั้งแต่ก่อนที่พื้นที่จะเต็ม รวมถึงทบทวนแนวทางการจัดการพื้นที่จัดเก็บข้อมูลในระยะยาวด้วย

หากมีข้อสงสัยหรือพบความผิดปกติในการใช้งาน ติดต่อทีมงานได้ที่ [ช่องทางติดต่อ] ทางเราพร้อมดูแลอย่างเต็มที่

ขอแสดงความนับถือ
[ชื่อ / ทีมงาน / บริษัท]

## เวอร์ชันสั้น

> แจ้งเหตุขัดข้องระบบ [ชื่อระบบ]
>
> เช้าวันนี้ เวลา [HH:MM] ถึง [HH:MM] ระบบใช้งานไม่ได้ประมาณ 40 นาที สาเหตุมาจากพื้นที่จัดเก็บข้อมูลของฐานข้อมูลเต็ม
>
> ขณะนี้แก้ไขเรียบร้อยและระบบกลับมาใช้งานได้ตามปกติแล้ว ทีมงานได้ตั้งระบบแจ้งเตือนเพิ่มเพื่อป้องกันไม่ให้เกิดซ้ำ
>
> ขออภัยในความไม่สะดวกครับ หากพบปัญหาการใช้งาน แจ้งได้ที่ [ช่องทางติดต่อ]

สิ่งที่ต้องเติมก่อนส่ง มีเวลาเริ่ม-จบที่ชัดเจน ชื่อระบบ ช่องทางติดต่อ และข้อสรุปเรื่องข้อมูลสูญหาย

ข้อสังเกตสองเรื่อง อย่างแรกคือเวลาที่ระบุ ลูกค้ามักเอาไปเทียบกับ log ตัวเอง ถ้าใส่เวลาคลาดเคลื่อนจะกลายเป็นประเด็นต่อ ควรดึงจาก monitoring จริง อย่างที่สองคือเรื่องข้อมูล ถ้ายังไม่ได้ตรวจครบ อย่าเพิ่งเขียนว่าข้อมูลไม่สูญหาย เขียนว่า "อยู่ระหว่างตรวจสอบและจะแจ้งให้ทราบอีกครั้ง" ปลอดภัยกว่า

ถ้าลูกค้ามี SLA ที่ต้องแจ้งเป็นทางการ บอกได้ว่าอยากให้เพิ่มส่วนไหน เช่น timeline รายนาที หรือ root cause analysis เดี๋ยวเติมให้ครับ

### B

ร่างให้ 2 เวอร์ชันครับ — แบบเต็ม (อีเมล/ประกาศ) กับแบบสั้น (LINE/แจ้งในแอป) ส่วนที่อยู่ใน `[ ]` ต้องเติมก่อนส่ง

---

## เวอร์ชันเต็ม (อีเมล / ประกาศ)

**หัวข้อ:** แจ้งเหตุขัดข้องของระบบ [ชื่อระบบ] วันที่ 1 ตุลาคม 2569 และการแก้ไข

เรียน ลูกค้าผู้ใช้บริการทุกท่าน

เมื่อเช้าวันนี้ (1 ตุลาคม 2569) ระบบ [ชื่อระบบ] เกิดเหตุขัดข้องไม่สามารถใช้งานได้เป็นเวลาประมาณ 40 นาที ระหว่างเวลา [HH:MM] – [HH:MM] น.

**สาเหตุ**
พื้นที่จัดเก็บข้อมูล (disk) ของเซิร์ฟเวอร์ฐานข้อมูลเต็ม ส่งผลให้ระบบไม่สามารถอ่านและบันทึกข้อมูลได้ตามปกติ

**การแก้ไข**
ทีมงานตรวจพบสาเหตุและดำเนินการขยายพื้นที่จัดเก็บข้อมูลพร้อมกู้คืนระบบเรียบร้อยแล้ว ขณะนี้ระบบกลับมาให้บริการได้ตามปกติทุกส่วน

**การป้องกันไม่ให้เกิดซ้ำ**
เราได้ตั้งค่าการแจ้งเตือน (alert) สำหรับพื้นที่จัดเก็บข้อมูลเพิ่มเติม เพื่อให้ทีมงานทราบและเข้าแก้ไขได้ล่วงหน้าก่อนที่จะกระทบต่อการใช้งานของท่าน

[ตัวเลือก: ข้อมูลของท่านยังคงอยู่ครบถ้วน ไม่มีการสูญหายจากเหตุการณ์ครั้งนี้]

บริษัทฯ ต้องขออภัยเป็นอย่างสูงในความไม่สะดวกที่เกิดขึ้น หากท่านพบความผิดปกติในการใช้งาน กรุณาติดต่อ [ช่องทางติดต่อ] ทีมงานพร้อมดูแลทันที

ขอแสดงความนับถือ
[ชื่อทีม / บริษัท]

---

## เวอร์ชันสั้น (LINE / แจ้งในแอป)

> แจ้งเหตุขัดข้อง 1 ต.ค. 2569
>
> ระบบ [ชื่อระบบ] ไม่สามารถใช้งานได้ประมาณ 40 นาที ช่วงเวลา [HH:MM] – [HH:MM] น. สาเหตุจากพื้นที่จัดเก็บข้อมูลของฐานข้อมูลเต็ม
>
> ขณะนี้ทีมงานแก้ไขเรียบร้อยแล้ว ระบบกลับมาใช้งานได้ตามปกติ และได้ตั้งการแจ้งเตือนเพิ่มเติมเพื่อป้องกันไม่ให้เกิดซ้ำ
>
> ขออภัยในความไม่สะดวกครับ/ค่ะ หากพบปัญหาการใช้งาน ติดต่อ [ช่องทาง] ได้ทันที

---

**ข้อควรพิจารณาก่อนส่ง**

1. **เรื่องข้อมูลสูญหาย** — ผมใส่ไว้เป็นตัวเลือกเพราะไม่ทราบข้อเท็จจริง ถ้ายืนยันได้ว่าข้อมูลครบควรใส่ เพราะเป็นคำถามแรกที่ลูกค้าจะถาม แต่ถ้ายังไม่ได้ตรวจสอบ **อย่าเพิ่งใส่** — การยืนยันแล้วมาแก้ทีหลังเสียความน่าเชื่อถือมากกว่าการไม่พูดถึง
2. **ระดับรายละเอียดทางเทคนิค** — ถ้าลูกค้าเป็นองค์กร/ฝ่าย IT คงรายละเอียดเรื่อง disk ไว้ได้ แต่ถ้าเป็นผู้ใช้ทั่วไป อาจเปลี่ยนเป็น "ปัญหาด้านพื้นที่จัดเก็บข้อมูลของระบบ" ให้อ่านง่ายขึ้น
3. ถ้ามี SLA ที่ผูกกับสัญญา อาจต้องเพิ่มบรรทัดเรื่องการชดเชยหรือช่องทางขอเครดิต

เลือก: 

---

## 11-explain-to-pm

> PM ถามว่าทำไมแก้ปุ่มเดียวต้องใช้เวลา 3 วัน ช่วยอธิบายแบบที่คนไม่ใช่ dev เข้าใจหน่อย จริงๆ ต้องแก้ทั้ง API, DB migration แล้วก็ test

### A

อธิบายได้ครับ กุญแจสำคัญคือต้องทำให้ PM เห็นว่า "ปุ่ม" เป็นแค่สิ่งที่มองเห็น ส่วนงานจริงอยู่หลังผนัง

## ข้อความที่ส่งให้ PM ได้เลย

> ตัวปุ่มเองใช้เวลาไม่ถึงชั่วโมงครับ แต่สิ่งที่ปุ่มไปสั่งให้ระบบทำ ตอนนี้ยังไม่มีอยู่ เลยต้องสร้างขึ้นมาใหม่ทั้งเส้น
>
> เทียบง่าย ๆ เหมือนขอติดสวิตช์ไฟเพิ่มในห้องประชุม ตัวสวิตช์ราคาไม่กี่ร้อย ติดสิบนาทีเสร็จ แต่ถ้าในผนังยังไม่มีสายไฟเดินมาถึงจุดนั้น ก็ต้องเจาะผนัง เดินสายใหม่ ไปต่อที่ตู้ไฟหลัก แล้วตรวจให้แน่ใจว่าไม่ลัดวงจรก่อนเปิดใช้ ค่าแรงส่วนใหญ่อยู่ที่งานในผนัง ไม่ใช่ที่สวิตช์

แล้วค่อยแมปของจริงให้ดู

| สิ่งที่ต้องทำ | เทียบเป็นภาษาคน |
|---|---|
| แก้ API | เดินสายไฟจากสวิตช์ไปถึงตู้ไฟ |
| DB migration | ตู้เก็บเอกสารที่มีแฟ้มอยู่แล้วเป็นหมื่นใบ ต้องเพิ่มช่องใหม่โดยแฟ้มเดิมห้ามหายแม้แต่ใบเดียว |
| test | เปิดไฟทุกดวงในบ้านดูว่ายังติดเหมือนเดิม ไม่ใช่แค่ดวงใหม่ |

## แจกแจงให้เห็นว่า 3 วันมาจากไหน

PM ส่วนใหญ่ไม่ได้ติดใจที่ตัวเลข แต่ติดใจที่มองไม่เห็นว่าเวลาหายไปไหน พอแยกเป็นรายการให้ดู เรื่องจบเร็วกว่า

- **วันที่ 1** แก้โครงสร้างฐานข้อมูล เขียน migration แล้วลองรันกับข้อมูลชุดเดิม ขั้นนี้พลาดไม่ได้เพราะกระทบข้อมูลลูกค้าที่มีอยู่แล้ว
- **วันที่ 2** แก้ API กับหน้าจอให้คุยกันรู้เรื่อง รวมถึงเช็กว่าของเดิมที่เรียก API ตัวนี้อยู่ยังทำงานได้
- **วันที่ 3** test แก้จุดที่พัง แล้ว deploy

## จุดที่ควรเน้นตอนคุย

เรื่อง DB migration นี่ขายให้ PM เข้าใจง่ายที่สุด เพราะเป็นงานที่ย้อนกลับยาก ถ้าทำพลาดบน production แล้วข้อมูลเพี้ยน ค่าตามแก้แพงกว่า 3 วันเยอะ ลองพูดประมาณว่า "งานส่วนนี้ทำเร็วได้ แต่ถ้าพลาด เราจะเสียเวลากู้ข้อมูลเป็นสัปดาห์"

ถ้า PM ถามต่อว่าตัดอะไรออกได้บ้าง ตอบตรง ๆ ได้เลยว่า test คือส่วนเดียวที่ย่อได้ แต่ความเสี่ยงจะย้ายไปตกที่ production แทน แล้วให้ PM เป็นคนตัดสินใจเอง วิธีนี้ดีกว่าการต่อรองเรื่องตัวเลขวัน เพราะเปลี่ยนบทสนทนาจาก "ช้าไปไหม" เป็น "รับความเสี่ยงระดับไหนได้"

ถ้าอยากให้ช่วยเขียนเป็นข้อความ Slack สั้น ๆ หรือสไลด์หนึ่งหน้าสำหรับ PM บอกได้ครับ

### B

ประเด็นหลักคือต้องเปลี่ยนกรอบจาก "ปุ่มเดียวทำไมนาน" เป็น "ปุ่มคือส่วนที่มองเห็น แต่งานจริงอยู่ข้างหลัง" — และอย่าอธิบายแบบตั้งรับ ให้อธิบายเป็นเรื่องความเสี่ยงกับต้นทุน เพราะนั่นคือภาษาที่ PM ฟังรู้เรื่องที่สุด

## อุปมาที่ใช้ได้ผล

> "ปุ่มก็เหมือนสวิตช์ไฟบนผนัง สิ่งที่พี่เห็นคือสวิตช์ แต่สิ่งที่ผมต้องแก้คือสายไฟในผนังกับตู้ไฟ — และต้องเปลี่ยนตู้ไฟตอนที่ไฟในบ้านยังเปิดใช้งานอยู่ ห้ามดับแม้แต่วินาทีเดียว"

ตัวสวิตช์ (โค้ดปุ่ม) ใช้เวลาจริงอาจครึ่งชั่วโมง ที่เหลือคือสายไฟกับตู้ไฟ

## ข้อความที่ส่งให้ PM ได้เลย

> งานนี้หน้าบ้านเห็นเป็นปุ่มเดียวครับ แต่หลังบ้านแตะ 3 ชั้น:
>
> **1. ฐานข้อมูล (~1 วัน)** — ข้อมูลเดิมที่มีอยู่แล้วต้องแปลงให้เข้ากับโครงสร้างใหม่ ของเก่าห้ามหายห้ามเพี้ยน และต้องทำตอนระบบยังเปิดให้ลูกค้าใช้อยู่ ขั้นตอนนี้ย้อนกลับยากที่สุด ถ้าพลาดคือกู้ข้อมูลลูกค้า ไม่ใช่แค่แก้โค้ดใหม่
>
> **2. API (~1 วัน)** — ปุ่มไม่ได้ทำงานเอง มันเรียกไปที่ API ซึ่งมีหน้าจออื่นเรียกใช้อยู่ด้วย ต้องแก้โดยไม่ให้ของเดิมพัง
>
> **3. เทสต์ (~1 วัน)** — ไม่ได้เทสต์แค่ว่าปุ่มใหม่กดได้ แต่เทสต์ว่าของเดิมที่เคยใช้ได้ ยังใช้ได้อยู่ ส่วนนี้แหละที่กันไม่ให้เกิดเคสแบบ "แก้อย่างนึง พังอีกอย่าง" ที่ต้องมาตามแก้ทีหลัง
>
> ถ้าอยากได้เร็วกว่านี้ บอกได้ครับว่าตัดอะไรได้บ้าง แต่ส่วนที่ผมไม่แนะนำให้ตัดคือข้อ 1 กับ 3

## ทำไมจบด้วยการเสนอทางเลือก

ประโยคสุดท้ายสำคัญ — มันเปลี่ยนบทสนทนาจาก "dev อู้หรือเปล่า" เป็น "PM จะเลือกยังไง" ซึ่งเป็นงานของเขา และทำให้คุณไม่ได้อยู่ในฐานะคนที่ต้องแก้ตัว

ถ้าจำเป็นต้องเร่งจริง สิ่งที่พอต่อรองได้คือลด scope ของปุ่ม (เช่น เอาเฉพาะเคสหลัก ยังไม่รองรับทุก edge case) ไม่ใช่ลด migration หรือเทสต์

## กันปัญหาซ้ำรอบหน้า

ตอนให้ estimate ครั้งต่อไป ให้แตกตัวเลขตั้งแต่แรกเลย อย่าบอกแค่ "3 วัน" — บอกว่า "3 วัน = DB 1 + API 1 + test 1" คนฟังจะเห็นภาพทันทีว่าเวลาไปอยู่ตรงไหน และจะไม่ย้อนกลับมาถามคำถามนี้อีก ตัวเลขก้อนเดียวมักถูกตีความว่าเป็นการเผื่อเวลา ตัวเลขที่แตกแล้วถูกตีความว่าเป็นแผน

ถ้าบอกได้ว่าปุ่มนี้คืออะไร ระบบอะไร ผมช่วยปรับข้อความให้ตรงกับงานจริงมากขึ้นได้ครับ

เลือก: 

---

## 12-recommend-forms

> ฟอร์มยาวๆ ที่มีหลายหน้า ควรใช้ Reactive Forms หรือ Signal Forms ดี ช่วยแนะนำหน่อย

### A

## สรุปสั้น

**ถ้าเป็นงานที่ต้องขึ้น production เร็วๆ นี้ → Reactive Forms** ส่วน Signal Forms เก็บไว้ใช้กับงานใหม่ที่รับความเสี่ยงเรื่อง API เปลี่ยนได้

เหตุผลหลักไม่ใช่เรื่อง "อันไหนดีกว่า" แต่เป็นเรื่องสถานะ: Signal Forms ยังเป็น experimental (เข้ามาใน Angular 21) — ความรู้ผมถึงราวกลางปี 2026 มันยังไม่ stable และ signature ยังขยับระหว่าง minor version อยู่ ถ้าตอนนี้มันออกจาก experimental แล้วก็เช็ก changelog อีกทีนะครับ แต่สมมติฐานด้านล่างผมอิงว่ายังไม่ stable

แต่ตลกร้ายคือ **ฟอร์มหลายหน้าคือเคสที่ Signal Forms ชนะชัดที่สุด** เลยอยากให้เห็นภาพทั้งสองฝั่งก่อนตัดสินใจ

## สิ่งที่ต่างกันจริงในฟอร์มหลายหน้า

| ปัญหาที่เจอแน่ๆ ในฟอร์ม wizard | Reactive Forms | Signal Forms |
|---|---|---|
| Gate ปุ่ม "ถัดไป" ตาม validity ของ step | ต้อง `toSignal(statusChanges)` หรือ subscribe เอง | `form.step1().valid()` เป็น computed ตรงๆ |
| Validation ข้าม step (ตอบข้อ 1 แล้วข้อ 7 required) | `setValidators()` + `updateValueAndValidity()` ใน subscription — จุดที่พังบ่อยสุด | เขียน declarative ใน schema อ่านค่า step อื่นได้เลย |
| Save draft / resume | `getRawValue()` + ระวัง disabled control หาย | model เป็น plain object อยู่แล้ว serialize ได้ตรงๆ |
| Type safety ของฟอร์มใหญ่ nested | ใช้ได้ แต่ dynamic/nested แล้วเริ่มเลอะ | derive จาก interface ของ model ทั้งก้อน |
| Component library (Material, PrimeNG) | รองรับเต็ม ผ่าน `ControlValueAccessor` | ต้องเช็กเวอร์ชันไลบรารีว่ารองรับ `[control]` หรือยัง |
| ตัวอย่าง/คำตอบใน Stack Overflow | เยอะมาก | ยังน้อย |

ข้อ "validation ข้าม step" คือตัวตัดสินจริงๆ ถ้าฟอร์มคุณมี conditional logic เยอะ (แบบฟอร์มสมัคร/เคลม) โค้ด Reactive Forms จะกลายเป็นก้อน subscription ที่แก้ยากมาก

## สิ่งที่สำคัญกว่าการเลือก library

ไม่ว่าเลือกอันไหน ให้ทำแบบนี้: **ฟอร์มเดียวครอบทุกหน้า แล้วเก็บไว้ใน service ที่ provide ที่ route ของ wizard** ไม่ใช่ฟอร์มแยกต่อหน้า

```ts
// wizard.routes.ts — store อยู่รอดตลอดอายุ wizard แต่ถูกทำลายเมื่อออกจาก wizard
export const routes: Routes = [{
  path: 'apply',
  providers: [ApplicationWizardStore],
  children: [
    { path: 'personal', component: PersonalStep },
    { path: 'employment', component: EmploymentStep },
  ],
}];
```

แบบนี้กด Back/Next ข้อมูลไม่หาย, validate ข้าม step ได้, และ submit ทีเดียวจบ ถ้าแยกฟอร์มต่อหน้าแล้วค่อยมา merge คุณจะเจอปัญหาหนักกว่าเรื่องเลือก API เยอะ

## หน้าตาโค้ด

**Reactive Forms:**

```ts
@Injectable()
export class ApplicationWizardStore {
  private fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    personal: this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
    }),
    employment: this.fb.group({
      status: ['employed' as 'employed' | 'student'],
      employer: [''],
    }),
  });

  constructor() {
    // conditional validation ข้าม step — ต้องทำแบบ imperative
    this.form.controls.employment.controls.status.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe((status) => {
        const employer = this.form.controls.employment.controls.employer;
        employer.setValidators(status === 'employed' ? [Validators.required] : []);
        employer.updateValueAndValidity();
      });
  }

  stepValid(step: 'personal' | 'employment') {
    const c = this.form.controls[step];
    return toSignal(c.statusChanges.pipe(startWith(c.status)), { requireSync: true });
  }
}
```

**Signal Forms** (รูปร่างประมาณนี้ — เช็ก signature ปัจจุบันจาก docs ก่อนใช้):

```ts
interface Application {
  personal: { firstName: string; lastName: string };
  employment: { status: 'employed' | 'student'; employer: string };
}

@Injectable()
export class ApplicationWizardStore {
  readonly model = signal<Application>({
    personal: { firstName: '', lastName: '' },
    employment: { status: 'employed', employer: '' },
  });

  readonly form = form(this.model, (path) => {
    required(path.personal.firstName);
    required(path.personal.lastName);
    required(path.employment.employer, {
      when: ({ valueOf }) => valueOf(path.employment.status) === 'employed',
    });
  });
}
```

```html
<input [control]="store.form.personal.firstName" />
<button [disabled]="!store.form.personal().valid()">ถัดไป</button>
```

สังเกตว่า conditional validation หายไปทั้งก้อน subscription และ `model()` เป็น plain object ที่ยิง `POST` หรือ `localStorage.setItem` ได้ทันที

## คำแนะนำสุดท้าย

เลือก **Reactive Forms** ถ้า: ขึ้น production ภายในไม่กี่เดือน, พึ่ง component library หนัก, หรือทีมยังไม่คุ้น signals

เลือก **Signal Forms** ถ้า: Angular 21+ แบบ zoneless, เป็น internal tool หรือ greenfield, และฟอร์มมี conditional logic ซับซ้อนจนคุ้มกับการรับความเสี่ยง

อย่าผสมสองอันในฟอร์มเดียวกัน แต่ผสม "คนละฟอร์มในแอปเดียวกัน" ได้ — วิธีลองของที่ปลอดภัยคือเอา Signal Forms ไปใช้กับฟอร์มเล็กๆ ที่ไม่ critical ก่อน แล้วค่อยตัดสินใจกับ wizard ตัวจริง

ถ้าบอกผมได้ว่าใช้ Angular เวอร์ชันไหน ใช้ component library อะไร และฟอร์มมีกี่ step / conditional เยอะแค่ไหน ผมช่วยฟันธงให้ชัดกว่านี้ได้ครับ

### B

ฟอร์มหลายหน้าที่ต้อง ship ขึ้น production ตอนนี้ ผมแนะนำ Reactive Forms ครับ

Signal Forms ยังเป็น experimental อยู่ (เข้ามาตอน Angular 21) API ยังขยับได้ระหว่าง minor version เอาไปวางเป็นฐานของฟอร์มใหญ่ที่ต้องดูแลยาว ๆ แล้วมีโอกาสต้องตามแก้ทุกครั้งที่อัปเดต ซึ่งฟอร์ม wizard มักเป็นของที่อยู่กับโปรเจกต์ไปอีกหลายปี

## ทำไมถึงยังเป็น Reactive Forms

- typed forms นิ่งแล้ว `FormGroup` ซ้อนกันต่อ step ทำได้ตรงไปตรงมา
- ecosystem พร้อม ทั้ง Material, PrimeNG, library ของ third party ทุกตัว binding กับ `formControlName` ได้หมด
- เคสยาก ๆ ของ wizard เช่น validate ข้าม step, async validator เช็กซ้ำกับ server, dynamic `FormArray` มีคนเจอมาก่อนหมดแล้ว หาตัวอย่างง่าย
- คนในทีมที่เข้ามาใหม่อ่านโค้ดออกทันที

## แต่ Signal Forms เหมาะกับ wizard มากกว่าในเชิงโมเดล

ตรงนี้พูดตามตรง ถ้ามองแค่ความเข้ากันได้ Signal Forms ออกแบบมาตรงกับฟอร์มหลายหน้ากว่า

- data ทั้งหมดอยู่ใน signal ก้อนเดียวเป็น plain object ไม่ต้องห่วงว่า step component ถูก destroy แล้วค่าหาย
- validation แบบมีเงื่อนไข เช่น "ถ้าเลือกนิติบุคคล ค่อยบังคับกรอกเลขผู้เสียภาษี" เขียนใน schema ได้เลย ไม่ต้องไล่ `setValidators()` + `updateValueAndValidity()` เอง
- save draft คือ persist signal ตัวเดียว อ่าน resume ก็ set กลับเข้าไป จบ

เพราะงั้นเลือกแบบนี้ ถ้าเป็น internal tool หรือ POC ที่ยอมรับการแก้ตาม API ได้ ลองใช้ Signal Forms ไปเลย แต่ถ้าเป็นงานลูกค้าที่มี SLA เอา Reactive Forms

## สิ่งที่ทำได้ตอนนี้เพื่อย้ายทีหลังไม่เจ็บ

กฎเหล็กข้อเดียวคือ **อย่าให้ form เป็นเจ้าของข้อมูล** ให้ service เป็นเจ้าของ

```ts
@Injectable()
export class ApplicationWizardStore {
  private readonly data = signal<ApplicationDraft>(emptyDraft);
  readonly draft = this.data.asReadonly();

  patch(partial: Partial<ApplicationDraft>) {
    this.data.update(d => ({ ...d, ...partial }));
  }
}
```

แต่ละ step สร้าง `FormGroup` ของตัวเองจาก slice ที่ดึงมาจาก store พอกด "ถัดไป" ก็ `patch()` กลับเข้า store แล้ว navigate ทำแบบนี้แล้ววันที่ย้ายไป Signal Forms จะแตะแค่ชั้น component ไม่ต้องรื้อ flow ทั้งหมด

ของแถมอีกอย่างคือ progress bar กับปุ่ม submit หน้าสุดท้ายจะอ่าน state จาก store ตัวเดียว ไม่ต้องวิ่งไปถาม form ของแต่ละ step

## จุดพลาดที่เจอบ่อยกับ wizard แบบ Reactive Forms

- สร้าง `FormGroup` ใหญ่ก้อนเดียวไว้ที่ parent แล้วแต่ละ step ใช้ `formGroupName` ต่อ อันนี้ก็ได้ แต่ระวังว่า `form.valid` จะ false ตลอดทางจนกว่าจะกรอกครบทุก step ให้ gate ปุ่มถัดไปด้วย `form.get('step2')!.valid` แทน
- step ที่ข้ามได้ ต้อง `disable()` group นั้นด้วย ไม่งั้น validator ยังทำงานอยู่แล้วติดค้างแบบหาสาเหตุไม่เจอ
- อยากได้ความสะดวกแบบ signal ใช้ `toSignal(form.valueChanges, { initialValue: form.getRawValue() })` ไปก่อนได้ ได้ reactivity โดยไม่ต้องรอ API ใหม่

ตอนนี้โปรเจกต์อยู่ Angular เวอร์ชันไหน แล้วฟอร์มมี step ที่แสดงตามเงื่อนไขไหมครับ ถ้ามีเดี๋ยวผมร่างโครง store กับ step component ให้ดูเป็นตัวอย่าง

เลือก: 

---

## 13-architecture-cqrs

> อธิบาย CQRS ให้หน่อย ระบบ HR แบบของเราเหมาะจะใช้ไหม

### A

# CQRS คืออะไร

**Command Query Responsibility Segregation** = แยก "ทางที่เขียนข้อมูล" ออกจาก "ทางที่อ่านข้อมูล" ให้เป็นคนละ model กัน

ปกติเราใช้ model เดียวทำทั้งสองอย่าง เช่น มี entity `Employee` ตัวเดียวที่ทั้งรับ validation ตอนบันทึก และถูกเอาไปแสดงบนหน้าจอ ปัญหาคือความต้องการสองฝั่งนี้มันขัดกัน:

- **ฝั่งเขียน** ต้องการ normalize, invariant ครบ, transaction, business rule เข้ม
- **ฝั่งอ่าน** ต้องการ denormalize, join น้อย, ตอบเร็ว, รูปร่างตรงกับหน้าจอ

CQRS บอกว่า "งั้นเลิกยัดสองอย่างนี้ใส่ model เดียว"

## สิ่งที่คนเข้าใจผิดบ่อยที่สุด

CQRS **ไม่ใช่** package deal ที่ต้องเอาทั้งก้อน มันเป็น spectrum มี 4 ระดับ และส่วนใหญ่คนไปเหมารวมว่าระดับ 1 = ระดับ 4 เลยกลัวกันไปหมด

| ระดับ | ทำอะไร | ต้นทุน | Consistency |
|---|---|---|---|
| 1. แยกในโค้ด | `CommandHandler` / `QueryHandler` คนละชั้น, query ยิง SQL ตรงไม่ผ่าน ORM aggregate | แทบเป็นศูนย์ | Strong |
| 2. แยก read model | Materialized view / summary table ใน DB เดียวกัน | ต่ำ | Strong หรือ lag สั้น |
| 3. แยก DB | Write DB + Read DB + message bus + projection | **สูง** | Eventual |
| 4. + Event Sourcing | เก็บ event เป็น source of truth, state คือผลลัพธ์ที่ replay ออกมา | **สูงมาก** | Eventual |

ราคาที่ต้องจ่ายตั้งแต่ระดับ 3 ขึ้นไปคือ: eventual consistency (user กด save แล้วหน้า list ยังไม่อัปเดต), dual-write failure, ต้องมีกลไก rebuild projection, debug ยากขึ้นมาก, และต้อง maintain model สองชุดตลอดไป

---

# ระบบ HR ของคุณเหมาะไหม

ผมไม่มี context ของ codebase คุณใน session นี้ (ไม่มีไฟล์ให้อ่าน) เลยขอตอบจาก**ลักษณะทั่วไปของระบบ HR** ซึ่งค่อนข้างมีแพตเทิร์นชัด — ถ้าของคุณต่างจากนี้บอกได้ครับ

## คำตอบสั้น

**ระดับ 1–2: ควรทำ. ระดับ 3: อย่าเพิ่ง. ระดับ 4: ทำเฉพาะบาง aggregate**

## เหตุผล

**สิ่งที่ทำให้ HR ไม่เหมาะกับ CQRS แบบเต็มรูปแบบ:**

- **จำนวน user มีเพดาน** — ระบบ HR มี user เท่ากับจำนวนพนักงาน ไม่ใช่ internet-scale เหตุผลหลักของ CQRS ระดับ 3 คือ scale read แยกจาก write ซึ่งคุณน่าจะยังไม่เจอปัญหานั้นจริง
- **งานส่วนใหญ่เป็น CRUD ตรง ๆ** — แก้ที่อยู่พนักงาน, อัปเดตเบอร์โทร, เพิ่มแผนก พวกนี้ไม่มี business logic ซับซ้อนพอจะคุ้มกับการแยก model
- **Eventual consistency เป็นพิษกับ HR หลายจุด** — จุดที่อันตรายที่สุดคือ **ยอดวันลาคงเหลือ** ถ้าเช็คสิทธิ์จาก read model ที่ lag อยู่ พนักงานยิงใบลาสองใบพร้อมกันแล้วลาเกินสิทธิ์ได้เลย เรื่องแบบนี้ต้อง strong consistency ใน transaction เดียวเท่านั้น เงินเดือนก็เหมือนกัน

**สิ่งที่ทำให้ HR เหมาะ — และเหมาะมากกว่าที่คนคิด:**

- **Reporting กินทรัพยากรหนักกว่า transaction เยอะ** — headcount, turnover rate, OT summary, สรุปการลงเวลารายเดือน, dashboard ผู้บริหาร พวกนี้ join 5–10 ตารางและรันทับ transactional DB นี่คือจุดที่ CQRS ระดับ 2 คุ้มที่สุด
- **Load เป็น burst ไม่ใช่ sustained** — ตอกบัตรตอนเช้า 8:30, ปิดงวด payroll, ประเมินผลปลายปี ช่วงพวกนี้โหลดพุ่ง การแยก read path ช่วยไม่ให้ dashboard ไปแย่งทรัพยากรกับการตอกบัตร
- **HR เป็น event-driven โดยธรรมชาติอยู่แล้ว** — เข้างาน, ปรับตำแหน่ง, ขึ้นเงินเดือน, โอนย้าย, ลาออก มันคือ event ตามความจริงของ domain ไม่ใช่ event ที่เราประดิษฐ์ขึ้น
- **Compliance บังคับให้ต้องมี audit trail อยู่แล้ว** — ต้องตอบได้ว่าใครแก้เงินเดือนใคร เมื่อไหร่ ด้วยเหตุผลอะไร ถ้ายังไงก็ต้องเก็บ ก็เก็บให้เป็น event ไปเลย
- **Effective dating** — เงินเดือนมีผล 1 เม.ย., โครงสร้างองค์กรย้อนหลัง, ต้องออกรายงานย้อนหลังด้วยโครงสร้างตอนนั้น CRUD แบบ update-in-place ทำเรื่องนี้ไม่ได้

---

# สิ่งที่ผมแนะนำให้ทำจริง

**1. แยก command/query ในชั้น application (ทำเลย)**

Write ผ่าน domain service + transaction ตามปกติ แต่ **read ให้ยิง query ตรงคืน DTO ที่ตรงกับหน้าจอ** ไม่ต้องโหลด entity ทั้งก้อนผ่าน ORM แล้ว map ไป map มา ต้นทุนแทบไม่มี ได้ performance กับความชัดเจนของโค้ดทันที ไม่มี eventual consistency เข้ามาเกี่ยว

**2. ทำ read model เฉพาะ reporting/dashboard**

Materialized view หรือ summary table ที่ refresh ทุก 5–15 นาที สำหรับรายงานสรุปและ dashboard โดยเฉพาะ ตรงนี้ผู้ใช้ยอมรับ lag ได้สบาย — ไม่มีใครเดือดร้อนถ้า headcount บน dashboard ช้าไป 10 นาที ส่วนหน้าจอ operational (อนุมัติใบลา, ดูโปรไฟล์) ให้อ่านจาก write model ตรงไว้เหมือนเดิม

**3. ทำ Event Sourcing เฉพาะ aggregate ที่เป็น ledger จริง ๆ**

ตัวที่คุ้มที่สุดคือ **ยอดวันลา** — ทำเป็น append-only ledger เหมือนบัญชี: `+10 สิทธิ์ประจำปี`, `-1 ลาป่วย`, `+2 ยกยอดจากปีก่อน`, `-0.5 ลาครึ่งวัน` ยอดคงเหลือ = ผลรวม (+ snapshot รายปีกันช้า)

ข้อดีคือตอบคำถาม "ทำไมยอดเหลือ 7.5 วัน" ได้ทันทีโดยไม่ต้องไปขุด log แก้ย้อนหลังได้โดยไม่ทำลายประวัติ และ reconcile ตอนปลายปีง่ายมาก

ตัวที่ควรพิจารณาถัดมาคือ **employment history** (ตำแหน่ง/เงินเดือน/สังกัด) เพราะมัน effective-dated อยู่แล้ว

**ไม่ต้องทำ** กับ master data ธรรมดา เช่น ข้อมูลส่วนตัวพนักงาน, แผนก, ตำแหน่ง — CRUD ปกติพอ

**4. อย่าแยก database จนกว่าจะวัดได้ว่าเจ็บจริง**

ถ้ายังไม่มีตัวเลขที่ชี้ว่า read load ทำให้ write ช้า การแยก DB + message bus คือการเพิ่มโหมดพังใหม่ ๆ เข้ามาโดยไม่ได้อะไรกลับมา

---

# สัญญาณว่าคิดผิดตั้งแต่ต้น

ถ้าเจอข้อใดข้อหนึ่ง ให้ทบทวนใหม่:

- ทำ CQRS เพราะอยากให้ architecture ดูทันสมัย ไม่ใช่เพราะมีปัญหาที่วัดได้
- เอา eventual consistency ไปแตะยอดวันลา เงินเดือน หรือ flow อนุมัติ
- ทำทั้งระบบรวดเดียวแทนที่จะเริ่มจาก bounded context เดียว
- ทีมยังไม่มีคนที่เคยดูแล projection rebuild ตอนมันพังกลางดึก
- Command กับ Query ได้ model ที่หน้าตาเหมือนกันเป๊ะ (= ยังไม่มีเหตุผลต้องแยก)

---

# สิ่งที่จะเปลี่ยนคำตอบผม

ถ้าบอกข้อมูลพวกนี้มาได้ ผมจะฟันธงให้ชัดขึ้น:

1. **ขนาด** — พนักงานกี่คน องค์กรเดียวหรือ multi-tenant หลายบริษัท (ถ้าเป็น SaaS หลายพันบริษัท ภาพเปลี่ยนไปเยอะ)
2. **จุดที่เจ็บตอนนี้** — report ช้า? หน้า list ช้า? ตอกบัตรตอนเช้าล่ม? หรือยังไม่เจ็บแต่กำลังออกแบบของใหม่?
3. **Stack ปัจจุบัน** — .NET? Node? DB อะไร มี message bus อยู่แล้วหรือยัง
4. **ขนาดทีม** — CQRS ระดับ 3+ ต้องมีคนดูแล operational complexity ระยะยาว ทีม 3 คนกับทีม 15 คนคำตอบไม่เหมือนกัน
5. **Greenfield หรือของเดิม** — ถ้าเป็นระบบที่รันอยู่แล้ว ยิ่งควรทำแบบค่อย ๆ แทรกทีละส่วน

### B

CQRS คือการแยก model ของฝั่งเขียนกับฝั่งอ่านออกจากกันครับ ไม่ใช่แค่แยก method แต่แยกเป็นคนละเส้นทางเลย

ฝั่ง command รับคำสั่งที่เปลี่ยนข้อมูล เน้นถูกต้องตาม business rule ส่วนฝั่ง query แค่ดึงข้อมูลไปแสดง ไม่ต้องแบกกฎอะไรเลย ปั้น model ให้ตรงกับหน้าจอได้เต็มที่

## CQRS มีหลายระดับ ไม่ใช่ของตายตัว

คนมักเข้าใจว่า CQRS = แยก database สองตัว + message bus ซึ่งเป็นแค่ปลายสุดของสเกล จริง ๆ มี 4 ระดับ

**ระดับ 1: แยกแค่ในโค้ด** ใช้ database เดียวกัน มี `ApproveLeaveRequestCommand` กับ `GetLeaveBalanceQuery` แยก handler กัน ฝั่ง query ข้าม repository ไปยิง SQL หรือ Dapper ตรง ๆ ได้ ราคาถูก ได้ประโยชน์เยอะ

**ระดับ 2: แยก read model ใน DB เดียวกัน** ทำ denormalized table หรือ materialized view ไว้ให้รายงานอ่าน อัปเดตด้วย trigger หรือ job

**ระดับ 3: แยก database คนละตัว** write ลง SQL Server, read ไปอยู่ Elasticsearch หรือ read replica แล้ว sync ผ่าน event ตรงนี้เริ่มแพง และเจอ eventual consistency เต็ม ๆ

**ระดับ 4: บวก Event Sourcing** เก็บเป็น event ทั้งหมดแทน state ปัจจุบัน เป็นคนละเรื่องกับ CQRS นะ แค่มักมาด้วยกัน

## ราคาที่ต้องจ่าย

- โค้ดเยอะขึ้นชัดเจน CRUD ง่าย ๆ ที่เคยเขียน 20 บรรทัด กลายเป็น command + handler + validator + DTO
- eventual consistency ตั้งแต่ระดับ 3 ขึ้นไป ผู้ใช้กดบันทึกเสร็จ กด refresh แล้วยังไม่เห็นข้อมูล
- debug ยากขึ้น ต้องไล่ว่า event ไปติดตรงไหน
- ต้องดูแล infra เพิ่ม message broker, retry, dead letter queue

## ระบบ HR เหมาะไหม

ไม่รู้รายละเอียดระบบของทีม เลยตอบตามลักษณะงาน HR ทั่วไปก่อน แล้วค่อยปรับตามจริงได้

**เหมาะระดับ 1 มาก** เพราะ domain ของ HR เป็น command ชัดเจนโดยธรรมชาติ `ApproveLeaveRequest`, `TransferEmployee`, `TerminateEmployment` สื่อเจตนาดีกว่า `UpdateEmployee` ที่รับ DTO ก้อนเดียวแล้วเดาเอาว่าผู้ใช้ตั้งใจทำอะไร งาน HR แต่ละอย่างมีกฎไม่เหมือนกัน ย้ายแผนกกับลาออกต้องเช็กคนละชุด ยัดรวมใน update เดียวแล้วจะเละ

ส่วนฝั่ง query หน้าจอ HR มักต้อง join พนักงาน + แผนก + ตำแหน่ง + หัวหน้า + สิทธิ์ลา ถ้าดึงผ่าน entity กับ navigation property จะช้าและ N+1 ง่ายมาก แยกออกมายิง SQL ตรง ๆ คืนเป็น flat DTO สบายกว่าเยอะ

**ระดับ 3 ส่วนใหญ่ไม่คุ้ม** ระบบ HR มี user หลักพันถึงหลักหมื่น ไม่ใช่ระดับที่ write กับ read ต้องแย่ง resource กัน แยก database มาเพื่อแก้ปัญหา scale ที่ยังไม่เกิด แล้วต้องแลกกับ eventual consistency ซึ่งเป็นปัญหาจริงกับงาน HR

ลองนึกภาพ หัวหน้ากด approve ใบลา แล้วหน้าจอยังขึ้น "รออนุมัติ" อยู่ 2 วินาที เขาก็กดซ้ำ งาน approval flow ผู้ใช้คาดหวังเห็นผลทันที

**payroll ยิ่งต้องระวัง** เรื่องเงินพลาดไม่ได้ ถ้าตอนปิดงวดอ่านจาก read model ที่ sync ช้าไป 5 วินาที แล้วคำนวณเงินเดือนผิด อธิบายยากมาก ส่วนนี้แนะนำให้อ่านจาก write model ตรง ๆ ไปเลย

**ที่พอมีเหตุผล** คือทำ read model แยกเฉพาะจุด เช่น dashboard ผู้บริหาร หรือรายงานกำลังพลย้อนหลังที่ scan ข้อมูลหลายปี พวกนี้ยอมให้ข้อมูลช้าไปชั่วโมงหนึ่งได้ ไม่มีใครเดือดร้อน

## สรุป

เอาระดับ 1 ไปใช้ได้เลย คุ้มแน่ ๆ ส่วนระดับ 3 รอให้มีปัญหาจริงก่อนค่อยทำ และทำเฉพาะหน้าจอที่มีปัญหา ไม่ต้องยกทั้งระบบ

อยากถามกลับหน่อยว่าอะไรทำให้นึกถึง CQRS ตอนนี้ครับ ถ้าปัญหาคือรายงานช้า บางทีลง index ให้ถูกหรือเพิ่ม read replica จบเร็วกว่ามาก แต่ถ้าปัญหาคือ service class บวมจนแตะตรงไหนก็พัง อันนั้น CQRS ตอบโจทย์ตรง ๆ เลย

เลือก: 

---

## 14-debug-slow-page

> หน้า dashboard โหลดช้ามาก ประมาณ 8 วินาที ควรเริ่มไล่หาสาเหตุจากตรงไหนบ้าง

### A

เริ่มจากวัดก่อนครับ อย่าเพิ่งเดาว่าตรงไหนช้า เพราะ 8 วินาทีนี่อาจกระจายอยู่หลายจุด

## ขั้นแรก แบ่ง 8 วิให้ออกก่อน

เปิด DevTools แท็บ Network โหลดหน้าใหม่แบบ hard reload แล้วดู waterfall ว่าเวลาหมดไปกับอะไร

- **TTFB ของ request หลักสูง** (เช่น 5 วิกว่า response จะเริ่มมา) ปัญหาอยู่ที่ backend
- **request เยอะหรือไฟล์ใหญ่** เวลาไปอยู่ที่ transfer ปัญหาอยู่ที่ network กับ bundle
- **request เสร็จหมดตั้งแต่วิที่ 2 แต่หน้ายังว่างถึงวิที่ 8** ปัญหาอยู่ที่ frontend render

แค่ขั้นนี้ก็ตัดไปได้สองในสามทางแล้ว

## ถ้าเวลาอยู่ที่ backend

ไล่ตามลำดับความน่าจะเป็น

1. **N+1 query** อาการคลาสสิกของ dashboard ดึง list มา 50 แถว แล้ววนยิง query ต่อแถวละครั้ง เปิด log ของ ORM ดูจำนวน query ที่เกิดขึ้นจริงต่อหนึ่ง request
2. **query ไม่มี index** เอา query ที่ช้าที่สุดไปรัน EXPLAIN ดูว่ามี full table scan ตรงไหน
3. **ยิง API หลายตัวแบบต่อคิว** dashboard มักมีหลาย widget ถ้า frontend ยิงทีละตัวรอทีละตัว เวลาก็บวกกันไปเรื่อย ๆ ตรงนี้แก้ด้วยการยิงขนานได้เลย
4. **คำนวณ aggregate สด ๆ ทุกครั้ง** พวกยอดรวม ยอดเดือนนี้ ถ้าข้อมูลไม่ต้อง realtime ขนาดนั้น ทำ cache หรือ pre-aggregate ไว้

## ถ้าเวลาอยู่ที่ frontend

- bundle ใหญ่เกิน ดูว่า chart library หรือ date library ติดมาทั้งก้อนไหม พวกนี้ lazy load ได้
- render ข้อมูลเยอะเกินจำเป็น ตาราง 5000 แถวที่ไม่มี pagination หรือ virtual scroll
- แท็บ Performance กด record ตอนโหลด ดูว่ามี long task ตัวไหนกินเวลาเป็นวินาที

## คำถามที่ช่วยจำกัดวงได้เร็ว

- ช้าทุกครั้งหรือช้าเฉพาะครั้งแรกหลังไม่ได้เข้านาน ถ้าเป็นอย่างหลังน่าจะเป็น cold start หรือ cache หมดอายุ
- ช้าทุก user หรือเฉพาะ user ที่ข้อมูลเยอะ ถ้าเฉพาะบางคน ชี้ไปที่ query ที่ไม่สเกลตามปริมาณข้อมูล
- เพิ่งช้าหรือช้ามานาน ถ้าเพิ่งช้า ไล่ดู deploy ล่าสุดก่อนเลย เร็วกว่าไล่ทีละจุดเยอะ

ถ้าเอา screenshot ของ waterfall ใน Network tab มาให้ดู เดี๋ยวช่วยชี้ว่าควรเจาะตรงไหนต่อครับ

### B

## หลักคิด: อย่าเพิ่งเดา — แยกให้ได้ก่อนว่า 8 วินาทีนั้นหมดไปกับอะไร

เปิด DevTools → แท็บ Network → hard reload แล้วดู waterfall ก่อนเลย คำถามเดียวที่ต้องตอบคือ **เวลาส่วนใหญ่อยู่ช่วงไหน**

| ช่วงที่ช้า | แปลว่า | ไปดูต่อที่ |
|---|---|---|
| TTFB ของ request แรก / API สูง | backend หรือ DB ช้า | query, index, cache |
| TTFB เร็ว แต่ download นาน | payload ใหญ่ / bundle ใหญ่ | ขนาด JSON, code splitting |
| ไฟล์มาครบแล้วแต่หน้ายังขาว | render / JS ช้า | แท็บ Performance |
| request เรียงกันเป็นขั้นบันได | API waterfall (ยิงทีละตัว) | ทำให้ parallel |

ข้อสุดท้ายเป็นสาเหตุที่เจอบ่อยที่สุดในหน้า dashboard โดยเฉพาะ — มี 8 widget ยิง 8 endpoint แบบรอกันทีละตัว ตัวละ 1 วิ ก็ครบ 8 วินาทีพอดี ถ้า waterfall เป็นขั้นบันได คุณเจอต้นเหตุแล้วโดยไม่ต้องดูอย่างอื่น

## คำถามคัดกรองที่ช่วยตัดตัวเลือกได้เร็ว

- **ช้าทุกครั้ง หรือช้าเฉพาะครั้งแรก?** — ครั้งแรกอย่างเดียวมักเป็น cold start / lambda / connection pool ยังไม่อุ่น
- **ช้าเฉพาะ production หรือ local ก็ช้า?** — ถ้า local เร็วแต่ prod ช้า มักเป็นเรื่องปริมาณข้อมูลหรือ network latency ไม่ใช่โค้ด
- **ช้าเฉพาะ user บางคน / บางช่วงวันที่?** — เป็นสัญญาณชัดว่า query scale ตามจำนวน row ของ user นั้น
- **เพิ่งช้า หรือช้ามานาน?** — ถ้าเพิ่งช้า ให้ย้อนดู deploy ล่าสุดก่อนเลย คุ้มกว่าไล่โค้ดทั้งหมด

## ถ้าปัญหาอยู่ฝั่ง backend

ไล่ตามลำดับนี้:

1. **หา endpoint ที่ช้าที่สุด** จาก Network tab แล้วโฟกัสตัวเดียวก่อน อย่าแก้พร้อมกันหลายจุด
2. **นับจำนวน query ต่อ 1 request** — เปิด query log แล้วดู ถ้าเห็น query หน้าตาเหมือนกันรันซ้ำ 50-100 ครั้ง นั่นคือ N+1 (แก้ด้วย eager loading / join / batch)
3. **`EXPLAIN ANALYZE` query ที่ช้า** — มองหา full table scan, missing index บน column ที่ใช้ใน `WHERE` / `JOIN` / `ORDER BY`
4. **ดูว่ามีการคำนวณ aggregate สดทุกครั้งไหม** — `SUM`/`COUNT` ทั้งตารางเพื่อโชว์การ์ดใบเดียว เป็นปัญหาคลาสสิกของ dashboard แก้ด้วย summary table, materialized view หรือ cache ที่ refresh เป็นรอบ
5. **เช็ก external call** — ถ้า backend ไปเรียก API อื่นหรือ service อื่นระหว่างทาง ตรงนั้นมักเป็นคอขวดที่มองไม่เห็นจากฝั่ง client

## ถ้าปัญหาอยู่ฝั่ง frontend

- ขนาด JS bundle (ดู Coverage tab ว่าโหลดมาแล้วไม่ได้ใช้เท่าไร) — chart library หนัก ๆ ควร lazy load
- จำนวน re-render (React DevTools Profiler) — dashboard ที่ state ตัวเดียวทำให้ทั้งหน้า render ใหม่
- render ตารางหลายพันแถวพร้อมกันโดยไม่มี virtualization หรือ pagination

## สิ่งที่ควรทำก่อนแก้

วัดให้ได้ตัวเลข baseline แล้วจดไว้ (เช่น endpoint นี้ 4.2 วิ, bundle 2.1 MB) เพราะ dashboard มักช้าจากหลายสาเหตุรวมกัน ถ้าไม่มีตัวเลขเทียบ จะไม่รู้ว่าที่แก้ไปได้ผลจริงหรือแค่รู้สึกว่าเร็วขึ้น

---

ถ้าบอก stack ที่ใช้ (framework, ฐานข้อมูล, SSR/CSR) และ screenshot ของ Network waterfall มา ผมช่วยเจาะจุดที่น่าจะเป็นต้นเหตุให้ตรงกว่านี้ได้ครับ

เลือก: 

---

## 15-explain-code

> โค้ดนี้ทำอะไร
> 
> ```csharp
> public async Task<IActionResult> Get(int id) =>
>     await _cache.GetOrCreateAsync($"emp:{id}", async e =>
>     {
>         e.AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5);
>         return await _repo.FindAsync(id);
>     }) is { } emp ? Ok(emp) : NotFound();
> ```

### A

โค้ดนี้คือ GET endpoint ที่ดึงข้อมูลพนักงานตาม id โดยอ่านผ่าน cache ก่อนครับ ถ้าไม่มีใน cache ค่อยไป database แล้วเก็บผลไว้ 5 นาที หาไม่เจอก็คืน 404

ไล่ทีละส่วน

- `_cache.GetOrCreateAsync($"emp:{id}", ...)` หาใน memory cache ด้วย key แบบ `emp:5` ถ้ามีอยู่แล้วคืนค่าเลย ไม่แตะ database
- ถ้าไม่มี ก็รัน factory ข้างใน ตั้งอายุ entry 5 นาทีนับจากตอนสร้าง แล้วดึงจาก `_repo.FindAsync(id)` ค่าที่ได้จะลง cache ให้อัตโนมัติ
- `is { } emp` เป็น pattern ที่แมตช์ค่าที่ไม่ใช่ null พูดง่าย ๆ คือเช็ก null แล้วผูกค่าเข้าตัวแปร `emp` ในบรรทัดเดียว
- เจอ ก็ `Ok(emp)` ไม่เจอ ก็ `NotFound()`

## จุดที่ต้องระวัง

**1. null ก็เข้า cache ด้วย** `GetOrCreateAsync` เซ็ต `entry.Value` เสมอ ไม่ว่า factory จะคืนอะไรกลับมา ดังนั้นถ้ายิง id ที่ไม่มีจริง จะได้ entry ที่เก็บ null ค้างไว้ 5 นาที ถ้าระหว่างนั้นมีคนสร้างพนักงาน id นั้นขึ้นมา ก็ยังได้ 404 จนครบเวลา บางทีมตั้งใจทำแบบนี้เพื่อกัน DB โดนยิงรัว ๆ ด้วย id มั่ว แต่ถ้าตั้งใจ ควรแยกอายุให้สั้นกว่า เช่น 30 วินาที

**2. ไม่มีกัน cache stampede** ถ้ามี 50 request เข้ามาพร้อมกันตอน cache miss ทุกตัววิ่งไป DB หมด เพราะ `GetOrCreateAsync` ไม่ได้ล็อกอะไรไว้ ถ้า endpoint นี้โดนหนัก ให้ดู `HybridCache` ใน .NET 9 ที่กันให้แล้ว หรือทำ `SemaphoreSlim` แยกราย key เอง

**3. `IMemoryCache` อยู่ใน process เดียว** deploy หลาย instance เมื่อไหร่ แต่ละเครื่องจะมี cache ของตัวเอง ข้อมูลไม่ตรงกันได้นานถึง 5 นาที

**4. ไม่มีการล้าง cache ตอนแก้ข้อมูล** ถ้ามี endpoint update พนักงาน ต้องเรียก `_cache.Remove($"emp:{id}")` ด้วย ไม่งั้นแก้เสร็จแล้วยังเห็นของเก่า

**5. object ที่คืนไปเป็นตัวเดียวกับที่อยู่ใน cache** ทุก request ได้ reference เดียวกัน ถ้ามีโค้ดไหนไปแก้ field ของ entity ตัวนี้ ก็เท่ากับแก้ค่าใน cache ให้คนอื่นไปด้วย

## เขียนใหม่ให้ไม่ cache null

```csharp
public async Task<IActionResult> Get(int id)
{
    var key = $"emp:{id}";

    if (!_cache.TryGetValue(key, out Employee? emp))
    {
        emp = await _repo.FindAsync(id);
        if (emp is not null)
            _cache.Set(key, emp, TimeSpan.FromMinutes(5));
    }

    return emp is not null ? Ok(emp) : NotFound();
}
```

ยาวกว่าเดิมไม่กี่บรรทัด แต่ชัดเจนว่าอะไรลง cache อะไรไม่ลง

ถ้าบอกมาว่า service นี้รันกี่ instance และมี endpoint update ด้วยไหม เดี๋ยวแนะนำต่อได้ว่าควรอยู่กับ `IMemoryCache` หรือย้ายไป distributed cache ครับ

### B

โค้ดนี้เป็น action method ของ ASP.NET Core ที่ดึงข้อมูลพนักงานตาม `id` โดยมี in-memory cache คั่นหน้า repository

## แยกทีละส่วน

**1. Expression-bodied async method** — ทั้งเมธอดคือ expression เดียว ไม่มี `{ }` body

**2. `_cache.GetOrCreateAsync($"emp:{id}", ...)`** — extension method ของ `IMemoryCache` ทำงานแบบ:
- ถ้ามี key `emp:5` ใน cache อยู่แล้ว → คืนค่าจาก cache ทันที ไม่เรียก factory
- ถ้าไม่มี → เรียก factory lambda เพื่อสร้างค่า แล้วเก็บลง cache

**3. Factory lambda** — พารามิเตอร์ `e` คือ `ICacheEntry` ใช้ตั้งค่า entry นั้น ตรงนี้กำหนด `AbsoluteExpirationRelativeToNow = 5 นาที` คือหมดอายุแบบตายตัว 5 นาทีหลังถูกเก็บ (ไม่ใช่ sliding — เข้าถึงบ่อยแค่ไหนก็ไม่ยืดอายุ) จากนั้น `_repo.FindAsync(id)` ไปดึงจากฐานข้อมูลจริง

**4. `is { } emp ? Ok(emp) : NotFound()`** — `is { }` คือ property pattern ที่ match ค่าอะไรก็ได้ที่ไม่ใช่ null (เทียบเท่า `is not null`) พร้อมผูกค่าเข้าตัวแปร `emp` ถ้าเจอข้อมูลก็คืน 200 พร้อม body ถ้าเป็น null ก็คืน 404

สรุปคือ: **เช็ค cache ก่อน ถ้าไม่มีค่อยยิง DB แล้ว cache ไว้ 5 นาที เจอ → 200, ไม่เจอ → 404**

## จุดที่ควรรู้

**Negative caching** — ถ้า `FindAsync` คืน `null` ตัว `GetOrCreateAsync` ก็ยัง `entry.Value = null` และเก็บลง cache อยู่ดี แปลว่า 404 ถูก cache ไว้ 5 นาทีด้วย ถ้ามีการสร้างพนักงาน id นั้นขึ้นมาระหว่างนั้น API จะยังตอบ 404 ต่ออีกจนกว่าจะหมดอายุ ถ้าไม่ต้องการพฤติกรรมนี้ต้องเช็ค null แล้วค่อยตัดสินใจ cache เอง

**Cache stampede** — `GetOrCreateAsync` ไม่มี lock ถ้ามี request พร้อมกัน 50 ตัวตอน cache miss จะยิง `FindAsync` ทั้ง 50 ตัว ถ้าเป็นปัญหา ใน .NET 9 ขึ้นไปมี `HybridCache` ที่จัดการ stampede protection ให้

**ไม่มี `CancellationToken`** — client ตัดการเชื่อมต่อแล้ว query ยังวิ่งต่อ

**กรณี factory throw** — ตั้งแต่ .NET 7 เป็นต้นไป entry จะไม่ถูก commit (เพราะ `entry.Value` ยังไม่เคยถูก set) exception จะ propagate ออกมาตรงๆ ซึ่งเป็นพฤติกรรมที่ถูกต้อง

เลือก: 

---

## 16-upgrade-plan

> ถ้าจะย้ายโปรเจกต์จาก Angular 17 ไป 20 ต้องเตรียมอะไรบ้าง

### A

ต้องไล่ขึ้นทีละ major ครับ 17 → 18 → 19 → 20 ข้ามไม่ได้ เพราะ `ng update` จะรัน migration script ของแต่ละเวอร์ชันให้ ถ้ากระโดดข้ามจะไม่ได้ schematic ที่จำเป็น

## เตรียมก่อนเริ่ม

| เรื่อง | Angular 17 | Angular 20 |
|---|---|---|
| Node | 18.13+ | 20.11.1+ (ตัด 18 ออกแล้ว) |
| TypeScript | 5.2 | 5.8 |
| RxJS | 7.4+ | 7.8+ |

นอกจากนี้
- ไล่ดู `package.json` ทุกตัวว่ารองรับ Angular 20 หรือยัง โดยเฉพาะ UI library อย่าง PrimeNG, ng-zorro, ngx-bootstrap และพวก NgRx ตัวไหนยังไม่รองรับ ให้ตัดสินใจก่อนว่าจะรอ จะเปลี่ยน หรือจะ fork
- test ต้องรันผ่านหมดก่อนเริ่ม เพราะจะใช้เป็นตัววัดว่าแต่ละ step พังตรงไหน ถ้า coverage บางมาก แนะนำให้เขียนเพิ่มในส่วน business logic หลักก่อน
- แยก branch และ commit แยกทีละเวอร์ชัน เวลาต้องถอยจะได้ถอยเป็นช่วง ๆ ได้

## แต่ละช่วงเจออะไรบ้าง

**17 → 18** ช่วงนี้เบาที่สุด
- ส่วนใหญ่ `ng update @angular/core@18 @angular/cli@18` แล้วจบ
- ถ้ายังใช้ `*ngIf` `*ngFor` อยู่ จังหวะนี้เหมาะจะรัน `ng generate @angular/core:control-flow` แปลงเป็น `@if` `@for` เลย ไม่ต้องรอถึง 20
- Angular Material ขยับไป Material 3 ถ้าทีมทำ custom theme ไว้เยอะ ตรงนี้กินเวลามากกว่าตัว framework เอง

**18 → 19** ช่วงนี้หนักสุด
- standalone กลายเป็นค่า default migration จะไปเติม `standalone: false` ให้ทุก component ที่ยังประกาศใน NgModule diff จะใหญ่มาก แต่ไม่ต้องตกใจ
- import ที่ไม่ได้ใช้ใน standalone component จะกลายเป็น error ไม่ใช่แค่ warning
- timing ของ `effect()` เปลี่ยน ถ้ามีโค้ดที่พึ่งลำดับการทำงานของ effect ต้องเช็กจุดนี้
- `ExperimentalPendingTasks` เปลี่ยนชื่อเป็น `PendingTasks`

**19 → 20**
- `provideExperimentalZonelessChangeDetection` → `provideZonelessChangeDetection` (zoneless ขึ้น stable แล้ว)
- `afterRender` เปลี่ยนชื่อเป็น `afterEveryRender`
- `*ngIf` `*ngFor` `*ngSwitch` ขึ้นสถานะ deprecated (ยังใช้ได้ แต่ควรเคลียร์ให้หมด)
- API ที่ deprecated มานานโดนลบ เช่น `TestBed.get` และ `InjectFlags`
- Karma ขึ้นสถานะ deprecated ถ้าใช้ Karma อยู่ ยังรันได้ แต่ควรเริ่มวางแผนย้ายไป Vitest หรือ Jest
- `@angular/platform-browser-dynamic` deprecated ให้ย้ายไปใช้ของใน `@angular/platform-browser`

## จุดที่มักพังจริง ๆ

เรียงตามที่เจอบ่อย
1. ไลบรารี third-party ตามไม่ทัน อันนี้คือตัวบล็อกอันดับหนึ่ง ควรเช็กให้จบก่อนลงมือ
2. Angular Material theming เปลี่ยน API เยอะมากจาก M2 ไป M3 และมาจบที่ `mat.theme()` ใน v20 ถ้ามี SCSS theme เยอะ ให้กันเวลาไว้ต่างหากเลย
3. ถ้าใช้ custom webpack config ผ่าน `@angular-builders/custom-webpack` ต้องดูว่าจะอยู่กับ webpack builder ต่อ หรือย้ายไป `@angular/build:application` ที่เป็น esbuild
4. SSR ถ้าโปรเจกต์ทำ server-side rendering ไว้ API ฝั่ง `@angular/ssr` ขยับหลายรอบตั้งแต่ 17
5. test ที่พึ่ง `fakeAsync` หรือพฤติกรรมของ zone อาจมีที่หลุด

## ลำดับที่แนะนำ

1. อัป Node กับ TypeScript ใน dev environment และ CI ให้ถึงระดับที่ v20 ต้องการก่อน
2. ทำความสะอาดบน 17 ก่อน: แปลง control flow, ลบ API ที่ deprecated, ย้าย `HttpClientModule` ไป `provideHttpClient()` งานพวกนี้ทำบนเวอร์ชันเก่าง่ายกว่าไปทำตอนพังแล้ว
3. ไล่ทีละ major รัน `ng update` แล้วรัน build + test ให้ผ่านก่อนค่อยไปต่อ อย่าใช้ `--force` ถ้าไม่จำเป็น เพราะคือการข้ามการเช็ก peer dependency
4. ค่อยมาคิดเรื่อง zoneless, signal-based component, naming convention ใหม่ ทีหลัง พวกนี้เป็น optional ไม่ต้องทำพร้อมการ migrate

เครื่องมือที่ช่วยได้มากที่สุดคือ update.angular.dev เลือกเวอร์ชันต้นทางปลายทางแล้วจะได้ checklist ครบทุกข้อของแต่ละช่วง

ถ้าบอกขนาดโปรเจกต์คร่าว ๆ มาได้ ว่าใช้ UI library ตัวไหน มี NgModule เยอะไหม ทำ SSR หรือเปล่า เดี๋ยวผมช่วยประเมินเวลาและชี้จุดเสี่ยงเฉพาะของงานนี้ให้ครับ

### B

ย้าย Angular 17 → 20 เป็นการข้าม 3 major (17→18→19→20) หลักสำคัญที่สุดคือ **ต้องไล่ทีละ major ห้ามกระโดดข้าม** เพราะ `ng update` จะรัน migration schematics ของแต่ละเวอร์ชันตามลำดับ ถ้าข้ามไปเลยจะไม่ได้ schematic กลางทางและจะต้องมาแก้มือ

## 1. เตรียมก่อนเริ่ม (pre-flight)

- **Freeze feature work** — schematics จะแตะไฟล์หลายร้อยไฟล์ ถ้ามี branch ค้างเยอะจะ conflict หนักมาก เคลียร์/merge ให้หมดก่อน
- **CI ต้องเขียวและ test ต้องเชื่อถือได้** — ถ้า test coverage บาง การ upgrade จะกลายเป็นการเดา แนะนำให้มี smoke test ของ flow หลักอย่างน้อย
- **แยก branch ต่อ 1 major** (`chore/ng18`, `chore/ng19`, …) แล้ว merge ทีละตัว อย่ารวบเป็น PR เดียว
- **Node.js** — Angular 20 ต้องการ Node 20.11.1+ / 22.11+ / 24 (Node 18 ถูกตัดแล้ว) เช็ค CI image, Dockerfile, `engines` ใน package.json, และ `.nvmrc`
- **TypeScript** — v18 ต้อง TS ~5.4, v19 ~5.5–5.6, v20 ต้อง 5.8+ ถ้าโค้ดมี `any` เยอะหรือปิด strict ไว้ TS ที่ใหม่ขึ้นมักจะเจอ type error เพิ่ม
- **RxJS** — RxJS 6 ถูกตัดใน v18 ต้องอยู่ที่ 7.x ก่อน
- **สำรวจ dependency ทั้งหมด** ว่าตัวไหนรองรับ Angular 20 — ตัวที่ต้องเช็ค: Angular Material/CDK, NgRx, Nx (ถ้าใช้), PrimeNG/ng-zorro/ng-bootstrap, `angular-eslint`, `jest-preset-angular`, ngx-translate, chart libs ตัวที่ยังไม่รองรับคือ blocker จริง ให้ตัดสินใจล่วงหน้าว่าจะรอ / หา alternative / fork

## 2. งานจริงในแต่ละช่วง

**17 → 18**
ค่อนข้างราบรื่น ส่วนใหญ่เป็น automatic migration หลัก ๆ คือ built-in control flow (`@if`/`@for`) และ deferrable views เป็น stable, Material 3 stable, package `@angular/build` เริ่มถูกแยกออกมา

**18 → 19**
เป็นช่วงที่ schematics แตะโค้ดเยอะที่สุด:
- `standalone: true` กลายเป็นค่า default → schematic จะไล่ลบ flag ออกจากทุก component และใส่ `standalone: false` ให้ตัวที่ยังอยู่ใน NgModule (diff ใหญ่ แต่ปลอดภัย)
- `allowSignalWrites` ใน `effect()` ถูกถอด (เขียน signal ใน effect ได้เลยแล้ว) และ **timing ของ effect เปลี่ยน** — ถ้าโค้ดคุณพึ่งลำดับการรันของ effect ตรงนี้คือจุดที่พังแบบเงียบ ๆ ให้ไล่ดูเอง schematic ช่วยไม่ได้
- signal-based `input()` / `output()` / `viewChild()` stable

**19 → 20**
- **Karma ถูก deprecate** — ยังใช้ได้อยู่ แต่ควรวางแผนย้ายไป Vitest/Jest ในรอบถัดไป (ยังไม่ต้องทำในรอบนี้)
- Zoneless change detection เป็น developer preview — **ไม่จำเป็นต้องทำตอนนี้** อย่าเอามารวมใน PR upgrade
- Angular Material มี theming API ใหม่ (`mat.theme()`) ถ้าคุณ custom theme ไว้เยอะ ตรงนี้กินเวลา
- Style guide ใหม่เปลี่ยนวิธีตั้งชื่อไฟล์ (`user.ts` แทน `user.component.ts`) — มีผลกับไฟล์ที่ generate ใหม่เท่านั้น ของเดิมไม่ต้องแตะ

## 3. จุดเสี่ยงที่กินเวลามากที่สุด

เรียงตามโอกาสที่จะทำให้ timeline บาน:

1. **Custom webpack / Module Federation** — ถ้าใช้ `@angular-builders/custom-webpack`, `ngx-build-plus` หรือ Module Federation แบบ webpack นี่คือ blocker อันดับหนึ่ง เพราะ application builder ตัวใหม่ใช้ esbuild/Vite ไม่ใช่ webpack ต้องประเมินแยกเป็นงานต่างหากเลย
2. **การย้าย builder** `browser` → `application` — ถ้า project ยังใช้ `@angular-devkit/build-angular:browser` อยู่ จะเจอเรื่อง CommonJS dependency warnings, polyfills ที่เปลี่ยนรูปแบบ config, และ output path structure ที่เปลี่ยน (`dist/browser/`)
3. **SSR** — ถ้ายังใช้ `@nguniversal/*` ต้องย้ายมา `@angular/ssr` ก่อน (เป็น migration ของ v17 ที่หลายโปรเจกต์ค้างไว้)
4. **Material theming** ถ้า custom หนัก
5. **Third-party lib ที่ตามไม่ทัน**

## 4. ลำดับงานที่แนะนำ

```bash
# ต่อ 1 major: branch ใหม่ → update → build → test → merge
ng update @angular/core@18 @angular/cli@18
ng update @angular/material@18   # แยกทีละ package
npm run build && npm test
```

เคล็ดลับ: หลีกเลี่ยง `--force` และ `--legacy-peer-deps` ถ้าทำได้ เพราะมันจะซ่อนปัญหา peer dependency ไว้ให้ไประเบิดตอน runtime แทน ถ้าต้องใช้ ให้จดไว้ว่าใช้กับ package ไหนเพราะอะไร

**แยกเป็น PR ทีหลัง ไม่ต้องทำในรอบ upgrade:** control flow migration (`ng generate @angular/core:control-flow`), `inject()` migration, standalone migration, signal inputs migration ทั้งหมดนี้เป็น optional และทำย้อนหลังได้ การยัดรวมใน PR upgrade จะทำให้ review ไม่ได้และหา regression ไม่เจอ

## 5. ประมาณการ

สำหรับโปรเจกต์ขนาดกลางที่ไม่มี custom webpack และ dependency ไม่แปลก: **ประมาณ 3–5 วันทำงาน** สำหรับทั้ง 3 major รวม regression test ถ้ามี custom webpack / Module Federation / SSR ให้บวกไปอีกเท่าตัวเป็นอย่างน้อย

---

รายการ breaking change แบบครบถ้วนอยู่ที่ **angular.dev/update-guide** — เลือก from 17 to 20 แล้วติ๊ก complexity level ให้ตรงกับโปรเจกต์ อันนั้นคือ source of truth ที่ควรใช้เป็น checklist จริงตอนลงมือ

ถ้าบอกได้ว่าโปรเจกต์ใช้ builder ตัวไหน มี SSR ไหม และใช้ UI library อะไร ผมช่วยไล่ประเมินจุดเสี่ยงเฉพาะเจาะจงให้ได้ครับ

เลือก: 

---

## 17-readme-section

> ช่วยเขียนหัวข้อ "วิธีรันโปรเจกต์บนเครื่อง" ใน README ให้หน่อย โปรเจกต์ใช้ .NET 9, SQL Server ที่รันใน Docker และ Angular 20

### A

ด้านล่างเป็นหัวข้อที่เขียนไว้ให้ copy ไปวางใน README ได้เลยครับ ผมตั้งสมมติฐานไว้ 3 อย่าง (ปรับชื่อให้ตรงโปรเจกต์จริงได้เลย): โครงสร้างโฟลเดอร์เป็น `src/Api` กับ `src/web`, backend ใช้ EF Core migrations และ Angular เรียก API ผ่าน proxy

````markdown
## วิธีรันโปรเจกต์บนเครื่อง

### สิ่งที่ต้องติดตั้งก่อน

| เครื่องมือ | เวอร์ชันที่ใช้ |
|---|---|
| [.NET SDK](https://dotnet.microsoft.com/download) | 9.0 ขึ้นไป |
| [Node.js](https://nodejs.org/) | 20.19+, 22.12+ หรือ 24+ (ข้อกำหนดของ Angular 20) |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | เวอร์ชันล่าสุด |

ตรวจสอบว่าติดตั้งครบแล้ว:

```bash
dotnet --version   # ต้องขึ้นต้นด้วย 9.
node --version
docker --version
```

### 1. Clone โปรเจกต์

```bash
git clone <repo-url>
cd <ชื่อโฟลเดอร์โปรเจกต์>
```

### 2. รัน SQL Server ด้วย Docker

โปรเจกต์มีไฟล์ `docker-compose.yml` สำหรับฐานข้อมูลบนเครื่อง dev อยู่แล้ว:

```yaml
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: sqlserver-dev
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "Your_password123!"
      MSSQL_PID: "Developer"
    ports:
      - "1433:1433"
    volumes:
      - mssql-data:/var/opt/mssql

volumes:
  mssql-data:
```

สั่งรัน:

```bash
docker compose up -d
```

ตรวจสอบว่า container ขึ้นแล้ว:

```bash
docker compose ps
docker compose logs -f sqlserver   # รอจนเห็น "SQL Server is now ready for client connections"
```

> **หมายเหตุ**
> - รหัสผ่าน SA ต้องยาวอย่างน้อย 8 ตัวอักษร และมีตัวพิมพ์ใหญ่ พิมพ์เล็ก ตัวเลข และอักขระพิเศษ ไม่งั้น container จะดับทันทีหลังสตาร์ท
> - ข้อมูลถูกเก็บใน volume `mssql-data` ถ้าต้องการล้างฐานข้อมูลทั้งหมดให้ใช้ `docker compose down -v`
> - บน Mac ที่เป็น Apple Silicon ต้องเปิด Rosetta ใน Docker Desktop (Settings → General → Use Rosetta for x86/amd64 emulation)

### 3. ตั้งค่าและรัน Backend (.NET 9)

ตั้งค่า connection string ผ่าน User Secrets เพื่อไม่ให้รหัสผ่านหลุดเข้า git:

```bash
cd src/Api
dotnet user-secrets init
dotnet user-secrets set "ConnectionStrings:DefaultConnection" "Server=localhost,1433;Database=AppDb;User Id=sa;Password=Your_password123!;TrustServerCertificate=True"
```

> `TrustServerCertificate=True` จำเป็นสำหรับ dev เพราะ SQL Server ใน container ใช้ self-signed certificate

สร้างฐานข้อมูลและรัน migrations:

```bash
dotnet tool install --global dotnet-ef   # ข้ามได้ถ้าติดตั้งไว้แล้ว
dotnet restore
dotnet ef database update
```

รัน API:

```bash
dotnet run
```

API จะรันที่ `https://localhost:5001` และดู endpoint ทั้งหมดได้ที่ `https://localhost:5001/swagger`

ถ้าเบราว์เซอร์เตือนเรื่องใบรับรองไม่ปลอดภัย ให้รันคำสั่งนี้หนึ่งครั้ง:

```bash
dotnet dev-certs https --trust
```

### 4. ตั้งค่าและรัน Frontend (Angular 20)

เปิด terminal อีกหน้าต่างหนึ่ง:

```bash
cd src/web
npm ci
npm start
```

เปิดเบราว์เซอร์ที่ `http://localhost:4200`

Angular dev server จะ proxy request ที่ขึ้นต้นด้วย `/api` ไปยัง backend ตามค่าใน `proxy.conf.json`:

```json
{
  "/api": {
    "target": "https://localhost:5001",
    "secure": false,
    "changeOrigin": true
  }
}
```

ถ้าเปลี่ยนพอร์ตของ API อย่าลืมแก้ `target` ในไฟล์นี้ด้วย

### สรุปพอร์ตที่ใช้

| Service | URL |
|---|---|
| Angular (dev server) | http://localhost:4200 |
| .NET API | https://localhost:5001 |
| Swagger UI | https://localhost:5001/swagger |
| SQL Server | localhost,1433 |

### ปัญหาที่พบบ่อย

**`docker compose up` แล้ว container ดับทันที**
ดู log ด้วย `docker compose logs sqlserver` ส่วนใหญ่เกิดจากรหัสผ่าน SA ไม่ผ่านเกณฑ์ความซับซ้อน

**พอร์ต 1433 ถูกใช้งานอยู่แล้ว**
ถ้ามี SQL Server ติดตั้งบนเครื่องอยู่แล้ว ให้เปลี่ยน port mapping เป็น `"14330:1433"` แล้วแก้ connection string เป็น `Server=localhost,14330`

**`dotnet ef database update` ขึ้น error เชื่อมต่อไม่ได้**
ตรวจสอบว่า container พร้อมใช้งานแล้วจริง (SQL Server ใช้เวลาสตาร์ทประมาณ 10–30 วินาทีหลัง `docker compose up`)

**Angular ขึ้น error เรื่อง Node version**
Angular 20 ไม่รองรับ Node 18 แล้ว ให้อัปเกรดเป็น Node 20.19+ ขึ้นไป แนะนำให้ใช้ [nvm](https://github.com/nvm-sh/nvm) จัดการหลายเวอร์ชัน
````

สองจุดที่อยากให้ตรวจก่อนใช้งาน: ชื่อฐานข้อมูล (`AppDb`) และ path โฟลเดอร์ ถ้าโปรเจกต์ไม่ได้ใช้ EF Core migrations ให้แทนขั้นตอน `dotnet ef database update` ด้วยวิธี init ฐานข้อมูลที่ใช้จริง (เช่น รัน SQL script หรือ DbUp)

### B

เขียนให้แล้วครับ ขอเดาโครงโฟลเดอร์เป็น `src/Api` กับ `src/web` ไว้ก่อน ถ้าของจริงไม่ตรงก็แก้ชื่อ path ในไฟล์ได้เลย

````markdown
## วิธีรันโปรเจกต์บนเครื่อง

### สิ่งที่ต้องติดตั้งก่อน

| เครื่องมือ | เวอร์ชัน | เช็กด้วย |
|---|---|---|
| .NET SDK | 9.0 | `dotnet --version` |
| Node.js | 20.19+, 22.12+ หรือ 24.x | `node -v` |
| Docker Desktop | เวอร์ชันล่าสุด | `docker -v` |
| Angular CLI | 20.x | `ng version` |

Angular CLI จะติดตั้งแบบ global ก็ได้ (`npm i -g @angular/cli@20`) หรือเรียกผ่าน `npx ng` แทน

### 1. Clone โค้ดและเตรียม environment

```bash
git clone <repo-url>
cd <repo-name>
```

### 2. รัน SQL Server ด้วย Docker

ไฟล์ `docker-compose.yml` ที่ root:

```yaml
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: app-sqlserver
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "Your_strong_Password123"
      MSSQL_PID: "Developer"
    ports:
      - "1433:1433"
    volumes:
      - mssql-data:/var/opt/mssql

volumes:
  mssql-data:
```

สั่งรัน:

```bash
docker compose up -d
docker compose logs -f sqlserver   # รอจนขึ้น "SQL Server is now ready for client connections"
```

ครั้งแรก container ใช้เวลาประมาณ 20-30 วินาทีกว่าจะพร้อมรับ connection

> password ของ `sa` ต้องยาวอย่างน้อย 8 ตัว และมีตัวพิมพ์ใหญ่ ตัวพิมพ์เล็ก ตัวเลข หรืออักขระพิเศษ อย่างน้อย 3 ใน 4 กลุ่ม ไม่งั้น container จะดับทันทีที่สตาร์ท

### 3. ตั้งค่า connection string

เก็บ password ไว้ใน user secrets แทนการ commit ลง `appsettings.json`

```bash
cd src/Api
dotnet user-secrets init
dotnet user-secrets set "ConnectionStrings:DefaultConnection" \
  "Server=localhost,1433;Database=AppDb;User Id=sa;Password=Your_strong_Password123;TrustServerCertificate=True"
```

`TrustServerCertificate=True` จำเป็น เพราะ SqlClient เปิด encryption เป็นค่าเริ่มต้น แต่ container ใช้ self-signed certificate

### 4. สร้าง database และรัน migration

```bash
dotnet tool install --global dotnet-ef   # ข้ามได้ถ้าลงไว้แล้ว
dotnet ef database update --project src/Api
```

### 5. รัน API

```bash
dotnet dev-certs https --trust   # ทำครั้งเดียวต่อเครื่อง
cd src/Api
dotnet run
```

API จะขึ้นที่ `https://localhost:7001` และ Swagger อยู่ที่ `https://localhost:7001/swagger`
เลขพอร์ตจริงดูได้จาก `src/Api/Properties/launchSettings.json`

### 6. รัน Angular

เปิด terminal อีกหน้าต่าง:

```bash
cd src/web
npm install
npm start
```

เปิดเบราว์เซอร์ที่ `http://localhost:4200`

ฝั่ง frontend ยิง API ผ่าน proxy เพื่อเลี่ยงปัญหา CORS ตั้งค่าใน `src/web/proxy.conf.json`:

```json
{
  "/api": {
    "target": "https://localhost:7001",
    "secure": false,
    "changeOrigin": true
  }
}
```

### 7. เช็กว่าครบทุกส่วน

- `docker compose ps` เห็น container สถานะ `Up`
- เปิด `https://localhost:7001/swagger` แล้วยิง endpoint ใดก็ได้ผ่าน
- เปิด `http://localhost:4200` แล้วหน้าเว็บโหลดข้อมูลจาก API ได้

### หยุดการทำงาน

```bash
docker compose stop        # หยุด container แต่ข้อมูลยังอยู่
docker compose down        # ลบ container แต่ข้อมูลยังอยู่ใน volume
docker compose down -v     # ลบ volume ด้วย ข้อมูลใน database หายทั้งหมด
```

### ปัญหาที่เจอบ่อย

| อาการ | สาเหตุและวิธีแก้ |
|---|---|
| `Login failed for user 'sa'` | container ยังสตาร์ทไม่เสร็จ รอสักครู่แล้วลองใหม่ หรือ password ใน connection string ไม่ตรงกับใน compose |
| `The certificate chain was issued by an authority that is not trusted` | ลืมใส่ `TrustServerCertificate=True` ใน connection string |
| port 1433 ชนกัน | มี SQL Server ลงบนเครื่องอยู่แล้ว แก้ port mapping เป็น `"14330:1433"` แล้วเปลี่ยน connection string เป็น `Server=localhost,14330` |
| `dotnet ef` ไม่รู้จักคำสั่ง | ยังไม่ได้ติดตั้ง tool หรือ PATH ยังไม่อัปเดต ปิดแล้วเปิด terminal ใหม่ |
| Angular ฟ้องเรื่อง Node version | ใช้ nvm สลับไปเวอร์ชันที่ Angular 20 รองรับ |
| เรียก API จากหน้าเว็บแล้วได้ 404 | ตรวจว่า `npm start` อ่าน `proxy.conf.json` จริง ดูที่ `serve` options ใน `angular.json` |
````

สองจุดที่ควรแก้ให้ตรงกับของจริงก่อนใช้: ชื่อ path (`src/Api`, `src/web`) กับชื่อ database และ connection string key ว่าโค้ดอ่านชื่อไหนอยู่ ถ้าบอกโครงสร้างโฟลเดอร์จริงกับเลขพอร์ตมา เดี๋ยวปรับให้ตรงเป๊ะครับ

เลือก: 

---

## 18-tradeoff-graphql

> ทีมอยากเปลี่ยนจาก REST เป็น GraphQL มีข้อดีข้อเสียอะไรบ้าง

### A

ก่อนตอบข้อดีข้อเสีย อยากชวนตั้งคำถามก่อนว่าตอนนี้เจ็บตรงไหนครับ เพราะ GraphQL แก้ปัญหาบางแบบได้ดีมาก แต่ถ้าย้ายเพราะอยากลองของใหม่ จะเจอต้นทุนที่ไม่คุ้ม

## ข้อดี

**client ขอข้อมูลเองได้**
หน้า list ขอแค่ 3 field หน้า detail ขอ 20 field ใช้ query เดียวกันไม่ได้ก็เขียนคนละ query ไม่ต้องทำ endpoint `/users/summary` กับ `/users/full` แยกกัน ปัญหา over-fetching กับ under-fetching หายไปเกือบหมด

**ลด round trip**
หน้าเดียวที่เดิมต้องยิง 5 endpoint แล้วรอทีละตัว เหลือ request เดียว เรื่องนี้เห็นผลชัดมากบน mobile ที่ latency สูง

**schema เป็น contract ที่บังคับใช้จริง**
มี type ชัดเจน generate typescript type จาก schema ได้เลย เอกสารไม่หลุดจากโค้ดเพราะเป็นตัวเดียวกัน ต่างจาก swagger ที่ต้องคอยอัปเดตเอง

**frontend ไม่ต้องรอ backend**
UI เปลี่ยน อยากได้ field เพิ่มที่มีใน schema อยู่แล้ว ก็แก้ query ฝั่งเดียวจบ ทีมที่แยก frontend/backend ชัด ๆ ได้ประโยชน์ข้อนี้มากที่สุด

**versioning ง่ายกว่า**
ไม่ต้องทำ `/v2` ใช้ `@deprecated` ที่ field แล้วดูจาก metrics ว่ายังมีใครเรียกอยู่ไหม พอไม่มีคนใช้ค่อยลบ

## ข้อเสีย

**caching ยากขึ้นเยอะ**
ข้อนี้หนักสุด REST ได้ HTTP cache กับ CDN ฟรี แต่ GraphQL ยิง POST ไป `/graphql` ทางเดียว CDN ช่วยอะไรไม่ได้ ต้องไปทำ cache ที่ client (Apollo, urql) หรือใช้ persisted query + GET ถึงจะเอา CDN กลับมาได้ ซึ่งก็เป็นงานเพิ่ม

**N+1 query**
query ที่ขอ `posts { author { name } }` 50 posts จะกลายเป็น 51 query ถ้าไม่ระวัง ต้องใช้ DataLoader หรือตัวเทียบเท่าตั้งแต่วันแรก ไม่ใช่ค่อยมาแก้ทีหลัง

**คุมโหลดยาก**
rate limit แบบนับจำนวน request ใช้ไม่ได้แล้ว เพราะ 1 request หนักเบาไม่เท่ากัน ต้องทำ depth limit กับ query cost analysis เอง ไม่งั้นมีคนยิง query ซ้อน 10 ชั้นเข้ามาที DB ล่ม

**monitoring มืดลง**
ทุกอย่างเป็น `POST /graphql` ตอบ 200 หมด แม้แต่ตอน error APM เดิมที่ดู status code กับ path จะอ่านอะไรไม่ได้เลย ต้อง instrument ที่ระดับ resolver ใหม่

**error handling คนละโลก**
error มาใน `errors` array พร้อม HTTP 200 โค้ดฝั่ง client ที่เช็ก status code อยู่ต้องรื้อหมด

**authorization ละเอียดขึ้น**
เดิมเช็กที่ endpoint จบ ทีนี้ต้องเช็กราย field เพราะคนที่เข้า query ได้ อาจไม่ควรเห็น `user.salary`

**file upload กับ streaming ไม่ถนัด** ส่วนใหญ่สุดท้ายก็ต้องเหลือ REST endpoint ไว้ทำงานพวกนี้อยู่ดี

## ตัดสินใจแบบนี้

| สถานการณ์ | ควรไหม |
|---|---|
| มี client หลายตัว (web, iOS, Android) ขอข้อมูลต่างกัน | คุ้ม |
| หน้าหนึ่งต้องยิง 4-5 endpoint แล้วรอกัน | คุ้ม |
| frontend รอ backend ทำ endpoint ใหม่ตลอด | คุ้ม |
| public API ที่พึ่ง CDN cache หนัก | อย่า |
| internal API, client เดียว, endpoint นิ่งแล้ว | ไม่คุ้ม |
| ทีมเล็ก ไม่มีคนดูแล tooling เพิ่ม | ไม่คุ้ม |

## ถ้าจะย้ายจริง

อย่าทำ big bang เริ่มจากวาง GraphQL เป็น layer หน้า REST เดิม (BFF pattern) resolver ไปเรียก service เดิมที่มีอยู่ ยังไม่ต้องแตะ data layer แล้วเลือกมาสัก feature เดียวที่เจ็บที่สุด ทำให้จบ วัดผลจริงว่า request ลดลงเท่าไร หน้าเร็วขึ้นไหม ทีมรับไหวไหม ค่อยตัดสินใจขยาย

REST ก็ไม่ต้องทิ้ง webhook, health check, file upload, OAuth callback ปล่อยไว้แบบเดิมดีกว่า ระบบใหญ่ ๆ ส่วนใหญ่ก็อยู่กันสองแบบแบบนี้

ถ้าบอกได้ว่าตอนนี้ระบบหน้าตาประมาณไหน มี client กี่ตัว และปัญหาที่ทำให้อยากเปลี่ยนคืออะไร เดี๋ยวช่วยดูให้ว่าคุ้มหรือมีทางแก้ที่ถูกกว่าครับ

### B

## ข้อดีของ GraphQL

**ลด over-fetching / under-fetching**
Client ระบุ field ที่ต้องการเอง ไม่ต้องรับ payload ทั้งก้อน — ได้ผลชัดกับ mobile หรือเน็ตช้า

**ลด round trip**
จากเดิมที่ต้องยิง `/users/1` → `/users/1/orders` → `/orders/5/items` เหลือ query เดียว ซึ่งช่วยเรื่อง latency มากกว่าเรื่อง bandwidth อีก

**Schema เป็น contract ที่ strongly typed**
มี introspection ทำให้ codegen ได้จริง (TypeScript types, React hooks) และ tooling อย่าง GraphiQL / Apollo Studio ใช้งานได้ทันที เอกสารไม่หลุดจากโค้ดเหมือน OpenAPI ที่ต้องมาคอยอัปเดตเอง

**ลด coupling ระหว่างทีม**
Frontend เปลี่ยน requirement ได้โดยไม่ต้องรอ backend เพิ่ม endpoint ใหม่ ข้อนี้มักเป็นเหตุผลที่คุ้มที่สุดจริง ๆ ถ้าทีม frontend ถูก block บ่อย

**Versioning ยืดหยุ่นกว่า**
Deprecate ทีละ field ได้ ไม่ต้องทำ `/v2` ทั้งชุด

---

## ข้อเสียและต้นทุนที่ต้องจ่าย

**HTTP caching หายไป**
POST ไป endpoint เดียวทำให้ CDN / reverse proxy / browser cache ใช้ไม่ได้เลย ต้องไปทำ persisted queries + GET, หรือพึ่ง client-side cache (Apollo/urql) แทน ถ้าระบบปัจจุบันพึ่ง CDN caching หนัก ๆ นี่คือข้อเสียที่ใหญ่ที่สุด

**N+1 query problem**
Resolver ที่เขียนตรงไปตรงมาจะยิง DB ซ้ำมหาศาล ต้องใช้ DataLoader / batching แทบทุกที่ ซึ่งไม่ใช่ของที่เขียนครั้งเดียวจบ

**Security surface กว้างขึ้น**
Client เขียน query เองได้แปลว่ายิง query ลึก ๆ หรือซ้อน ๆ จนล่มระบบได้ ต้องมี depth limit, query cost analysis, allowlist ของ operation — งานที่ REST ไม่ต้องทำ

**Authorization ย้ายไปอยู่ระดับ field**
จากเดิมเช็คที่ route เดียวจบ กลายเป็นต้องเช็คทุก field ที่ sensitive และต้องมั่นใจว่าไม่มีช่องให้เข้าถึงอ้อมผ่าน relation

**Observability และ error handling ต้องรื้อ**
GraphQL ตอบ HTTP 200 เสมอแม้มี error ทำให้ alert ที่ตั้งบน 5xx ใช้ไม่ได้ และ metric แบบ per-endpoint ก็ใช้ไม่ได้ ต้อง instrument ใหม่เป็น per-operation

**เรื่องจุกจิกอื่น ๆ**
File upload ไม่ native, rate limiting แบบนับ request ใช้ไม่ได้ผล (ต้องนับ cost แทน), learning curve ของทีมทั้ง backend และ frontend

---

## ข้อคิดก่อนตัดสินใจ

คำถามสำคัญกว่าคือ **ปัญหาที่เจอตอนนี้คืออะไร** เพราะหลายเคสแก้ได้ถูกกว่ามาก:

- ถ้าปัญหาคือ over-fetching → ลอง sparse fieldsets (`?fields=id,name`) ก่อน
- ถ้าปัญหาคือ round trip เยอะ → ทำ BFF endpoint รวมข้อมูลให้หน้าจอนั้น ๆ
- ถ้าปัญหาคือ type safety / DX → OpenAPI + codegen หรือ tRPC (ถ้าเป็น TypeScript ทั้ง stack) ให้ผลใกล้เคียงด้วยต้นทุนต่ำกว่าเยอะ

**GraphQL คุ้มเมื่อ:** มีหลาย client ที่ต้องการข้อมูลต่างกัน (web / iOS / Android), data model เชื่อมโยงกันเป็น graph จริง ๆ, หรือมีทีม frontend หลายทีมที่ติดคอขวดที่ backend

**ไม่คุ้มเมื่อ:** เป็น CRUD ตรงไปตรงมา, มี client เดียว, ทีมเล็ก, หรือเป็น public API ให้ลูกค้าภายนอกใช้ (REST เรียนรู้ง่ายกว่าสำหรับคนนอก)

---

## ถ้าตัดสินใจจะไป

อย่า rewrite ทั้งระบบรวดเดียว — วิธีที่เสี่ยงน้อยสุดคือวาง GraphQL layer ครอบ REST เดิม แล้วย้ายทีละ domain หรือเริ่มจากหน้าจอที่เจ็บที่สุดหน้าเดียว วัดผลจริงว่า latency / จำนวนบรรทัดโค้ด frontend ดีขึ้นจริงไหม แล้วค่อยขยาย ระหว่างนั้น REST เดิมยังอยู่ได้ ไม่มีใครต้องรอ

ถ้าบอกได้ว่าตอนนี้ pain point ของทีมคืออะไร และ client มีกี่ตัว จะช่วยประเมินให้ตรงกว่านี้ได้ครับ

เลือก: 

---

## 19-short-async

> async/await ใน C# ทำงานยังไงข้างใน อธิบายสั้นๆ

### A

สรุปสั้น ๆ คือ compiler แปลง method ที่ติด `async` ให้กลายเป็น state machine แล้วทุกจุดที่ `await` ก็คือจุดพักที่ method return กลับไปหา caller แล้วค่อยกลับมาทำต่อตอนงานเสร็จครับ

**ตอน compile**

- method นี้ถูกแปลงเป็น struct ที่ implement `IAsyncStateMachine` มี field `state` เก็บว่าพักอยู่ตรงไหน
- ตัวแปร local ที่ต้องอยู่ข้าม `await` กลายเป็น field ของ struct นั้น เพราะอยู่บน stack ต่อไม่ได้
- มี `AsyncTaskMethodBuilder` ทำหน้าที่สร้าง `Task` ส่งกลับให้ caller ตั้งแต่ยังไม่มีผลลัพธ์

**ตอนรัน**

พอ `MoveNext()` วิ่งมาเจอ `await` จะเรียก `GetAwaiter()` ก่อน แล้วเช็ก `IsCompleted`

- ถ้าเสร็จแล้ว ก็ทำต่อแบบ synchronous เลย ไม่มีการสลับ thread ไม่มี allocation เพิ่ม ซึ่งเป็น fast path ที่เจอบ่อยกว่าที่คิด เช่นอ่านจาก cache
- ถ้ายังไม่เสร็จ ก็ลงทะเบียน continuation ผ่าน `OnCompleted` แล้ว return ออกไปทันที caller ได้ `Task` ที่ยังไม่เสร็จกลับไปทำอย่างอื่นต่อ

พองานเสร็จ callback จะเรียก `MoveNext()` อีกรอบ ค่า `state` บอกว่าต้องกระโดดไปทำต่อบรรทัดไหน ผลลัพธ์ดึงมาจาก `GetAwaiter().GetResult()` ซึ่งเป็นจุดเดียวกับที่ exception เด้งออกมา เลยเขียน try/catch คร่อม `await` ได้ตามปกติ

**เรื่อง thread**

จุดที่คนเข้าใจผิดบ่อยสุดคือคิดว่า `await` สร้าง thread ใหม่ ความจริงคือไม่มี thread นั่งรอ I/O งานจริงไปอยู่ที่ OS (บน Windows คือ IOCP) พอเสร็จค่อยมีคนจาก thread pool หยิบ continuation ไปทำต่อ

ส่วน `ConfigureAwait(false)` เกี่ยวกับตรงนี้ ปกติ continuation จะกลับไปทำบน `SynchronizationContext` เดิม เช่น UI thread การใส่ `false` คือบอกว่าไม่ต้องกลับ ทำบน thread pool ต่อได้เลย ใน library code ควรใส่ แต่ใน ASP.NET Core ไม่มี context อยู่แล้ว ไม่ใส่ก็ไม่ต่างกัน

อยากให้แกะ IL หรือดูโค้ดที่ compiler gen ออกมาจริง ๆ ไหมครับ จะได้เห็นหน้าตา state machine ชัดกว่านี้

### B

## สรุปสั้นที่สุด
`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **การแปลงโค้ดตอน compile** — compiler ตัดเมธอดออกเป็นชิ้นๆ ตามจุด `await` แล้วประกอบใหม่เป็น **state machine** ที่เรียกตัวเองซ้ำได้

## สิ่งที่ compiler สร้าง

โค้ดที่เราเขียน:

```csharp
async Task<int> GetAsync()
{
    var data = await httpClient.GetStringAsync(url);  // จุดตัด
    return data.Length;
}
```

ถูกแปลงเป็นประมาณนี้ (ย่อมาก):

```csharp
struct StateMachine : IAsyncStateMachine   // struct ใน Release, class ใน Debug
{
    public int _state;                      // -1 = ยังไม่เริ่ม/จบแล้ว, 0 = รอ await ตัวแรก
    public AsyncTaskMethodBuilder<int> _builder;
    public string _data;                    // local variable กลายเป็น field
    private TaskAwaiter<string> _awaiter;

    public void MoveNext()
    {
        switch (_state)
        {
            case -1:
                _awaiter = httpClient.GetStringAsync(url).GetAwaiter();
                if (!_awaiter.IsCompleted)           // ยังไม่เสร็จ → ยอมแพ้ชั่วคราว
                {
                    _state = 0;
                    _builder.AwaitUnsafeOnCompleted(ref _awaiter, ref this);
                    return;                          // คืน control ให้ caller ทันที
                }
                goto case 0;                         // เสร็จแล้ว → วิ่งต่อเลย ไม่ yield
            case 0:
                _data = _awaiter.GetResult();        // ดึงผล หรือ rethrow exception
                _builder.SetResult(_data.Length);
                return;
        }
    }
}
```

ส่วน `GetAsync()` ตัวจริงเหลือแค่: สร้าง state machine → `builder.Start(ref sm)` (เรียก `MoveNext()` ครั้งแรก **แบบ synchronous บน thread เดิม**) → `return builder.Task`

## กลไกตอน await

1. **`GetAwaiter()`** — `await` เป็น *pattern-based* ไม่ผูกกับ `Task` อะไรก็ awaitable ได้ขอแค่มี `GetAwaiter()` ที่คืน type ซึ่งมี `IsCompleted`, `GetResult()` และ implement `INotifyCompletion`
2. **Fast path** — ถ้า `IsCompleted == true` (เช่น cache hit, `Task.FromResult`) จะไม่มีการ yield ไม่มี allocation เลย วิ่งต่อเหมือนโค้ด sync
3. **Slow path** — state machine ที่เป็น struct จะถูก **box ขึ้น heap** ครั้งเดียวตรงนี้ แล้วลงทะเบียน `MoveNext` เป็น continuation กับ awaiter จากนั้น return ออกไป → caller ได้ `Task` ที่ยังไม่เสร็จ **thread ถูกปล่อยคืน ไม่มี thread ใดนั่งรอ**
4. **ตอนงานเสร็จ** — awaiter เรียก continuation → `MoveNext()` ถูกเรียกอีกครั้ง → `switch` กระโดดกลับไปจุดที่ค้างไว้

## จุดที่คนมักเข้าใจผิด

- **async ≠ thread ใหม่** งาน I/O จริงๆ รออยู่ที่ OS (IOCP) ไม่มี thread ไหนถูกใช้ระหว่างรอ ส่วน `Task.Run` ต่างหากที่ยืม thread จาก thread pool
- **Context capture** — ตอนลงทะเบียน continuation awaiter จะจำ `SynchronizationContext` (หรือ `TaskScheduler`) ปัจจุบันไว้ แล้ว post `MoveNext` กลับไปที่เดิม นี่คือเหตุผลที่ UI code กลับมาอยู่บน UI thread ได้เอง และเป็นที่มาของ deadlock เวลาใช้ `.Result` บน context ที่มี thread เดียว — `ConfigureAwait(false)` คือการบอกว่าไม่ต้อง capture
- **Exception** — ไม่ถูกโยนออกจากเมธอดตรงๆ แต่ถูกจับใส่ `Task` ผ่าน `builder.SetException()` แล้วตอน `GetResult()` ค่อย rethrow โดยใช้ `ExceptionDispatchInfo` เพื่อรักษา stack trace เดิม
- **ต้นทุน** — ทุกครั้งที่ไปถึง slow path จะเสีย allocation (boxed state machine + `Task`) ถ้าเป็น hot path ที่มักเสร็จแบบ sync ให้ใช้ `ValueTask` และ `[AsyncMethodBuilder(typeof(PoolingAsyncValueTaskMethodBuilder))]` เพื่อ pool ตัว state machine กลับมาใช้ซ้ำ

เลือก: 

---

## 20-teach-junior-di

> น้องในทีมเพิ่งจบใหม่ ยังไม่เข้าใจว่า dependency injection คืออะไร ช่วยอธิบายให้เข้าใจง่ายๆ หน่อย

### A

อธิบายสั้นที่สุดคือ "คลาสไม่ต้องหาของใช้เอง ให้คนอื่นส่งเข้ามาให้" ครับ

เปรียบเทียบง่าย ๆ เหมือนครัวร้านอาหาร เชฟไม่ต้องไปปลูกผักเอง มีคนเตรียมวัตถุดิบมาวางให้ถึงมือ เชฟมีหน้าที่ทำอาหารอย่างเดียว DI ก็แบบนั้น คลาสไหนต้องใช้อะไรก็ประกาศไว้ที่ constructor แล้วรอรับ

## ปัญหาที่ DI มาแก้

ลองดูโค้ดแบบที่ยังไม่ใช้ DI

```csharp
public class OrderService
{
    private readonly SqlOrderRepository _repo = new SqlOrderRepository();

    public void Place(Order order)
    {
        _repo.Save(order);
    }
}
```

ตรง `new SqlOrderRepository()` นี่แหละคือตัวปัญหา เพราะ `OrderService` ผูกกับ `SqlOrderRepository` แบบแกะไม่ออก ผลที่ตามมาคือ

- เขียน unit test ไม่ได้ เพราะทุกครั้งที่เทสจะวิ่งไปต่อ database จริง
- วันไหนอยากเปลี่ยนไปใช้ที่เก็บแบบอื่น ต้องเข้าไปแก้ในคลาสนี้
- ถ้า `SqlOrderRepository` ต้องการ connection string เพิ่ม `OrderService` ก็ต้องรู้เรื่องนั้นไปด้วยทั้งที่ไม่ใช่หน้าที่

## ทำเป็น DI

```csharp
public class OrderService
{
    private readonly IOrderRepository _repo;

    public OrderService(IOrderRepository repo)
    {
        _repo = repo;
    }

    public void Place(Order order)
    {
        _repo.Save(order);
    }
}
```

เปลี่ยนแค่นี้เอง จาก new เองกลายเป็นรับเข้ามาทาง constructor ทีนี้ `OrderService` รู้แค่ว่า "มีของที่ save order ได้" ส่วนของจริงจะเป็นตัวไหนไม่สนใจแล้ว

เวลาเทสก็ส่งตัวปลอมเข้าไปได้เลย

```csharp
var service = new OrderService(new FakeOrderRepository());
```

## แล้วใครเป็นคนส่งของเข้ามา

ตอน run จริงคนส่งคือ DI container ซึ่งใน .NET มีมาให้ในตัว เราแค่ไปบอกไว้ที่เดียวว่าของแต่ละอย่างหน้าตายังไง

```csharp
builder.Services.AddScoped<IOrderRepository, SqlOrderRepository>();
builder.Services.AddScoped<OrderService>();
```

พอมีคนขอ `OrderService` container จะเห็นว่า constructor ต้องใช้ `IOrderRepository` ก็ไปหยิบ `SqlOrderRepository` มาสร้างให้อัตโนมัติ ไล่ลงไปเรื่อย ๆ จนครบทั้งสาย

จุดนี้น้องมักสับสน เลยอยากย้ำ: DI คือแนวคิดการส่งของเข้ามาทาง constructor ส่วน container เป็นแค่ตัวช่วยประกอบให้ ไม่มี container ก็ทำ DI ได้ แค่ต้อง new เองที่จุดเริ่มโปรแกรม

## lifetime ที่ต้องรู้ไว้

ตอนลงทะเบียนจะมีสามแบบให้เลือก เรื่องนี้ชนบ่อยมาก

| แบบ | สร้างใหม่เมื่อไหร่ | เหมาะกับ |
|---|---|---|
| Transient | ทุกครั้งที่มีคนขอ | ของเบา ๆ ที่ไม่เก็บ state |
| Scoped | ครั้งเดียวต่อหนึ่ง request | DbContext, repository |
| Singleton | ครั้งเดียวตลอดอายุแอป | config, cache |

กฎเหล็กข้อเดียวที่ต้องจำคือ อย่าเอา scoped ไปยัดใน singleton เช่น singleton ที่รับ `DbContext` เข้ามา เพราะ context ตัวนั้นจะค้างอยู่ตลอดอายุแอปแทนที่จะจบไปพร้อม request แล้วจะเจอ error แปลก ๆ ตอน production

## สรุปให้น้องจำ

เห็น `new` อยู่ในคลาสที่มี business logic เมื่อไหร่ ให้สงสัยไว้ก่อนว่าควรดึงออกมาเป็น constructor parameter ไหม ยกเว้นพวก object ข้อมูลล้วน ๆ อย่าง DTO หรือ model พวกนั้น new ได้ตามปกติ

ถ้าทีมใช้ Angular หรือ TypeScript เดี๋ยวผมเขียนตัวอย่างชุดเดียวกันให้ใหม่ได้ครับ แนวคิดเหมือนกันเป๊ะ ต่างแค่ syntax

### B

## สรุปประโยคเดียวก่อน

**Dependency Injection คือ "อย่าไปหาของที่ต้องใช้เอง ให้คนอื่นส่งมาให้"**

---

## อุปมาแบบเห็นภาพ

ลองนึกถึงเชฟสองแบบ:

- **เชฟแบบ A**: จะทำผัดกะเพรา ต้องเดินไปตลาดเอง เลือกร้าน ซื้อหมู ซื้อใบกะเพราเอง → ถ้าอยากให้เขาลองทำด้วยเนื้อแทนหมู ต้องไปแก้โค้ดข้างในหัวเขา และถ้าอยากทดสอบว่าเขาผัดเป็นไหม ก็ต้องให้เขาเดินไปตลาดจริงๆ ทุกครั้ง
- **เชฟแบบ B**: บอกว่า "ส่งเนื้อสัตว์กับผักมาให้ผม แล้วผมผัดให้" → อยากได้เมนูเนื้อก็ส่งเนื้อมา อยากทดสอบก็ส่งของปลอมมาได้

เชฟแบบ B คือ Dependency Injection ครับ

---

## โค้ดจริง — แบบที่ยังไม่มี DI

```csharp
public class OrderService
{
    private readonly SqlOrderRepository _repo = new SqlOrderRepository();
    private readonly SmtpEmailSender _email = new SmtpEmailSender();

    public void PlaceOrder(Order order)
    {
        _repo.Save(order);
        _email.Send(order.CustomerEmail, "สั่งซื้อสำเร็จ");
    }
}
```

ดูเผินๆ ไม่เห็นมีอะไรผิด แต่ปัญหาคือ:

1. **เขียนเทสต์ไม่ได้** — เรียก `PlaceOrder` ทีไร ต่อ DB จริงและยิงอีเมลจริงทุกครั้ง
2. **เปลี่ยนของไม่ได้** — วันหนึ่งย้ายจาก SQL ไป MongoDB หรือเปลี่ยนจาก SMTP ไป SendGrid ต้องเข้ามาแก้ `OrderService` ทั้งที่ logic การสั่งซื้อไม่ได้เปลี่ยนเลย
3. **`OrderService` รู้มากเกินไป** — มันควรรู้แค่ "ขั้นตอนการสั่งซื้อ" ไม่ใช่ "ต้องต่อ DB ยังไง"

---

## โค้ดเดิม แบบมี DI

```csharp
public class OrderService
{
    private readonly IOrderRepository _repo;
    private readonly IEmailSender _email;

    // ของที่ต้องใช้ รับเข้ามาทาง constructor
    public OrderService(IOrderRepository repo, IEmailSender email)
    {
        _repo = repo;
        _email = email;
    }

    public void PlaceOrder(Order order)
    {
        _repo.Save(order);
        _email.Send(order.CustomerEmail, "สั่งซื้อสำเร็จ");
    }
}
```

เปลี่ยนแค่สองอย่าง:
- พึ่งพา **interface** (`IOrderRepository`) แทนคลาสจริง (`SqlOrderRepository`)
- **รับเข้ามาทาง constructor** แทนการ `new` เอง

ทีนี้เทสต์ง่ายมาก:

```csharp
var service = new OrderService(new FakeOrderRepository(), new FakeEmailSender());
service.PlaceOrder(order);
// ไม่แตะ DB ไม่ส่งอีเมลจริง รันเร็วเป็นมิลลิวินาที
```

---

## แล้ว "DI Container" คืออะไร?

พอทำแบบนี้ไปเรื่อยๆ จะเจอปัญหาใหม่ — ใครเป็นคน `new` ให้?

```csharp
var service = new OrderService(
    new SqlOrderRepository(new DbConnection(connStr)),
    new SmtpEmailSender(new SmtpConfig(...)));
```

เขียนเองก็ได้ แต่พอโปรเจกต์ใหญ่ขึ้นจะเริ่มเหนื่อย DI Container เลยเข้ามาช่วย เราแค่ **ลงทะเบียน**ไว้ว่าเจอ interface ตัวไหนให้หยิบคลาสไหนมาใช้ ที่เหลือมันประกอบให้เอง:

```csharp
builder.Services.AddScoped<IOrderRepository, SqlOrderRepository>();
builder.Services.AddScoped<IEmailSender, SmtpEmailSender>();
builder.Services.AddScoped<OrderService>();
```

จุดที่น้องใหม่มักสับสน: **DI กับ DI Container ไม่ใช่สิ่งเดียวกัน** — DI คือ *แนวคิด* (รับของเข้ามาแทนที่จะหาเอง) ส่วน Container เป็นแค่ *เครื่องมือ* ที่ช่วยทำให้สะดวก ไม่มี Container ก็ทำ DI ได้

---

## Lifetime — เรื่องที่ต้องรู้เพิ่มถ้าใช้ Container

ตอนลงทะเบียนจะต้องบอกว่าอยากให้ object อยู่นานแค่ไหน:

| แบบ | ความหมาย | ใช้เมื่อไหร่ |
|---|---|---|
| `Transient` | สร้างใหม่ทุกครั้งที่ขอ | object เบาๆ ไม่มี state |
| `Scoped` | ตัวเดียวต่อ 1 request | ส่วนใหญ่ใช้อันนี้ เช่น DbContext, Repository |
| `Singleton` | ตัวเดียวตลอดอายุแอป | config, cache, ของที่ thread-safe |

**กับดักคลาสสิก**: อย่าเอา Scoped ไปยัดใน Singleton (เช่น Singleton ที่ inject `DbContext` เข้าไป) — มันจะค้างอยู่ตลอดอายุแอปและพังแบบหาสาเหตุยากมาก

---

## ข้อควรระวังที่อยากให้น้องรู้ตั้งแต่แรก

**1. ไม่ใช่ทุกอย่างต้อง inject** — คลาสที่ไม่มี side effect อย่าง `DateTime`, `StringBuilder`, value object ต่างๆ `new` ตรงๆ ได้เลย ให้ inject เฉพาะของที่แตะโลกภายนอก (DB, API, ไฟล์, เวลา, random) หรือของที่อยากสลับไส้ในได้

**2. ถ้า constructor มีพารามิเตอร์ 8-10 ตัว นั่นไม่ใช่ปัญหาของ DI** — มันคือสัญญาณว่าคลาสนั้นทำงานเยอะเกินไป ควรแตกออก DI แค่ทำให้ปัญหาที่ซ่อนอยู่มองเห็นได้ชัดขึ้นเท่านั้น

**3. อย่าใช้ Service Locator** — คือการ inject ตัว container เข้ามาแล้วไปขอของเอาเองข้างใน:

```csharp
// อย่าทำ
public OrderService(IServiceProvider sp) { _sp = sp; }
public void PlaceOrder(Order o) { var repo = _sp.GetService<IOrderRepository>(); }
```

แบบนี้ซ่อน dependency ไว้ข้างใน มองจาก constructor ไม่รู้เลยว่าคลาสนี้ต้องใช้อะไรบ้าง — เสียประโยชน์หลักของ DI ไปเกือบหมด

---

## วิธีอธิบายให้น้องจำได้

ลองให้น้องถามตัวเอง 2 คำถามนี้ทุกครั้งที่จะเขียน `new` ในคลาส:

1. "ของชิ้นนี้ตอนเขียนเทสต์ ฉันอยากสลับเป็นของปลอมไหม?"
2. "ของชิ้นนี้มีโอกาสเปลี่ยนไส้ในไหม?"

ถ้าตอบ "ใช่" ข้อใดข้อหนึ่ง → รับเข้ามาทาง constructor ครับ

เลือก: 

---
