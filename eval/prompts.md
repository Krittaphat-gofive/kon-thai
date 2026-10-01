# ชุดคำถาม baseline

คำถามจากงานประจำวัน ใช้วัดว่า Claude ตอบภาษาไทยเป็นธรรมชาติแค่ไหน
แต่ละข้อขึ้นต้นด้วย `## <id> | <หมวด>` แล้วตามด้วยตัวคำถาม เพิ่มหรือแก้ได้ตามสบาย
`eval/run_eval.py` อ่านทุกหัวข้อ `## ` ในไฟล์นี้

## 01-error-angular | อธิบาย error
รัน ng serve แล้วเจอ error นี้ใน console หมายความว่าอะไร แก้ยังไง

```
NG0100: ExpressionChangedAfterItHasBeenCheckedError: Expression has changed after it was checked. Previous value: 'false'. Current value: 'true'.
```

## 02-error-dotnet | อธิบาย error
API ตอบ 500 แล้วใน log มีแบบนี้ ช่วยอธิบายหน่อยว่าเกิดจากอะไร

```
System.InvalidOperationException: A second operation was started on this context instance before a previous operation completed. This is usually caused by different threads concurrently using the same instance of DbContext.
```

## 03-concept-signal | สอน concept
อธิบาย signal ใน Angular ให้หน่อย ต่างจาก RxJS Observable ยังไง แล้วควรใช้อะไรตอนไหน

## 04-concept-rebase | สอน concept
git rebase กับ git merge ต่างกันยังไง ทีมเราควรใช้แบบไหน

## 05-review-nested-subscribe | รีวิวโค้ด
ช่วยรีวิวโค้ดนี้หน่อย

```ts
ngOnInit() {
  this.http.get('/api/employees').subscribe(res => {
    this.employees = res;
    this.http.get('/api/departments').subscribe(d => {
      this.departments = d;
    });
  });
}
```

## 06-review-sql | รีวิวโค้ด
query นี้ช้ามาก ตาราง Employee มีประมาณ 2 ล้าน row ช่วยดูหน่อยว่าน่าจะติดตรงไหน

```sql
SELECT * FROM Employee e
WHERE YEAR(e.StartDate) = 2026
  AND e.CompanyId = @CompanyId
ORDER BY e.FirstName
```

## 07-pr-description | เขียนงานให้คนอื่นอ่าน
ช่วยเขียน PR description ให้หน่อย งานคือเพิ่ม validation ตอนพนักงานขอลาเกินโควตา ฝั่ง API เช็กโควตาก่อนบันทึก ฝั่งเว็บแสดง error ใต้ช่องวันลา และเพิ่ม unit test 6 เคส

## 08-commit-message | เขียนงานให้คนอื่นอ่าน
ช่วยเขียน commit message ภาษาไทยให้หน่อย แก้บั๊กหน้ารายงานเงินเดือนที่คำนวณ OT ผิดเวลาพนักงานทำงานข้ามเที่ยงคืน

## 09-slack-release | เขียนงานให้คนอื่นอ่าน
เขียนข้อความอัปเดตลง Slack ให้ทีมหน่อย ว่า deploy เวอร์ชัน 3.2 ขึ้น production แล้ว มีฟีเจอร์ใหม่คือ export รายงานเป็น Excel และแก้บั๊ก login ค้างบน Safari

## 10-incident-customer | เขียนงานให้คนอื่นอ่าน
ช่วยร่างข้อความแจ้งลูกค้าหน่อย เมื่อเช้าระบบล่มไป 40 นาทีเพราะ disk ของ database เต็ม ตอนนี้กลับมาใช้งานได้แล้ว และเราตั้ง alert เพิ่มแล้ว

## 11-explain-to-pm | อธิบายให้คนนอกสาย dev
PM ถามว่าทำไมแก้ปุ่มเดียวต้องใช้เวลา 3 วัน ช่วยอธิบายแบบที่คนไม่ใช่ dev เข้าใจหน่อย จริงๆ ต้องแก้ทั้ง API, DB migration แล้วก็ test

## 12-recommend-forms | แนะนำทางเลือก
ฟอร์มยาวๆ ที่มีหลายหน้า ควรใช้ Reactive Forms หรือ Signal Forms ดี ช่วยแนะนำหน่อย

## 13-architecture-cqrs | สอน concept
อธิบาย CQRS ให้หน่อย ระบบ HR แบบของเราเหมาะจะใช้ไหม

## 14-debug-slow-page | แนะนำวิธีไล่ปัญหา
หน้า dashboard โหลดช้ามาก ประมาณ 8 วินาที ควรเริ่มไล่หาสาเหตุจากตรงไหนบ้าง

## 15-explain-code | อธิบายโค้ด
โค้ดนี้ทำอะไร

```csharp
public async Task<IActionResult> Get(int id) =>
    await _cache.GetOrCreateAsync($"emp:{id}", async e =>
    {
        e.AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5);
        return await _repo.FindAsync(id);
    }) is { } emp ? Ok(emp) : NotFound();
```

## 16-upgrade-plan | วางแผนงาน
ถ้าจะย้ายโปรเจกต์จาก Angular 17 ไป 20 ต้องเตรียมอะไรบ้าง

## 17-readme-section | เขียนเอกสาร
ช่วยเขียนหัวข้อ "วิธีรันโปรเจกต์บนเครื่อง" ใน README ให้หน่อย โปรเจกต์ใช้ .NET 9, SQL Server ที่รันใน Docker และ Angular 20

## 18-tradeoff-graphql | แนะนำทางเลือก
ทีมอยากเปลี่ยนจาก REST เป็น GraphQL มีข้อดีข้อเสียอะไรบ้าง

## 19-short-async | คำถามสั้น
async/await ใน C# ทำงานยังไงข้างใน อธิบายสั้นๆ

## 20-teach-junior-di | สอนน้องในทีม
น้องในทีมเพิ่งจบใหม่ ยังไม่เข้าใจว่า dependency injection คืออะไร ช่วยอธิบายให้เข้าใจง่ายๆ หน่อย
