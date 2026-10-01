เกลาแล้วตามนี้ครับ (เนื้อหากับโค้ดเหมือนเดิมทุกจุด ปรับเฉพาะสำนวน):

---

## สรุปสั้นๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation** — compiler เอา method ที่เราเขียนไปแปลงเป็น **state machine** ให้

### 1. Compiler แปลงเป็น State Machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

พอ compile แล้วจะกลายเป็น struct ที่ implement `IAsyncStateMachine` หน้าตาประมาณนี้:

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

**แก่นอยู่ตรงนี้:** local variable ต้องกลายเป็น field เพราะพอ `return` ออกไป stack frame ก็หายไปด้วย state เลยต้องย้ายไปอยู่บน heap แทน

### 2. จุดที่คนมักเข้าใจผิด

| ความเชื่อ | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** — งาน I/O จริงๆ ใช้ IOCP (callback จาก OS) ไม่มี thread ไหนนั่งรอเลย |
| `await` บล็อก thread | **ไม่** — มัน `return` ออกไปเลย ปล่อยให้ thread ไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่** — ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer อยู่แล้ว) มันก็วิ่งต่อแบบ synchronous ไม่ alloc อะไรเพิ่มเลย |

State machine เป็น `struct` ที่นั่งอยู่บน stack ไปเรื่อยๆ ต่อเมื่อเจอ await ที่ยังไม่เสร็จจริงถึงจะโดน box ขึ้น heap — เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุน

### 3. แล้วกลับมาที่ไหน? → SynchronizationContext

ตอนเรียก `AwaitUnsafeOnCompleted` มันจะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ตัวที่ใช้อยู่ ณ ตอนนั้นเก็บไว้ พองานเสร็จก็ post `MoveNext` กลับไปที่เดิม

- **ASP.NET Core / Console** — ไม่มี context → resume บน thread ไหนของ thread pool ก็ได้
- **WPF / WinForms** — มี context → resume บน UI thread (เลยไปแตะ UI ต่อได้เลย)
- `ConfigureAwait(false)` — บอกว่า "ไม่ต้อง capture" ช่วยลด overhead แล้วก็กัน deadlock เวลาเขียน library

### 4. Exceptions

exception ที่เกิดใน `MoveNext` จะโดน catch แล้วส่งต่อให้ `_builder.SetException(ex)` → เก็บไว้ใน Task → พอเรียก `GetResult()` ถึงค่อย rethrow ผ่าน `ExceptionDispatchInfo` — วิธีนี้**stack trace เดิมยังอยู่ครบ** ไม่เหมือน `throw ex;` ที่ทำ stack trace หายเกลี้ยง

---

**สรุปบรรทัดเดียว:** compiler หั่น method เราเป็นชิ้นๆ ตามจุด `await` แล้วเย็บกลับมาเป็น state machine ที่โดนเรียก `MoveNext()` ซ้ำๆ แต่ละรอบก็ทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรออะไรเลย
