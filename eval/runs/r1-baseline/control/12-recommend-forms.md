## สรุปสั้น

**ใช้ Reactive Forms สำหรับงาน production ตอนนี้** — แต่วางโครงให้ย้ายไป Signal Forms ได้ง่ายทีหลัง

สิ่งเดียวที่อาจเปลี่ยนคำตอบคือเวอร์ชัน Angular ที่ใช้อยู่: Signal Forms เข้ามาเป็น experimental ตั้งแต่ v21 ถ้าโปรเจกต์ยังอยู่ต่ำกว่านั้น ก็ไม่มีตัวเลือกให้ตัดสินใจอยู่แล้ว

## ทำไมถึงยังเป็น Reactive Forms

1. **Signal Forms ยัง experimental** — ไม่อยู่ภายใต้ semver guarantee, API เปลี่ยนแบบ breaking ได้ใน minor release ฟอร์มหลายหน้าเป็นงานที่กินเวลาเป็นสัปดาห์ถึงเดือน การเจอ API เปลี่ยนกลางทางเจ็บกว่าที่คิด
2. **Ecosystem** — Angular Material, component library ของบริษัท, ngx-mask, date picker ต่างๆ ที่ implement `ControlValueAccessor` ใช้กับ Reactive Forms ได้แน่นอน ฝั่ง Signal Forms มี interop ให้แต่ยังไม่ครบทุกเคส
3. **คนในทีมรู้เยอะกว่า** — ฟอร์มยาวๆ มักมีหลายคนแตะ

## แต่ Signal Forms เหมาะกับ multi-page มากในเชิงแนวคิด

เพราะ model เป็น signal ก้อนเดียวที่ถือข้อมูลทุกหน้า ทำให้ save draft / restore ง่าย, conditional field ข้ามหน้าเขียนแบบ declarative ด้วย `applyWhen()` / `hidden()` / `disabled()`, และ cross-page validation เป็นธรรมชาติเพราะเห็นข้อมูลทั้งก้อน

ถ้าเป็น internal tool, prototype, หรือทีมเล็กที่ควบคุม dependency ได้เอง และอยู่ Angular 21+ — ลองได้เลย

## Pattern ที่ทำให้ย้ายง่าย: แยก "ข้อมูล" ออกจาก "ฟอร์ม"

หัวใจคือมี store กลางถือ state ของทั้งฟอร์ม แล้วแต่ละหน้าหยิบ `FormGroup` ของตัวเองไปใช้

```ts
interface ApplicationDraft {
  personal: { firstName: string; lastName: string };
  employment: { status: 'employed' | 'student'; company: string };
}

@Injectable({ providedIn: 'root' })
export class ApplicationStore {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    personal: this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
    }),
    employment: this.fb.group({
      status: ['employed' as const],
      company: [''],
    }),
  });

  // สะพานไปโลก signal — component อ่านผ่านตัวนี้
  readonly value = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });

  isStepValid(step: keyof ApplicationDraft) {
    return this.form.controls[step].valid;
  }
}
```

แต่ละ step component ผูกเฉพาะส่วนของตัวเอง:

```ts
@Component({
  template: `
    <form [formGroup]="group">
      <input formControlName="firstName" />
      <input formControlName="lastName" />
    </form>
  `,
})
export class PersonalStepComponent {
  protected readonly group = inject(ApplicationStore).form.controls.personal;
}
```

เวลาย้ายไป Signal Forms ภายหลัง `ApplicationDraft` กับ validation rules ยังอยู่เหมือนเดิม เปลี่ยนแค่ชั้นใน store:

```ts
// ภาพคร่าวๆ ของฝั่ง Signal Forms — API ยัง experimental เช็ค docs ก่อนใช้จริง
private readonly model = signal<ApplicationDraft>(initial);

readonly form = form(this.model, (path) => {
  required(path.personal.firstName);
  applyWhen(path, (m) => m.employment.status === 'employed', (p) => {
    required(p.employment.company);
  });
});
```

## เรื่องที่ต้องคิดอยู่ดี ไม่ว่าจะเลือกอันไหน

- **Validate ตอนกด "ถัดไป"** ไม่ใช่ตอน submit หน้าสุดท้าย — ถ้าไม่ผ่านให้ `markAllAsTouched()` บน group ของ step นั้นเพื่อให้ error แสดง
- **กันคนกดข้าม step** ด้วย route guard ที่เช็ค step ก่อนหน้าว่า valid
- **Save draft** — `form.valueChanges.pipe(debounceTime(500))` ลง localStorage หรือยิง API ฟอร์มยาวๆ คนทำไม่จบในรอบเดียวแน่นอน
- **Performance** — ถ้าฟิลด์เยอะมาก `valueChanges` ของ root group จะยิงรัวทุกตัวอักษร ใช้ `{ updateOn: 'blur' }` กับฟิลด์ที่ไม่ต้อง validate แบบ real-time
- **Lazy step** — ถ้ามี 10+ หน้า ค่อยสร้าง `FormGroup` ของ step ตอนเข้าหน้านั้น (`form.addControl(...)`) แทนที่จะสร้างทั้งหมดตั้งแต่แรก

ถ้าบอกได้ว่าใช้ Angular เวอร์ชันไหน ฟอร์มกี่หน้า และใช้ component library ตัวไหน ผมช่วยวางโครงให้ละเอียดกว่านี้ได้
