เกลาแล้ว linter เหลือ 0 จุด (เดิม 19 จุดต่อ 652 ตัวอักษร)

---

## สรุปสั้น ๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation** คือ compiler แปลง method เป็น **state machine**

### 1. Compiler แปลงเป็น State Machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

compiler แปลงให้เป็น struct ที่ implement `IAsyncStateMachine` คร่าว ๆ แบบนี้:

```csharp
struct StateMachine : IAsyncStateMachine {
    public int _state;                      // ตอนนี้อยู่ state ไหน
    public AsyncTaskMethodBuilder<int> _builder;
    public int _a;                          // local var → กลายเป็น field
    TaskAwaiter<int> _awaiter;

    public void MoveNext() {
        switch (_state) {
            case -1:
                _awaiter = FetchAsync().GetAwaiter();
                if (!_awaiter.IsCompleted) {
                    _state = 0;
                    _builder.AwaitUnsafeOnCompleted(ref _awaiter, ref this);
                    return;                 // ← คืน thread กลับไป
                }
                goto case 0;
            case 0:
                _a = _awaiter.GetResult();  // กลับมาทำงานต่อตรงนี้
                _builder.SetResult(_a + 1);
                return;
        }
    }
}
```

**หัวใจคือ:** local variables กลายเป็น fields เพราะ stack หายไปตอน `return` ต้องเก็บ state ไว้บน heap แทน

### 2. จุดสำคัญที่คนมักเข้าใจผิด

| เรื่อง | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** เพราะ I/O จริงใช้ IOCP (OS callback) ไม่มี thread นั่งรออยู่เลย |
| `await` บล็อก thread | **ไม่** `await` จะ `return` ออกไปเลย thread ว่างไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่** ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer แล้ว) ก็วิ่งต่อแบบ synchronous ไม่ alloc อะไรเลย |

state machine เป็น `struct` อยู่บน stack **จนกว่า** จะเจอ await ที่ยังไม่เสร็จจริง ถึงจะ box ขึ้น heap เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุน

### 3. กลับมาที่ไหน? → SynchronizationContext

ตอนเรียก `AwaitUnsafeOnCompleted` await จะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ปัจจุบันเก็บไว้ พอ operation เสร็จก็ post `MoveNext` กลับไปที่นั่น

- **ASP.NET Core / Console** ไม่มี context → resume บน thread pool thread ตัวไหนก็ได้
- **WPF / WinForms** มี context → resume บน UI thread (แก้ UI ต่อได้เลย)
- `ConfigureAwait(false)` สั่งว่า "ไม่ต้อง capture" ลด overhead และกัน deadlock ในฝั่ง library

### 4. Exceptions

state machine catch exception ใน `MoveNext` ไว้เอง แล้วส่งเข้า `_builder.SetException(ex)` → เก็บไว้ใน Task → พอเรียก `GetResult()` ก็ rethrow ด้วย `ExceptionDispatchInfo` ซึ่ง**รักษา stack trace เดิมไว้** (ไม่เหมือน `throw ex;` ที่ทำ stack trace หาย)

---

**สรุปบรรทัดเดียว:** compiler หั่น method เป็นชิ้น ๆ ตาม `await` แล้วเย็บกลับเป็น state machine ที่เรียก `MoveNext()` ซ้ำ ๆ แต่ละครั้งทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรอ

---

**แก้อะไรไปบ้าง**

- **em dash 10 จุด** ภาษาไทยไม่ใช้เครื่องหมายนี้ แทนด้วยเว้นวรรคหรือคำเชื่อม เช่น "**ไม่** เพราะ I/O จริงใช้ IOCP"
- **passive "ถูก" 4 จุด** เปลี่ยนเป็นประโยคที่บอกว่าใครทำ: "ถูกแปลงเป็น struct" → "compiler แปลงให้เป็น struct", "exception ถูก catch" → "state machine catch exception ไว้เอง", "จะถูก rethrow" → "ก็ rethrow"
- **"มัน" แทน it 3 จุด** เรียกชื่อสิ่งนั้นแทน: "มันจะ capture" → "await จะ capture", "มันวิ่งต่อแบบ synchronous" → "ก็วิ่งต่อแบบ synchronous"
- **"ของคุณ" 2 จุด** ละทิ้ง: "method ของคุณ" → "method"
- **ไม้ยมก 4 จุด** เว้นวรรคตามราชบัณฑิตฯ: สั้นๆ → สั้น ๆ, คร่าวๆ → คร่าว ๆ, ชิ้นๆ → ชิ้น ๆ, ซ้ำๆ → ซ้ำ ๆ
- **จุกจิกอื่น ๆ** "บรรทัดเดียว:" → "สรุปบรรทัดเดียว:", "ไลบรารี" → "library" (คำที่ dev ไทยพูดเป็นอังกฤษอยู่แล้ว), ตัด "เลย" ซ้ำใน "(เลยแก้ UI ต่อได้เลย)"

เนื้อหากับโค้ดทุกบรรทัดคงเดิมครับ
