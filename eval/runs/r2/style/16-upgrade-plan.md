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
