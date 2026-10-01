มีสองจุดที่ต้องแก้ก่อนขึ้น production คือ `async void` กับ `catch` เปล่าครับ ที่เหลือเป็นเรื่องรองลงมา

## 1. `async void` ทำให้ caller ควบคุมอะไรไม่ได้เลย

เมธอดที่คืน `void` แบบนี้ caller จะ await ไม่ได้ เลยไม่รู้ว่าส่งเสร็จหรือยัง และไม่รู้ว่าสำเร็จไหม ถ้าโค้ดฝั่งเรียกวนลูปส่งให้พนักงานทั้งบริษัท ก็จะยิงออกไปพร้อมกันทั้งหมดโดยไม่มีใครคุมจำนวน แล้วถ้า process จบก่อน งานที่ค้างอยู่ก็หายไปเงียบ ๆ

อีกเรื่องคือ exception ที่หลุดจาก `async void` จะเด้งขึ้นไปที่ SynchronizationContext แล้วทำให้ process ตายทั้งตัว ไม่ใช่แค่ throw กลับไปหา caller เคสนี้ try/catch คลุมทั้งบอดี้ไว้ก็จริง แต่เป็นการพึ่งโชค ไม่ใช่ดีไซน์

กฎเหล็กคือ `async void` ใช้กับ event handler เท่านั้น นอกนั้นคืน `Task` หมด

## 2. `catch` เปล่า อันตรายที่สุดในบล็อกนี้

ตรงนี้คือสลิปเงินเดือน ถ้าส่งไม่ออกแล้วไม่มีใครรู้ สิ่งที่จะเกิดคือ HR คิดว่าส่งครบแล้ว แต่พนักงานไม่ได้รับ และไม่มี log ให้ไล่ย้อนหลังด้วย กว่าจะรู้ตัวก็ตอนมีคนเดินมาถาม

ที่แย่กว่านั้นคือ `catch (Exception)` กลืนทุกอย่าง รวมถึง `NullReferenceException` ที่เกิดจากบั๊กในโค้ดเราเอง อย่างกรณี `GetSlipAsync` คืน `null` มาเพราะหา employeeId ไม่เจอ แล้วบรรทัดถัดไปอ่าน `slip.Email` ก็พัง แต่ catch กลืนไปหมด กลายเป็นว่าบั๊กซ่อนตัวอยู่ได้นาน

## 3. ไม่ได้เช็ก null และไม่ได้เช็กว่ามีอีเมลจริงไหม

พนักงานที่ยังไม่ได้กรอกอีเมล หรือ id ที่ไม่มีในระบบ ควรแยกออกมาเป็นอีกเคสหนึ่ง ไม่ใช่ปล่อยให้ไปพังที่ชั้นส่งเมล เพราะสองกรณีนี้ต้องการการแก้ต่างกัน

## 4. เรื่องรอง

- ไม่มี `CancellationToken` ส่งต่อ พอ job รันยาวแล้วอยากยกเลิก ก็ทำไม่ได้
- ชื่อเมธอดควรลงท้าย `Async` ตาม convention ของ .NET
- subject hardcode ภาษาไทย ถ้ามีพนักงานต่างชาติค่อยคิดเรื่อง template ทีหลังได้
- เวลา log ระวังอย่า log `slip.Html` หรือตัวเลขเงินเดือนลงไป ให้ log แค่ employeeId พอ ข้อมูลพวกนี้ไม่ควรไปโผล่ใน log file ที่คนเข้าถึงได้กว้างกว่า

## เขียนใหม่

```csharp
public async Task<bool> SendPayslipAsync(int employeeId, CancellationToken ct = default)
{
    var slip = await _payrollService.GetSlipAsync(employeeId, ct);

    if (slip is null)
    {
        _logger.LogWarning("ไม่พบสลิปของพนักงาน {EmployeeId}", employeeId);
        return false;
    }

    if (string.IsNullOrWhiteSpace(slip.Email))
    {
        _logger.LogWarning("พนักงาน {EmployeeId} ยังไม่มีอีเมลในระบบ", employeeId);
        return false;
    }

    try
    {
        await _email.SendAsync(slip.Email, "สลิปเงินเดือน", slip.Html, ct);
        _logger.LogInformation("ส่งสลิปให้พนักงาน {EmployeeId} สำเร็จ", employeeId);
        return true;
    }
    catch (SmtpException ex)
    {
        _logger.LogError(ex, "ส่งสลิปให้พนักงาน {EmployeeId} ไม่สำเร็จ", employeeId);
        return false;
    }
}
```

จุดที่เปลี่ยน: `GetSlipAsync` ไม่อยู่ใน try แล้ว ถ้าชั้น payroll พังก็ให้ exception เด้งขึ้นไป เพราะแปลว่าระบบมีปัญหาจริง ไม่ใช่แค่ส่งเมลไม่ผ่าน ส่วน catch จับเฉพาะ `SmtpException` ที่เป็นความผิดพลาดที่คาดไว้ บั๊กอื่น ๆ จะไม่โดนกลืน

## ที่อยากถามต่อ

ฝั่ง caller เรียกยังไงครับ ถ้าเป็นการวนส่งทั้งงวด ผมแนะนำให้เก็บสถานะการส่งลง DB ด้วย เพราะงานเกี่ยวกับเงินเดือนต้องตอบได้ว่าใครได้รับแล้วบ้าง และกันการส่งซ้ำตอนรันใหม่ ถ้าสนใจเดี๋ยวผมร่างให้ดูครับ
