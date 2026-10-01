รีวิวให้แล้ว โค้ดสั้นแต่มีปัญหาหนักอยู่ 2 จุดที่ต้องแก้ก่อนขึ้น prod ครับ

## 1. `async void` — อันตรายสุด

`async void` ทำให้ caller `await` ไม่ได้ ไม่รู้ว่างานเสร็จหรือยัง และถ้ามี exception หลุดออกมานอก try (เช่นตอน resolve dependency หรือ `_payrollService` เป็น null) มันจะไปโผล่ที่ `SynchronizationContext` แล้ว **kill ทั้ง process** ไม่ใช่แค่ request เดียว

ให้ใช้ `async Task` เสมอ ยกเว้นกรณีเดียวคือ event handler จริงๆ (`button_Click` แบบนั้น)

## 2. `catch` เปล่าๆ — กลืน error หายเงียบ

อันนี้คือ anti-pattern ที่เรียกว่า exception swallowing เมล์ส่งไม่ออก SMTP ล่ม อีเมลผิด — ทุกเคสจบเหมือนกันหมดคือ "เงียบ" ฝั่ง HR จะคิดว่าส่งไปแล้ว พนักงานก็ไม่ได้สลิป กว่าจะรู้ตัวคือสิ้นเดือนแล้วมีคนทัก

อย่างน้อยต้อง log ไว้ และโดยมากควร `throw;` ต่อ ให้ชั้นบนตัดสินใจเองว่าจะ retry หรือจะขึ้น error ให้ user

## 3. ไม่เช็ค null

`slip` กับ `slip.Email` อาจเป็น null ได้ (พนักงานลาออก ยังไม่มีข้อมูลเดือนนี้ หรือไม่ได้กรอกอีเมล) ตอนนี้ `NullReferenceException` ถูก catch เปล่ากลืนไปพอดี เลยไม่มีใครรู้เลยว่าข้อมูลมีปัญหา

## 4. ไม่มี `CancellationToken`

ถ้า request ถูกยกเลิก งานยังวิ่งต่อ เปลืองทรัพยากรฟรีๆ

## 5. ชื่อ method

convention ของ .NET คือ method ที่เป็น async ลงท้ายด้วย `Async` → `SendPayslipAsync`

---

## โค้ดที่แก้แล้ว

```csharp
public async Task SendPayslipAsync(int employeeId, CancellationToken ct = default)
{
    var slip = await _payrollService.GetSlipAsync(employeeId, ct);

    if (slip is null)
    {
        _logger.LogWarning("ไม่พบสลิปเงินเดือนของพนักงาน {EmployeeId}", employeeId);
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
        _logger.LogInformation("ส่งสลิปให้พนักงาน {EmployeeId} สำเร็จ", employeeId);
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "ส่งสลิปให้พนักงาน {EmployeeId} ไม่สำเร็จ", employeeId);
        throw;
    }
}
```

---

## อีก 2 เรื่องที่ควรคิดต่อ (นอกเหนือจากตัวโค้ด)

**เรื่อง PII** — สลิปเงินเดือนเป็นข้อมูลส่วนบุคคลอ่อนไหวตาม PDPA การยัด HTML เงินเดือนเต็มๆ ไปในเมลแปลว่าข้อมูลไปนอนอยู่ใน mailbox ของ provider ตลอดกาล ถ้าทำได้ควรส่งแค่ลิงก์ที่ต้อง login เข้ามาดู หรือถ้าจะแนบไฟล์ก็ใส่รหัสผ่าน และ **อย่า log ค่า `slip.Email` หรือ `slip.Html` ลงไฟล์ log เด็ดขาด** (ในโค้ดข้างบนผม log แค่ `employeeId` ด้วยเหตุผลนี้)

**เรื่อง reliability** — ถ้า method นี้ถูกเรียกตอนปิดงวดเงินเดือนทีละหลายร้อยคน การยิง SMTP ตรงๆ ใน request จะพังง่ายมาก ควรเขียนลง outbox table แล้วให้ background worker ค่อยๆ ส่งพร้อม retry จะทนกว่าเยอะ และได้ audit trail ด้วยว่าใครได้รับแล้วบ้าง
