## สรุปสั้นที่สุด
`async/await` ไม่ใช่ feature ของ runtime แต่เป็น **การแปลงโค้ดตอน compile** — compiler ตัดเมธอดออกเป็นชิ้นๆ ตามจุด `await` แล้วประกอบใหม่เป็น **state machine** ที่เรียกตัวเองซ้ำได้

## สิ่งที่ compiler สร้าง

โค้ดที่เราเขียน:

```csharp
async Task<int> GetAsync()
{
    var data = await httpClient.GetStringAsync(url);  // จุดตัด
    return data.Length;
}
```

ถูกแปลงเป็นประมาณนี้ (ย่อมาก):

```csharp
struct StateMachine : IAsyncStateMachine   // struct ใน Release, class ใน Debug
{
    public int _state;                      // -1 = ยังไม่เริ่ม/จบแล้ว, 0 = รอ await ตัวแรก
    public AsyncTaskMethodBuilder<int> _builder;
    public string _data;                    // local variable กลายเป็น field
    private TaskAwaiter<string> _awaiter;

    public void MoveNext()
    {
        switch (_state)
        {
            case -1:
                _awaiter = httpClient.GetStringAsync(url).GetAwaiter();
                if (!_awaiter.IsCompleted)           // ยังไม่เสร็จ → ยอมแพ้ชั่วคราว
                {
                    _state = 0;
                    _builder.AwaitUnsafeOnCompleted(ref _awaiter, ref this);
                    return;                          // คืน control ให้ caller ทันที
                }
                goto case 0;                         // เสร็จแล้ว → วิ่งต่อเลย ไม่ yield
            case 0:
                _data = _awaiter.GetResult();        // ดึงผล หรือ rethrow exception
                _builder.SetResult(_data.Length);
                return;
        }
    }
}
```

ส่วน `GetAsync()` ตัวจริงเหลือแค่: สร้าง state machine → `builder.Start(ref sm)` (เรียก `MoveNext()` ครั้งแรก **แบบ synchronous บน thread เดิม**) → `return builder.Task`

## กลไกตอน await

1. **`GetAwaiter()`** — `await` เป็น *pattern-based* ไม่ผูกกับ `Task` อะไรก็ awaitable ได้ขอแค่มี `GetAwaiter()` ที่คืน type ซึ่งมี `IsCompleted`, `GetResult()` และ implement `INotifyCompletion`
2. **Fast path** — ถ้า `IsCompleted == true` (เช่น cache hit, `Task.FromResult`) จะไม่มีการ yield ไม่มี allocation เลย วิ่งต่อเหมือนโค้ด sync
3. **Slow path** — state machine ที่เป็น struct จะถูก **box ขึ้น heap** ครั้งเดียวตรงนี้ แล้วลงทะเบียน `MoveNext` เป็น continuation กับ awaiter จากนั้น return ออกไป → caller ได้ `Task` ที่ยังไม่เสร็จ **thread ถูกปล่อยคืน ไม่มี thread ใดนั่งรอ**
4. **ตอนงานเสร็จ** — awaiter เรียก continuation → `MoveNext()` ถูกเรียกอีกครั้ง → `switch` กระโดดกลับไปจุดที่ค้างไว้

## จุดที่คนมักเข้าใจผิด

- **async ≠ thread ใหม่** งาน I/O จริงๆ รออยู่ที่ OS (IOCP) ไม่มี thread ไหนถูกใช้ระหว่างรอ ส่วน `Task.Run` ต่างหากที่ยืม thread จาก thread pool
- **Context capture** — ตอนลงทะเบียน continuation awaiter จะจำ `SynchronizationContext` (หรือ `TaskScheduler`) ปัจจุบันไว้ แล้ว post `MoveNext` กลับไปที่เดิม นี่คือเหตุผลที่ UI code กลับมาอยู่บน UI thread ได้เอง และเป็นที่มาของ deadlock เวลาใช้ `.Result` บน context ที่มี thread เดียว — `ConfigureAwait(false)` คือการบอกว่าไม่ต้อง capture
- **Exception** — ไม่ถูกโยนออกจากเมธอดตรงๆ แต่ถูกจับใส่ `Task` ผ่าน `builder.SetException()` แล้วตอน `GetResult()` ค่อย rethrow โดยใช้ `ExceptionDispatchInfo` เพื่อรักษา stack trace เดิม
- **ต้นทุน** — ทุกครั้งที่ไปถึง slow path จะเสีย allocation (boxed state machine + `Task`) ถ้าเป็น hot path ที่มักเสร็จแบบ sync ให้ใช้ `ValueTask` และ `[AsyncMethodBuilder(typeof(PoolingAsyncValueTaskMethodBuilder))]` เพื่อ pool ตัว state machine กลับมาใช้ซ้ำ
