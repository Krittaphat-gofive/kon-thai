รีวิวให้แล้วครับ มีสองจุดที่ต้องแก้ก่อนขึ้น production คือ `async void` กับ `catch` ว่าง ที่เหลือเป็นเรื่องรอง

## 1. `async void` ทำให้ exception หลุดไปล้มทั้ง process

`async void` ตัวเรียกจะ await ไม่ได้ ไม่รู้ว่าทำเสร็จหรือยัง และถ้ามี exception หลุดออกมานอก `try` (เช่น `GetSlipAsync` throw ตอนที่โค้ดยังไม่เข้า try ไม่ได้ กรณีนี้ไม่เกิด แต่ pattern นี้อันตรายทั่วไป) จะไปโผล่ที่ `SynchronizationContext` แล้วล้มทั้งแอป

ให้เปลี่ยนเป็น `async Task` และตั้งชื่อลงท้าย `Async` ตามธรรมเนียม ยกเว้นกรณีเดียวที่ `async void` ยอมรับได้คือ event handler

อีกเรื่องที่ตามมา: ถ้าโค้ดนี้วนส่งทีละคนใน loop ตัวเรียกจะ await ไม่ได้ กลายเป็นยิงพร้อมกันหมดทุกคน ทั้ง SMTP connection และ DbContext จะรับไม่ไหว

## 2. `catch` ว่างคือจุดที่หนักที่สุด

ตอนนี้ถ้าส่งอีเมลไม่สำเร็จ จะไม่มีใครรู้เลย ไม่มี log ไม่มีใคร retry พนักงานไม่ได้รับสลิป แล้วมาถามทีหลังว่าทำไมไม่ได้ ทีมก็ไล่ย้อนไม่ได้ว่าพลาดตรงไหน เรื่องเงินเดือนนี่ตามยาก

อย่างน้อยต้อง log พร้อม `employeeId` และตัว exception แล้วตัดสินใจว่าจะ throw ต่อหรือกลืนไว้ ขึ้นอยู่กับว่าใครเรียก
- ตัวเรียกเป็น API ที่ผู้ใช้กดปุ่มส่ง: ให้ throw ต่อ จะได้ตอบกลับว่าไม่สำเร็จ
- เป็น batch job ส่งทั้งบริษัท: log แล้วเก็บรายการที่ fail ไว้ ส่งสรุปท้าย job ว่าใครยังไม่ได้บ้าง จะได้ไม่พังทั้งรอบเพราะอีเมลคนเดียว

ถ้าจะ `catch (Exception)` จริง ๆ ควรแคบลงเป็น exception ที่คาดไว้ เช่น `SmtpException` ตอนนี้มันกลืนทุกอย่างรวมถึง `NullReferenceException` กับ bug ที่เราเขียนผิดเองด้วย

## 3. `slip` อาจเป็น null

ถ้า `GetSlipAsync` หา `employeeId` นั้นไม่เจอแล้วคืน `null` บรรทัดถัดไปจะ `NullReferenceException` แล้ว `catch` ว่างก็กลืนไปอีก กลายเป็นเงียบสองชั้น เช็กก่อนใช้แล้ว log แยกว่า "ไม่พบสลิป" ซึ่งคนละปัญหากับ "ส่งอีเมลไม่ผ่าน"

เรื่องเดียวกันคือ `slip.Email` ที่อาจว่างหรือเป็น null ถ้าพนักงานยังไม่ได้กรอกอีเมล ควรเช็กและ log ให้ชัดว่าเป็นเคสข้อมูลไม่ครบ

## 4. ไม่มี CancellationToken

ถ้าเป็น API ที่ผู้ใช้ปิดหน้าไปแล้ว หรือเป็น background service ที่กำลัง shutdown งานนี้จะยังค้างอยู่ รับ `CancellationToken` แล้วส่งต่อลงไปทั้งสองตัว

## โค้ดที่แก้แล้ว

```csharp
public async Task SendPayslipAsync(int employeeId, CancellationToken ct = default)
{
    var slip = await _payrollService.GetSlipAsync(employeeId, ct);

    if (slip is null)
    {
        _logger.LogWarning("ไม่พบสลิปของพนักงาน {EmployeeId}", employeeId);
        return;
    }

    if (string.IsNullOrWhiteSpace(slip.Email))
    {
        _logger.LogWarning("พนักงาน {EmployeeId} ไม่มีอีเมลในระบบ", employeeId);
        return;
    }

    try
    {
        await _email.SendAsync(slip.Email, "สลิปเงินเดือน", slip.Html, ct);
        _logger.LogInformation("ส่งสลิปให้พนักงาน {EmployeeId} แล้ว", employeeId);
    }
    catch (SmtpException ex)
    {
        _logger.LogError(ex, "ส่งสลิปให้พนักงาน {EmployeeId} ไม่สำเร็จ", employeeId);
        throw;
    }
}
```

สองจุดที่อยากรู้เพิ่มก่อนจะฟันธงเรื่อง throw หรือกลืน: ตัวเรียก `SendPayslip` เป็น controller action หรือ background job ครับ และตอนนี้มีกลไก retry ที่ไหนหรือยัง ถ้ายังไม่มี การส่งสลิปเดือนนั้นพลาดไปเลยจะเป็นปัญหาพอสมควร
