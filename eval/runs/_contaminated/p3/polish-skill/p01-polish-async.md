เกลาเสร็จแล้วครับ โค้ดกับเนื้อหาคงเดิมทุกตัวอักษร

---

## สรุปสั้น ๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation** คือ compiler แปลง method นี้เป็น **state machine**

### 1. Compiler แปลงเป็น State Machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

compiler จะแปลงเป็น struct ที่ implement `IAsyncStateMachine` คร่าว ๆ แบบนี้

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

**หัวใจคือ:** local variables กลายเป็น fields เพราะ stack หายไปตอน `return` เลยต้องเก็บ state ไว้บน heap

### 2. จุดสำคัญที่คนมักเข้าใจผิด

| เรื่อง | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** I/O จริงใช้ IOCP (OS callback) ไม่มี thread รออยู่เลย |
| `await` บล็อก thread | **ไม่** method `return` ออกไปเลย thread ไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่** ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer แล้ว) state machine วิ่งต่อแบบ synchronous ไม่ alloc อะไรเลย |

State machine เป็น `struct` และอยู่บน stack **จนกว่า** จะเจอ await ที่ยังไม่เสร็จจริง ถึงจะ box ขึ้น heap ตรงนี้เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุน

### 3. กลับมาที่ไหน? → SynchronizationContext

ตอนเรียก `AwaitUnsafeOnCompleted` จะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ปัจจุบันไว้ พอ operation เสร็จก็ post `MoveNext` กลับไปที่นั่น

- **ASP.NET Core / Console**: ไม่มี context → resume บน thread pool thread ใดก็ได้
- **WPF / WinForms**: มี context → resume บน UI thread (เลยแก้ UI ต่อได้เลย)
- `ConfigureAwait(false)`: สั่งว่า "ไม่ต้อง capture" ลด overhead และกัน deadlock ในไลบรารี

### 4. Exceptions

`MoveNext` จะ catch exception ไว้ แล้วส่งเข้า `_builder.SetException(ex)` → เก็บไว้ใน Task → ตอนเรียก `GetResult()` จะ rethrow ด้วย `ExceptionDispatchInfo` ซึ่ง**รักษา stack trace เดิมไว้** (ไม่เหมือน `throw ex;` ที่ทำ stack trace หาย)

---

**บรรทัดเดียว:** compiler หั่น method เป็นชิ้น ๆ ตาม `await` แล้วเย็บกลับเป็น state machine ที่เรียก `MoveNext()` ซ้ำ ๆ แต่ละครั้งทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรอ

---

## สิ่งที่แก้

- เอา em dash ออกทั้ง 10 จุด เปลี่ยนเป็นเว้นวรรคหรือ : ในหัวข้อย่อย
- "ถูกแปลงเป็น struct" เป็น "compiler จะแปลงเป็น struct" และ "จะถูก rethrow" เป็น "จะ rethrow" ยกตัวที่ทำขึ้นเป็นประธาน
- "มัน return ออกไปเลย" เป็น "method return ออกไปเลย" และ "มันวิ่งต่อ" เป็น "state machine วิ่งต่อ"
- ตัด "ของคุณ" ออกสองจุด เหลือ "method นี้" กับ "หั่น method"
- ไม้ยมกเว้นวรรคตามราชบัณฑิตฯ: สั้น ๆ, คร่าว ๆ, ชิ้น ๆ, ซ้ำ ๆ

รันlinter ซ้ำแล้วเหลือ 0 จุดครับ
