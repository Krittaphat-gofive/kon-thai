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
