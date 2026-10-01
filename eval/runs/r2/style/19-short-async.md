สรุปสั้น ๆ คือ compiler แปลง method ที่ติด `async` ให้กลายเป็น state machine แล้วทุกจุดที่ `await` ก็คือจุดพักที่ method return กลับไปหา caller แล้วค่อยกลับมาทำต่อตอนงานเสร็จครับ

**ตอน compile**

- method นี้ถูกแปลงเป็น struct ที่ implement `IAsyncStateMachine` มี field `state` เก็บว่าพักอยู่ตรงไหน
- ตัวแปร local ที่ต้องอยู่ข้าม `await` กลายเป็น field ของ struct นั้น เพราะอยู่บน stack ต่อไม่ได้
- มี `AsyncTaskMethodBuilder` ทำหน้าที่สร้าง `Task` ส่งกลับให้ caller ตั้งแต่ยังไม่มีผลลัพธ์

**ตอนรัน**

พอ `MoveNext()` วิ่งมาเจอ `await` จะเรียก `GetAwaiter()` ก่อน แล้วเช็ก `IsCompleted`

- ถ้าเสร็จแล้ว ก็ทำต่อแบบ synchronous เลย ไม่มีการสลับ thread ไม่มี allocation เพิ่ม ซึ่งเป็น fast path ที่เจอบ่อยกว่าที่คิด เช่นอ่านจาก cache
- ถ้ายังไม่เสร็จ ก็ลงทะเบียน continuation ผ่าน `OnCompleted` แล้ว return ออกไปทันที caller ได้ `Task` ที่ยังไม่เสร็จกลับไปทำอย่างอื่นต่อ

พองานเสร็จ callback จะเรียก `MoveNext()` อีกรอบ ค่า `state` บอกว่าต้องกระโดดไปทำต่อบรรทัดไหน ผลลัพธ์ดึงมาจาก `GetAwaiter().GetResult()` ซึ่งเป็นจุดเดียวกับที่ exception เด้งออกมา เลยเขียน try/catch คร่อม `await` ได้ตามปกติ

**เรื่อง thread**

จุดที่คนเข้าใจผิดบ่อยสุดคือคิดว่า `await` สร้าง thread ใหม่ ความจริงคือไม่มี thread นั่งรอ I/O งานจริงไปอยู่ที่ OS (บน Windows คือ IOCP) พอเสร็จค่อยมีคนจาก thread pool หยิบ continuation ไปทำต่อ

ส่วน `ConfigureAwait(false)` เกี่ยวกับตรงนี้ ปกติ continuation จะกลับไปทำบน `SynchronizationContext` เดิม เช่น UI thread การใส่ `false` คือบอกว่าไม่ต้องกลับ ทำบน thread pool ต่อได้เลย ใน library code ควรใส่ แต่ใน ASP.NET Core ไม่มี context อยู่แล้ว ไม่ใส่ก็ไม่ต่างกัน

อยากให้แกะ IL หรือดูโค้ดที่ compiler gen ออกมาจริง ๆ ไหมครับ จะได้เห็นหน้าตา state machine ชัดกว่านี้
