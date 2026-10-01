เกลาให้แล้วครับ โค้ดกับเนื้อหาคงเดิมทุกตัว แก้เฉพาะสำนวน

-----

## สรุปสั้น ๆ

`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **compiler transformation** คือ compiler แปลง method ที่เราเขียนให้กลายเป็น **state machine**

### 1. compiler แปลงเป็น state machine

```csharp
async Task<int> GetDataAsync() {
    var a = await FetchAsync();   // จุดตัดที่ 1
    return a + 1;
}
```

compiler จะแปลงเป็น struct ที่ implement `IAsyncStateMachine` หน้าตาคร่าว ๆ ประมาณนี้:

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

**หัวใจอยู่ตรงนี้:** local variable กลายเป็น field เพราะ stack หายไปตั้งแต่ตอน `return` แล้ว state เลยต้องย้ายไปเก็บบน heap

### 2. จุดที่คนมักเข้าใจผิด

| เรื่อง | ความจริง |
|---|---|
| `async` สร้าง thread ใหม่ | **ไม่** งาน I/O จริง ๆ ใช้ IOCP (OS callback) ไม่มี thread นั่งรออยู่เลย |
| `await` บล็อก thread | **ไม่** เพราะ `return` ออกไปเลย thread ว่างไปทำงานอื่นต่อได้ |
| ทุก `await` มี overhead | **ไม่** ถ้า `IsCompleted == true` (เช่น data อยู่ใน buffer แล้ว) ก็วิ่งต่อแบบ synchronous ไม่ alloc อะไรเลย |

state machine เป็น `struct` และอยู่บน stack ไปเรื่อย ๆ **จนกว่า** จะเจอ await ที่ยังไม่เสร็จจริง ถึงจะ box ขึ้น heap เป็น optimization ที่ทำให้ fast path แทบไม่มีต้นทุน

### 3. กลับมาทำงานต่อที่ไหน → SynchronizationContext

ตอนเรียก `AwaitUnsafeOnCompleted` จะมีการ **capture** `SynchronizationContext` (หรือ `TaskScheduler`) ตัวปัจจุบันเก็บไว้ พอ operation เสร็จก็ post `MoveNext` กลับไปที่เดิม

- **ASP.NET Core / Console** ไม่มี context จึง resume บน thread pool thread ตัวไหนก็ได้
- **WPF / WinForms** มี context จึง resume บน UI thread (เลยแก้ UI ต่อได้เลย)
- `ConfigureAwait(false)` สั่งว่า "ไม่ต้อง capture" ช่วยลด overhead และกัน deadlock ในไลบรารี

### 4. Exceptions

`MoveNext` มี try/catch ครอบอยู่ เจอ exception เมื่อไหร่ก็ส่งเข้า `_builder.SetException(ex)` → ไปเก็บไว้ใน Task → พอเรียก `GetResult()` ก็ throw ซ้ำด้วย `ExceptionDispatchInfo` ซึ่ง**รักษา stack trace เดิมไว้ครบ** (ต่างจาก `throw ex;` ที่ทำ stack trace หาย)

---

**สรุปบรรทัดเดียว:** compiler หั่น method ที่เราเขียนเป็นชิ้น ๆ ตาม `await` แล้วเย็บกลับเป็น state machine ที่เรียก `MoveNext()` ซ้ำ ๆ แต่ละรอบทำงานต่อจากจุดที่ค้างไว้ โดยไม่ต้องมี thread นั่งรอ

-----

สิ่งที่แก้: ตัด em dash ออกทั้งหมดแล้วใช้คำเชื่อมแทน, เว้นวรรคไม้ยมก (สั้น ๆ / คร่าว ๆ / ซ้ำ ๆ), เปลี่ยน "ถูกแปลง / ถูก box / ถูก catch / ถูก rethrow" เป็นรูปที่มีคนทำหรือรูปกริยาตรง, เปลี่ยน "method ของคุณ" เป็น "method ที่เราเขียน", และตัด "มัน" ที่ใช้แทน it ออกครับ
