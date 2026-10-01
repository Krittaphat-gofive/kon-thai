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
