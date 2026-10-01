## สรุปสั้น ๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation**: compiler แปลง method นั้นเป็น **state machine**

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

**หัวใจคือ:** local variables กลายเป็น fields เพราะ stack หายไปตอน `return` จึงต้องเก็บ state ไว้บน heap

### 2. จุดสำคัญที่คนมักเข้าใจผิด

| เรื่อง | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** I/O จริงใช้ IOCP (OS callback) ไม่มี thread นั่งรออยู่เลย |
| `await` บล็อก thread | **ไม่** await `return` ออกไปเลย thread ไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่** ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer แล้ว) state machine วิ่งต่อแบบ synchronous ไม่ alloc อะไรเลย |

State machine เป็น `struct` และอยู่บน stack **จนกว่า** จะเจอ await ที่ยังไม่เสร็จจริง ถึงจะ box ขึ้น heap ตรงนี้เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุน

### 3. กลับมาที่ไหน? → SynchronizationContext

ตอน `AwaitUnsafeOnCompleted` จะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ปัจจุบันเอาไว้ พอ operation เสร็จก็ post `MoveNext` กลับไปที่นั่น

- **ASP.NET Core / Console**: ไม่มี context → resume บน thread pool thread ใดก็ได้
- **WPF / WinForms**: มี context → resume บน UI thread (เลยแก้ UI ต่อได้เลย)
- `ConfigureAwait(false)`: สั่งว่า "ไม่ต้อง capture" ลด overhead และกัน deadlock ใน library

### 4. Exceptions

state machine จะ catch exception ใน `MoveNext` แล้วส่งเข้า `_builder.SetException(ex)` → เก็บไว้ใน Task → ตอน `GetResult()` จะ rethrow ด้วย `ExceptionDispatchInfo` ซึ่ง**รักษา stack trace เดิมไว้** (ไม่เหมือน `throw ex;` ที่ทำ stack trace หาย)

---

**บรรทัดเดียว:** compiler หั่น method นั้นเป็นชิ้น ๆ ตาม `await` แล้วเย็บกลับเป็น state machine ที่เรียก `MoveNext()` ซ้ำ ๆ แต่ละครั้งทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรอ

## สิ่งที่แก้

- ตัด em dash ทั้ง 11 จุด เปลี่ยนเป็นเว้นวรรค หรือ : ในหัวข้อย่อย
- เลิกใช้ "ถูก" กับเรื่องปกติ บอกว่าใครทำแทน เช่น "ถูกแปลงเป็น struct" เป็น "compiler แปลงให้เป็น struct"
- เปลี่ยน "มัน" เป็นชื่อสิ่งนั้น เช่น await, state machine
- ตัด "ของคุณ" ที่แปลมาจาก your เหลือ "method นั้น"
- เว้นวรรคหน้าและหลังไม้ยมก และเปลี่ยน "ไลบรารี" เป็น library ตามที่ dev พูดกันจริง
