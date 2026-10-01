สั้น ๆ คือ compiler แปลง method ที่ติด `async` เป็น state machine แล้วหั่นโค้ดออกเป็นท่อน ๆ ตามจุด await ครับ ไม่มี magic อะไรในระดับ runtime เป็น callback ธรรมดา

**ตอน compile**
- local variable ทุกตัวกลายเป็น field ของ struct ที่ implement `IAsyncStateMachine` เพื่อให้ค่าอยู่รอดข้ามการ await
- โค้ดแต่ละช่วงระหว่าง await กลายเป็น `case` ใน switch โดยมี field `state` คุมว่าตอนนี้ค้างอยู่ตรงไหน
- method เดิมเหลือแค่โค้ดสร้าง state machine แล้วเรียก `MoveNext()` ครั้งแรก

**ตอนวิ่งไปเจอ await**
- เรียก `GetAwaiter()` จากสิ่งที่ await (Task, ValueTask หรืออะไรก็ได้ที่มี method นี้)
- เช็ก `IsCompleted` ก่อน ถ้าเสร็จอยู่แล้วก็ `GetResult()` แล้ววิ่งต่อบน thread เดิมเลย ไม่มี allocation ไม่มี context switch
- ถ้ายังไม่เสร็จ ก็เซ็ตค่า `state` ไว้ว่าหยุดตรงไหน ลงทะเบียน continuation ผ่าน `OnCompleted` แล้ว return ออกไปทันที thread ว่างไปรับงานอื่นต่อได้
- พอ operation เสร็จ จะมีคนเรียก `MoveNext()` อีกรอบ switch ก็กระโดดไปที่ case ตาม `state` แล้วทำงานต่อจากจุดเดิม

**ใครเรียก MoveNext กลับ** ถ้ามี `SynchronizationContext` อยู่ เช่น UI thread หรือ ASP.NET Framework เดิม จะ post กลับไปรันบน context นั้น ถ้าไม่มีก็ไปโผล่บน thread pool ตรงนี้แหละคือเหตุผลที่ `ConfigureAwait(false)` ใน library code ช่วยทั้งเรื่อง performance และกัน deadlock

**จุดที่เข้าใจผิดกันบ่อย** await ไม่ได้สร้าง thread ใหม่ ระหว่างรอ I/O ไม่มี thread ไหนนั่งรอเลย งานจริงไปอยู่ที่ OS (IOCP บน Windows) พอ I/O เสร็จค่อยดึง thread จาก pool มาทำต่อ

อีกตัวที่อยู่เบื้องหลังคือ `AsyncTaskMethodBuilder` ทำหน้าที่สร้าง Task ที่ return ออกไป แล้ว set result หรือ exception ให้ตอน method จบ เลยเป็นที่มาว่าทำไม exception ใน async method ไม่เด้งออกมาตอนเรียก แต่ไปโผล่ตอน await

ถ้าอยากเห็นโค้ดที่ compiler gen จริง ๆ ลองวางใน sharplab.io แล้วดู decompiled C# ได้ครับ เห็นภาพเร็วดี
