Linter ผ่านสะอาด (จาก 19 จุด เหลือ 0) และ code block ทั้งสองบล็อกตรงกับต้นฉบับทุกตัวอักษร

---

## สรุปสั้น ๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation** compiler จะแปลง method ที่เขียนไว้ให้กลายเป็น **state machine**

### 1. Compiler แปลงเป็น State Machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

compiler แปลงออกมาเป็น struct ที่ implement `IAsyncStateMachine` หน้าตาคร่าว ๆ แบบนี้:

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

**หัวใจคือ:** local variables กลายเป็น fields เพราะ stack หายไปตอน `return` state เลยต้องไปเก็บไว้บน heap

### 2. จุดสำคัญที่คนมักเข้าใจผิด

| เรื่อง | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่สร้าง** I/O จริงใช้ IOCP (OS callback) ไม่มี thread รออยู่เลย |
| `await` บล็อก thread | **ไม่บล็อก** `await` จะ `return` ออกไปเลย thread ว่างไปทำงานอื่นต่อ |
| ทุก `await` มี overhead | **ไม่ใช่ทุกครั้ง** ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer แล้ว) จะวิ่งต่อแบบ synchronous ไม่ alloc อะไรเลย |

State machine เป็น `struct` และอยู่บน stack **จนกว่า** จะเจอ await ที่ยังไม่เสร็จจริง ถึงจะ box ขึ้น heap optimization ตัวนี้ทำให้ fast path แทบไม่มีต้นทุน

### 3. กลับมาที่ไหน? → SynchronizationContext

ตอน `AwaitUnsafeOnCompleted` builder จะ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ตัวปัจจุบันไว้ พอ operation เสร็จก็ post `MoveNext` กลับไปที่นั่น

- **ASP.NET Core / Console**: ไม่มี context → resume บน thread pool thread ใดก็ได้
- **WPF / WinForms**: มี context → resume บน UI thread (เลยแก้ UI ต่อได้เลย)
- `ConfigureAwait(false)`: สั่งว่า "ไม่ต้อง capture" ลด overhead และกัน deadlock ใน library

### 4. Exceptions

state machine จะ catch exception ที่เกิดใน `MoveNext` แล้วส่งเข้า `_builder.SetException(ex)` → เก็บไว้ใน Task → ตอน `GetResult()` ก็ rethrow ด้วย `ExceptionDispatchInfo` ซึ่ง**รักษา stack trace เดิมไว้** (ไม่เหมือน `throw ex;` ที่ทำ stack trace หาย)

---

**บรรทัดเดียว:** compiler หั่น method ออกเป็นชิ้น ๆ ตาม `await` แล้วเย็บกลับเป็น state machine ที่เรียก `MoveNext()` ซ้ำ ๆ แต่ละครั้งทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรอ

---

## แก้อะไรไปบ้าง

**em dash (9 จุด)** — ตัดออกทั้งหมด แทนด้วยเว้นวรรคหรือ `:` ในหัวข้อย่อย ภาษาไทยไม่ใช้เครื่องหมายนี้

**"ถูก + กริยา" แบบ passive (4 จุด)** — เรื่องพวกนี้ไม่ใช่เรื่องร้าย เลยบอกไปเลยว่าใครทำ
- "ถูกแปลงเป็น struct" → "compiler แปลงออกมาเป็น struct"
- "ถึงจะถูก box ขึ้น heap" → "ถึงจะ box ขึ้น heap"
- "exception ถูก catch แล้วส่งเข้า…" → "state machine จะ catch exception … แล้วส่งเข้า…"
- "จะถูก rethrow" → "ก็ rethrow"

**"มัน" แทน it (3 จุด)** — ใส่ชื่อสิ่งนั้นแทน หรือละไป: "มันจะ capture" → "builder จะ capture", "มัน `return` ออกไปเลย" → "`await` จะ `return` ออกไปเลย", "มันวิ่งต่อแบบ synchronous" → "จะวิ่งต่อแบบ synchronous"

**"ของคุณ" (2 จุด)** — ละทิ้ง: "method ของคุณ" → "method ที่เขียนไว้" / "method"

**ไม้ยมกติดคำ (4 จุด)** — "สั้นๆ, คร่าวๆ, ชิ้นๆ, ซ้ำๆ" → เว้นวรรคหน้าหลังตามราชบัณฑิตฯ

**ที่ linter จับไม่ได้**
- ช่องตารางเดิมตอบว่า "**ไม่**" ลอย ๆ เปลี่ยนเป็นตอบรับกับคำถามแต่ละแถว: "**ไม่สร้าง**", "**ไม่บล็อก**", "**ไม่ใช่ทุกครั้ง**" อ่านแล้วรู้ว่าปฏิเสธอะไร โดยไม่ต้องพึ่ง em dash คั่น
- "ไลบรารี" → "library" เพราะ dev ไทยพูดคำนี้เป็นอังกฤษอยู่แล้ว
- เรียงประโยคต่อท้ายใหม่ให้เชื่อมแบบไทย เช่น "state ต้องเก็บไว้บน heap" → "state เลยต้องไปเก็บไว้บน heap", "เป็น optimization ที่ทำให้…" → "optimization ตัวนี้ทำให้…"

โค้ด ชื่อตัวแปร คอมเมนต์ในโค้ด และลำดับเนื้อหา คงไว้เหมือนเดิมทั้งหมด
