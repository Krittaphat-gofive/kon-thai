รีวิวแล้วมีสองจุดที่ต้องแก้ก่อนขึ้น production ครับ คือ `async void` กับ `catch` ที่กลืน exception ทิ้ง สองอย่างนี้มารวมกันแล้วอันตรายกว่าที่เห็น เพราะเวลาส่งสลิปไม่สำเร็จ จะไม่มีใครรู้เลยว่าพนักงานคนไหนไม่ได้รับ

## 1. async void ทำให้ caller คุมอะไรไม่ได้

compiler แปลง method นี้เป็น state machine ที่ไม่คืน `Task` ให้ใครถือไว้ ผลคือ

- caller await ไม่ได้ ไม่รู้ว่าส่งเสร็จหรือยัง ถ้าเป็น API controller ก็ตอบ 200 กลับไปตั้งแต่อีเมลยังไม่ออกจากเครื่อง
- exception ที่หลุดนอก `try` เช่น `_payrollService` เป็น null จะเด้งขึ้นไปที่ thread pool ตรง ๆ แล้ว process ตายทั้งตัว ไม่มี catch ที่ไหนรับได้
- เขียน unit test ไม่ได้ เพราะ test รอให้งานจบไม่ได้

เปลี่ยนเป็น `async Task` แล้วให้ caller await เป็นอันจบ ชื่อ method ก็ควรเติม `Async` ตามที่ใช้กันใน codebase

ข้อยกเว้นเดียวของ `async void` คือ event handler จริง ๆ ถ้าตรงนี้ตั้งใจยิงแล้วไม่รอผล อย่าปล่อยลอยแบบนี้ ให้โยนเข้า background job อย่าง Hangfire หรือ queue แทน จะได้มี retry กับ dashboard ให้ดูด้วย

## 2. catch เปล่า ๆ ทำให้ปัญหาหายเงียบ

ตรงนี้หนักกว่า `async void` อีก เพราะ SMTP ล่ม อีเมลผิด format หรือ `slip` เป็น null ก็เงียบเหมือนกันหมด สิ้นเดือนถึงจะมีคนทักมาว่าไม่ได้สลิป แล้วตอนนั้นไม่มี log ให้ไล่เลยว่าเกิดอะไรขึ้น

เรื่องเงินเดือนยิ่งต้องมีร่องรอยไว้ตรวจย้อนหลัง อย่างน้อยต้อง log ว่าพังตอนไหน employee id อะไร แล้ว rethrow ให้ชั้นบนตัดสินใจต่อ

ระวังตอน log ด้วย อย่าใส่ `slip.Html` หรือยอดเงินลงไป เพราะเป็นข้อมูลส่วนบุคคล log แค่ employee id พอ

## 3. ไม่ได้เช็ก slip ว่าเป็น null ไหม

ถ้า `GetSlipAsync` หา employee ไม่เจอแล้วคืน `null` บรรทัด `slip.Email` จะพังทันที ตอนนี้ catch เปล่ารับไว้พอดีเลยไม่เห็นปัญหา แต่ถ้าแก้ catch แล้วจะโผล่มาทันที

## โค้ดที่แก้แล้ว

```csharp
public async Task SendPayslipAsync(int employeeId)
{
    var slip = await _payrollService.GetSlipAsync(employeeId);
    if (slip is null)
    {
        _logger.LogWarning("ไม่พบสลิปของ employee {EmployeeId}", employeeId);
        return;
    }

    try
    {
        await _email.SendAsync(slip.Email, "สลิปเงินเดือน", slip.Html);
        _logger.LogInformation("ส่งสลิปให้ employee {EmployeeId} สำเร็จ", employeeId);
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "ส่งสลิปให้ employee {EmployeeId} ไม่สำเร็จ", employeeId);
        throw;
    }
}
```

อีกเรื่องที่อยากถามคือ method นี้วนเรียกทีละคนตอนรันรอบเงินเดือนหรือเปล่า ถ้าใช่ การ `throw` ออกไปจะทำให้คนที่เหลือไม่ได้สลิป กรณีนั้นควรให้ loop ข้างนอกจับ error รายคน เก็บ id ที่พังไว้เป็น list แล้วสรุปตอนจบว่าใครส่งไม่ผ่านบ้าง จะได้ส่งซ้ำเฉพาะคนที่พลาด

ถ้าส่งโค้ดฝั่งที่เรียก method นี้มาให้ดูด้วย เดี๋ยวช่วยดูเรื่อง retry กับ transaction ให้ครับ
