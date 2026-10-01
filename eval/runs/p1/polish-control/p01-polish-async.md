เกลาแล้วครับ โค้ดและเนื้อหาคงเดิมทุกอย่าง ปรับเฉพาะสำนวนให้ลื่นขึ้น:

---

## สรุปสั้นๆ

`async/await` ไม่ได้เป็นฟีเจอร์ของ runtime แต่เป็น **compiler transformation** — compiler จะแปลงเมธอดของเราให้กลายเป็น **state machine**

### 1. Compiler แปลงเป็น State Machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

จะถูกแปลงเป็น struct ที่ implement `IAsyncStateMachine` หน้าตาประมาณนี้:

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

**ประเด็นสำคัญคือ** local variable จะกลายเป็น field เพราะพอ `return` ออกไปแล้ว stack frame จะหายไปด้วย state เลยต้องย้ายไปเก็บไว้บน heap แทน

### 2. เรื่องที่คนมักเข้าใจผิด

| ความเชื่อ | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** — งาน I/O จริงๆ ใช้ IOCP (OS callback) ไม่มี thread ไหนนั่งรออยู่เลย |
| `await` บล็อก thread | **ไม่** — มัน `return` ออกไปเลย ปล่อยให้ thread ไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่** — ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer อยู่แล้ว) มันจะวิ่งต่อแบบ synchronous เลย ไม่ alloc อะไรเพิ่ม |

State machine เป็น `struct` และอยู่บน stack ไปเรื่อยๆ **จนกว่า** จะเจอ await ที่ยังทำงานไม่เสร็จจริงๆ ถึงจะโดน box ขึ้น heap — เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุนเลย

### 3. แล้วกลับมาทำงานต่อที่ไหน? → SynchronizationContext

ตอนที่เรียก `AwaitUnsafeOnCompleted` มันจะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ที่ใช้อยู่ตอนนั้นเก็บไว้ พอ operation เสร็จก็จะ post `MoveNext` กลับไปรันที่เดิม

- **ASP.NET Core / Console** — ไม่มี context → resume บน thread pool thread ตัวไหนก็ได้
- **WPF / WinForms** — มี context → resume บน UI thread (เลยอัปเดต UI ต่อได้เลย)
- `ConfigureAwait(false)` — เป็นการบอกว่า "ไม่ต้อง capture นะ" ช่วยลด overhead และกัน deadlock เวลาเขียนไลบรารี

### 4. Exceptions

exception ที่เกิดใน `MoveNext` จะถูก catch ไว้ แล้วส่งต่อไปที่ `_builder.SetException(ex)` → เก็บไว้ใน Task → พอเรียก `GetResult()` ถึงจะถูก rethrow ด้วย `ExceptionDispatchInfo` ซึ่ง**ยังเก็บ stack trace เดิมไว้ครบ** (ต่างจาก `throw ex;` ที่ทำให้ stack trace หายไป)

---

**สรุปบรรทัดเดียว:** compiler หั่นเมธอดของเราออกเป็นท่อนๆ ตามจุดที่มี `await` แล้วเย็บกลับมาเป็น state machine ที่ถูกเรียก `MoveNext()` ซ้ำๆ — แต่ละครั้งก็ทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread ไหนนั่งรอเลย

---

จุดที่ปรับหลักๆ:
- เปลี่ยน "method ของคุณ" → "เมธอดของเรา" ซึ่งเป็นสรรพนามที่คนไทยใช้เขียนบทความเทคนิคมากกว่า
- เพิ่มคำเชื่อม/คำลงท้ายที่คนไทยใช้จริง ("เลย", "อยู่แล้ว", "ไปเรื่อยๆ", "นะ") แทนประโยคห้วนๆ แบบแปลตรงตัว
- หัวตาราง "เรื่อง" → "ความเชื่อ" ให้คู่กับ "ความจริง"
- "ไม่เหมือน `throw ex;`" → "ต่างจาก `throw ex;`" เป็นภาษาเขียนมากกว่า
- หัวข้อ 3 เติมบริบทให้เป็นคำถามเต็มประโยค แทน "กลับมาที่ไหน?" ที่ห้วนเกินไป
