# ชุดคำถาม held-out

ชุดนี้ไว้วัดผลอย่างเดียว ห้ามเอาคำตอบจากชุดนี้ไปทำตัวอย่างหรือกฎใน style ไม่งั้นจะวัดไม่ได้ว่า style ใช้ได้กับคำถามที่ไม่เคยเห็นจริงไหม
รูปแบบเหมือน `eval/prompts.md`

## h01-error-typescript | อธิบาย error
build แล้วเจอ error นี้ แก้ยังไงดี

```
TS2345: Argument of type 'string | undefined' is not assignable to parameter of type 'string'.
```

## h02-error-ef-migration | อธิบาย error
รัน `dotnet ef database update` แล้วขึ้นแบบนี้ ทำยังไงต่อ

```
There is already an object named 'Employees' in the database.
```

## h03-concept-jwt | สอน concept
อธิบาย access token กับ refresh token ของ JWT ให้หน่อย ทำไมต้องมีสองตัว

## h04-concept-idempotency | สอน concept
idempotency ใน API คืออะไร ทำไมระบบจ่ายเงินเดือนต้องสนใจเรื่องนี้

## h05-review-async-void | รีวิวโค้ด
ช่วยรีวิวโค้ดนี้หน่อย

```csharp
public async void SendPayslip(int employeeId)
{
    try
    {
        var slip = await _payrollService.GetSlipAsync(employeeId);
        await _email.SendAsync(slip.Email, "สลิปเงินเดือน", slip.Html);
    }
    catch (Exception)
    {
    }
}
```

## h06-review-ngfor | รีวิวโค้ด
template นี้มีอะไรควรแก้ไหม รายการพนักงานมีประมาณ 3,000 คน

```html
<div *ngFor="let emp of employees">
  {{ formatName(emp) }} - {{ calculateLeaveBalance(emp) }} วัน
</div>
```

## h07-release-note | เขียนงานให้คนอื่นอ่าน
เขียน release note ให้ลูกค้าฝั่ง HR อ่าน มีสองเรื่อง คือเพิ่มการอนุมัติใบลาได้หลายขั้น กับแก้รายงานภาษีหัก ณ ที่จ่ายที่แสดงผิดเดือน

## h08-slack-ask-review | เขียนงานให้คนอื่นอ่าน
ช่วยเขียนข้อความขอให้คนในทีมช่วย review PR ให้หน่อย PR ใหญ่ประมาณ 40 ไฟล์ อยากให้อ่านแล้วไม่รู้สึกกดดัน

## h09-explain-password-policy | อธิบายให้คนนอกสาย dev
HR ถามว่าทำไมระบบบังคับเปลี่ยนรหัสผ่านทุก 90 วัน แล้วทำไมบางทีระบบเด้งออกเอง ช่วยอธิบายแบบที่ HR เข้าใจหน่อย

## h10-recommend-background-job | แนะนำทางเลือก
จะทำ background job ส่งอีเมลแจ้งเตือนพนักงาน ใช้ Hangfire หรือ Azure Functions ดี

## h11-debug-stale-cache | แนะนำวิธีไล่ปัญหา
หลัง deploy เวอร์ชันใหม่ ผู้ใช้บางคนยังเห็นหน้าเก่าอยู่ ต้องกด refresh แรง ๆ ถึงจะหาย เกิดจากอะไร

## h12-short-stash | คำถามสั้น
git stash กับ commit เก็บไว้ก่อน ต่างกันยังไง ตอบสั้น ๆ

## h13-plan-legacy-tests | วางแผนงาน
ถ้าจะเริ่มเขียน unit test ให้โปรเจกต์เก่าที่ไม่มี test เลย ควรเริ่มจากตรงไหน

## h14-incident-leaked-secret | สถานการณ์เร่งด่วน
เพิ่งรู้ว่าเผลอ commit connection string ที่มีรหัสผ่าน database ขึ้น GitHub repo ที่เป็น public ไปตั้งแต่เมื่อวาน ต้องทำอะไรบ้าง
