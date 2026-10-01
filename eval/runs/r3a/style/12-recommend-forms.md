ถ้างานนี้มีกำหนดขึ้น production ตอบสั้น ๆ คือ Reactive Forms ครับ

เหตุผลหลักไม่ใช่เรื่องความสามารถ แต่เป็นเรื่องความนิ่งของ API Signal Forms เข้ามาเป็น experimental ตั้งแต่ Angular 21 และยังมี breaking change ระหว่างเวอร์ชันอยู่ ฟอร์ม wizard หลายหน้าเป็นงานก้อนใหญ่ ใช้เวลาหลายสัปดาห์ ถ้าเจอ API เปลี่ยนตอนทำไปได้ครึ่งทางนี่เจ็บมาก (ข้อมูลผมถึงกลางปี 2026 ถ้าตอนนี้ประกาศ stable แล้วก็เช็กใน changelog อีกที)

## ทำไมฟอร์มหลายหน้าถึงต้องคิดเยอะกว่าปกติ

ปัญหาจริงของ wizard ไม่ได้อยู่ที่ว่าใช้ API ไหน แต่อยู่ที่สี่ข้อนี้

1. state ต้องอยู่รอดตอนสลับหน้า ถ้าแต่ละ step เป็น route แยก Angular จะ destroy component ทิ้งทุกครั้งที่กดถัดไป
2. validation ข้าม step เช่น step 3 ต้องกรอกเลขผู้เสียภาษี เฉพาะตอนที่ step 1 เลือกว่าเป็นนิติบุคคล
3. step ที่ข้ามได้ตามเงื่อนไข
4. draft ที่กลับมาทำต่อได้

## ถ้าเลือก Reactive Forms

กฎเหล็กข้อเดียวคือ เก็บ root form ไว้ใน service หรือ parent component ที่ไม่ตายตามการ navigate แล้วให้แต่ละ step หยิบ sub-group ของตัวเองไปใช้

```ts
@Injectable()
export class WizardFormService {
  private fb = inject(FormBuilder);

  readonly form = this.fb.group({
    personal: this.fb.group({
      firstName: ['', Validators.required],
      customerType: ['individual' as 'individual' | 'company'],
    }),
    address: this.fb.group({ /* ... */ }),
    payment: this.fb.group({
      taxId: [''],
    }),
  }, { updateOn: 'blur' });

  isStepValid(step: keyof typeof this.form.controls) {
    return this.form.controls[step].valid;
  }
}
```

provide ตัวนี้ที่ route ของ wizard (ไม่ใช่ `providedIn: 'root'`) จะได้เคลียร์ทิ้งเองตอนออกจาก flow

ส่วน step component ก็สั้นมาก

```ts
export class PersonalStepComponent {
  readonly group = inject(WizardFormService).form.controls.personal;
}
```

สามจุดที่มักพลาด
- `updateOn: 'blur'` ช่วยเยอะตอนฟอร์มมี field เป็นร้อย เพราะค่า default จะ validate ทุก keystroke ไล่ขึ้นไปถึง root
- ถ้าใช้ `disable()` กับ step ที่ข้าม ค่าจะหายจาก `form.value` ต้องอ่านด้วย `getRawValue()` แทน
- validation ข้ามกลุ่มต้องสั่ง `updateValueAndValidity()` เองตอนต้นทาง เปลี่ยน ตรงนี้คือจุดที่เจ็บที่สุดของ Reactive Forms และเป็นที่มาของบั๊ก "กรอกครบแล้วแต่ปุ่มยังกดไม่ได้"

## Signal Forms เหมาะกับงานนี้ตรงไหน

พูดตามตรงคือเหมาะกว่าในเชิงแนวคิด เพราะ source of truth เป็น signal ของข้อมูลทั้งก้อน แล้ว form โครงสร้างค่อย derive ออกมา

```ts
const model = signal<WizardData>(initialData);

const wizardSchema = schema<WizardData>((path) => {
  required(path.personal.firstName);
  applyWhen(path, (d) => d().personal.customerType === 'company', () => {
    required(path.payment.taxId, { message: 'นิติบุคคลต้องกรอกเลขผู้เสียภาษี' });
  });
});

const wizardForm = form(model, wizardSchema);
```

ข้อดีที่เห็นชัดกับ wizard
- validation ข้าม step อ่าน model ตรง ๆ ได้เลย reactive เอง ไม่ต้องสั่ง update อะไรทั้งนั้น
- แยก schema เป็นไฟล์ต่อ step แล้วเอามาประกอบกัน เข้ากับโครงสร้าง wizard พอดี
- validation เป็น computed แบบ lazy ฟอร์ม 200 field จะคำนวณเฉพาะส่วนที่ template อ่านจริง
- model เป็น plain object อยู่แล้ว เซฟ draft ลง storage ง่ายกว่ามาก

ข้อแม้คือชื่อ API พวกนี้ยังขยับระหว่างเวอร์ชัน ให้ยืนยันกับ docs ของเวอร์ชันที่ใช้อยู่ก่อนเขียนจริง

## สรุปเป็นตาราง

| สถานการณ์ | เลือก |
|---|---|
| ขึ้น production ปีนี้ ทีมหลายคน | Reactive Forms |
| internal tool หรือ POC รับ breaking change ไหว | Signal Forms |
| มี custom control / lib ภายนอกเยอะ | Reactive Forms เพราะ ecosystem ของ ControlValueAccessor พร้อมกว่า |
| logic ข้าม step เยอะมาก | Signal Forms ถ้าเวอร์ชันพร้อม ไม่งั้น Reactive แล้วรวม logic ไว้ใน service |

## ทางสายกลางที่ผมแนะนำ

ถ้ายังลังเล ให้แยกชั้นข้อมูลออกจากชั้นฟอร์มตั้งแต่แรก คือเก็บ wizard state เป็น `signal<WizardData>` ไว้ใน service เป็น source of truth แล้วแต่ละหน้าค่อยสร้าง FormGroup เล็ก ๆ จากข้อมูลก้อนนั้น พอออกจาก step ก็ patch กลับเข้า signal

ทำแบบนี้แล้ว business logic อย่างเงื่อนไขข้าม step หรือกฎ validation ข้ามหน้า จะอยู่ในชั้นที่ไม่ผูกกับ forms API เลย วันที่อยากย้ายไป Signal Forms ก็เปลี่ยนแค่ชั้น UI ไม่ต้องรื้อ logic

ถ้าบอกได้ว่าฟอร์มมีกี่ step แต่ละ step ประมาณกี่ field และแยกเป็น route หรือใช้ component เดียวสลับ view เดี๋ยวผมร่างโครงให้ดูเป็นตัวอย่างได้ครับ
