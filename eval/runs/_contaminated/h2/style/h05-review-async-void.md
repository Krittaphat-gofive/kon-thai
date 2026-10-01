รีวิวให้แล้วครับ โค้ดชุดนี้มีปัญหาใหญ่ 2 จุดที่ต้องแก้ก่อนขึ้น production คือ `async void` กับ catch ว่าง ส่วนที่เหลือเป็นเรื่องความทนทานกับ PDPA

## 1. `async void` ทำให้ exception หลุดไปล้ม process

`async void` ทำให้ caller await ไม่ได้ และไม่รู้ว่าส่งสำเร็จหรือไม่ แต่ที่อันตรายกว่านั้นคือถ้ามี exception หลุดออกนอก try (เช่น `_payrollService` เป็น null หรือ `_email.SendAsync` throw ตอน synchronous part) runtime จะโยนขึ้น thread pool แล้วทำให้ทั้ง process ตาย ไม่ใช่แค่ request เดียว

เปลี่ยนเป็น `async Task` เสมอ ยกเว้นกรณีเดียวคือเป็น event handler จริง ๆ

ถ้าตั้งใจเขียนแบบ fire-and-forget เพราะไม่อยากให้ผู้ใช้รอ อย่าใช้ `async void` ให้โยนงานเข้า background queue แทน เช่น Hangfire หรือ `IHostedService` + `Channel` ซึ่งจะได้ retry กับ monitoring มาด้วย

## 2. catch ว่างกลืน error หมด

จุดนี้หนักกว่า `async void` อีกในแง่ธุรกิจ เพราะเรื่องสลิปเงินเดือนคือพนักงานไม่ได้รับ ก็ไม่มีใครรู้ จนกว่าจะมีคนเดินมาถามว่าทำไมสลิปไม่มา แล้วตอนนั้นไม่มี log ให้ไล่ด้วย

อย่างน้อยต้อง log พร้อม `employeeId` และคืนสถานะให้ caller รู้ว่าสำเร็จหรือไม่

ข้อควรระวังตอน log: อย่า log `slip.Email` หรือตัวเลขเงินเดือนลงไปตรง ๆ ใช้ `employeeId` อ้างอิงพอ

## 3. `slip` อาจเป็น null

ถ้า `GetSlipAsync` หา employeeId ไม่เจอแล้วคืน null บรรทัด `slip.Email` จะโยน `NullReferenceException` ซึ่งโดน catch ว่างกลืนไปอีกที กลายเป็นเงียบสองชั้น ควรเช็กทั้ง `slip` และ `slip.Email` แยกกัน เพราะสองเคสนี้คนละปัญหา (ไม่มีสลิป กับ ยังไม่ได้กรอกอีเมลในระบบ HR)

## 4. ข้อมูลอ่อนไหวส่งเป็น HTML ในตัวอีเมล

สลิปเงินเดือนเข้าข่ายข้อมูลส่วนบุคคลตาม PDPA การส่งเป็น HTML ในตัวเมลแปลว่าใครก็ตามที่เข้าถึง mailbox ได้ หรือระบบ mail archive ขององค์กร จะเห็นเงินเดือนทั้งหมด

แนวทางที่หลายที่ใช้: แนบเป็น PDF ที่ล็อกด้วยรหัส (เช่น เลขบัตรประชาชน 4 ตัวท้าย หรือรหัสที่ตั้งเอง) หรือส่งแค่ลิงก์ให้ล็อกอินเข้ามาดูในระบบ ส่วนนี้แล้วแต่นโยบายบริษัท แต่ควรมีการตัดสินใจไว้ชัดเจน ไม่ใช่ปล่อยตามค่าเริ่มต้น

## 5. จุดเล็กที่ควรใส่

- `CancellationToken` ส่งต่อให้ทั้งสอง call ไม่งั้นตอน shutdown งานจะค้าง
- subject `"สลิปเงินเดือน"` ควรดึงจาก resource หรือ config เผื่อมีพนักงานต่างชาติ หรือต้องการใส่งวดเดือนลงไป เช่น "สลิปเงินเดือน ตุลาคม 2569"
- ชื่อ method ลงท้าย `Async` ตามแบบแผน .NET
- idempotency ถ้ามี retry ต้องกันการส่งซ้ำ เก็บสถานะว่าส่งสลิปงวดไหนไปแล้ว ไม่งั้น retry ทีเดียวพนักงานได้เมลสามฉบับ

## โค้ดที่ปรับแล้ว

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
        await _email.SendAsync(slip.Email, _subjectBuilder.ForPayslip(slip.Period), slip.Html, ct);
        _logger.LogInformation("ส่งสลิปงวด {Period} ให้พนักงาน {EmployeeId} สำเร็จ", slip.Period, employeeId);
        return true;
    }
    catch (Exception ex) when (ex is not OperationCanceledException)
    {
        _logger.LogError(ex, "ส่งสลิปงวด {Period} ให้พนักงาน {EmployeeId} ไม่สำเร็จ", slip.Period, employeeId);
        return false;
    }
}
```

สังเกตว่าผมไม่ได้เอา `GetSlipAsync` ไว้ใน try เพราะถ้าดึงสลิปไม่ได้คือปัญหาคนละชนิดกับส่งเมลไม่ออก ควรให้ exception หลุดขึ้นไปให้ชั้นบนจัดการ ส่วน `when (ex is not OperationCanceledException)` ใส่ไว้ไม่ให้การ cancel ตอน shutdown ถูกนับเป็น error

การคืน `bool` เหมาะกับกรณีที่ caller เป็น loop ส่งทีละคนแล้วอยากได้สรุปตอนท้าย ถ้าเรียกทีละคนจากหน้าจอ ใช้ Result object ที่บอกสาเหตุได้จะดีกว่า

ถ้าบอกได้ว่า method นี้เรียกจากไหน (controller, background job หรือวนลูปส่งทั้งบริษัท) เดี๋ยวผมแนะนำเรื่อง retry กับการรายงานผลให้ตรงกับการใช้งานจริงครับ
