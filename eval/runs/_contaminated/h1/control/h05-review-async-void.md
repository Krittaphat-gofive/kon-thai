รีวิวให้แล้วครับ โค้ดนี้มีปัญหาใหญ่สองจุดที่ต้องแก้ก่อนขึ้น production คือ `async void` กับ catch ว่าง พอสองอย่างนี้มาด้วยกัน ผลคือสลิปเงินเดือนส่งไม่ถึงพนักงานแล้วไม่มีใครรู้เลยสักคน

## ปัญหาเรียงตามความร้ายแรง

**1. `async void`**

ตัวนี้ร้ายแรงสุด เพราะ

- caller `await` ไม่ได้ ไม่รู้ว่างานเสร็จหรือยัง ถ้าวนลูปส่งพนักงาน 500 คน จะยิงพร้อมกันหมดโดยไม่มีใครคุม
- ถ้ามี exception หลุดออกมานอก try (เช่น `_payrollService` เป็น null) จะไปโผล่ที่ `SynchronizationContext` แล้ว crash ทั้ง process ไม่ใช่แค่ fail request เดียว
- unit test รอผลไม่ได้

เปลี่ยนเป็น `async Task` `async void` ใช้ได้ที่เดียวคือ event handler

**2. catch ว่าง**

กลืน exception ทิ้งหมดเลย ทั้ง SMTP ล่ม ทั้ง bug ในโค้ดเอง ทั้ง `NullReferenceException` สิ้นเดือนพนักงานโทรมาถามว่าสลิปอยู่ไหน ไล่ log ก็ไม่เจออะไร

อย่างน้อยที่สุดต้อง log พร้อม `employeeId` และบอก caller ว่าสำเร็จหรือไม่

**3. `catch (Exception)` กว้างเกินไป**

จับ `OperationCanceledException` ด้วย ตอน shutdown app จะกลายเป็นว่า "ส่งไม่สำเร็จ" ทั้งที่แค่โดนยกเลิก แล้วก็จับ `OutOfMemoryException` กับ `StackOverflow`-class ที่ไม่ควรกลืนอยู่แล้ว ควรระบุ exception ที่คาดไว้จริง ๆ หรือใช้ exception filter

**4. ไม่เช็ก null**

`GetSlipAsync` หา employee ไม่เจอก็น่าจะคืน null แล้ว `slip.Email` พังทันที แล้ว catch ว่างก็กลืนไปอีก กลายเป็น bug ที่มองไม่เห็น

`slip.Email` เองก็ด้วย พนักงานบางคนอาจยังไม่ได้กรอกอีเมลในระบบ

**5. ไม่มี CancellationToken**

งานที่คุยกับ external service ควรรับ token เสมอ ไม่งั้นตอน app shutdown หรือ request timeout จะค้างรอ SMTP ต่อไป

**6. ชื่อ method ไม่ลงท้าย Async**

ตามแนวทาง .NET method ที่คืน Task ควรชื่อ `SendPayslipAsync`

**7. เรื่องที่ควรคิดต่อ (ไม่ใช่บั๊กแต่สำคัญกับงานเงินเดือน)**

- **audit trail**: ต้องบันทึกว่าส่งสลิปงวดไหน ให้ใคร เมื่อไร สำเร็จไหม เวลา HR ถามจะตอบได้
- **PII**: ห้าม log `slip.Html` หรือเนื้อหาสลิปลง log เด็ดขาด เพราะมีข้อมูลเงินเดือน log ส่วนใหญ่อ่านได้กันทั้งทีม
- **retry**: อีเมลล้มชั่วคราวเป็นเรื่องปกติ ควรมี retry แบบ backoff หรือโยนเข้า queue แทนการส่งตรง
- **idempotency**: ถ้ามีคนกดส่งซ้ำ ควรกันไม่ให้พนักงานได้สลิปงวดเดียวกันสองฉบับ
- subject hardcode ไว้ ถ้าต้องรองรับพนักงานต่างชาติจะแก้ลำบาก

## โค้ดที่แก้แล้ว

```csharp
public async Task<bool> SendPayslipAsync(
    int employeeId,
    CancellationToken cancellationToken = default)
{
    var slip = await _payrollService.GetSlipAsync(employeeId, cancellationToken);

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
        await _email.SendAsync(slip.Email, PayslipSubject, slip.Html, cancellationToken);
        _logger.LogInformation("ส่งสลิปงวด {Period} ให้พนักงาน {EmployeeId} สำเร็จ",
            slip.Period, employeeId);
        return true;
    }
    catch (Exception ex) when (ex is SmtpException or HttpRequestException or TimeoutException)
    {
        // ปล่อย OperationCanceledException ผ่านไป เพราะเป็นการยกเลิกตั้งใจ ไม่ใช่ความล้มเหลว
        _logger.LogError(ex, "ส่งสลิปให้พนักงาน {EmployeeId} ไม่สำเร็จ", employeeId);
        return false;
    }
}
```

จุดที่เปลี่ยนคือ ย้าย validation ออกมานอก try ให้ bug ในโค้ดเราเองโผล่ขึ้นมา ไม่ไปปนกับ error ของ external service แล้วเหลือใน try แค่ตัวที่ล้มได้จริงจากปัจจัยภายนอก

ถ้าบอกได้ว่าเรียก method นี้จากไหน (controller, background job, หรือ loop ส่งทีละคน) เดี๋ยวดูเรื่อง retry กับการคุมจำนวนที่ยิงพร้อมกันให้ต่อครับ
