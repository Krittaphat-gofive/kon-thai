ถ้าแอปเป็น .NET ที่มี SQL Server อยู่แล้ว ผมเลือก Hangfire ครับ

เหตุผลหลักคือ job ส่งอีเมลแบบนี้ต้องใช้ข้อมูลพนักงาน template และ business logic ชุดเดียวกับแอปหลัก ถ้าแยกไป Functions ก็ต้องลาก model, DbContext, connection string ไปอีกชุด กลายเป็นดูแลสองที่โดยไม่ได้อะไรกลับมาเท่าไร

## เลือก Hangfire เมื่อ

- deploy เป็น monolith หรืออยู่บน App Service อยู่แล้ว และมี SQL Server ให้ใช้เป็น storage
- อยากได้ dashboard ดู job ที่ fail แล้วกด retry เองได้ ตัวนี้มีประโยชน์มากตอน provider อีเมลล่ม
- ต้อง enqueue จากใน request เช่น พอ approve ใบลาเสร็จ ยิงอีเมลทันที เขียน `BackgroundJob.Enqueue(...)` บรรทัดเดียวจบ
- ปริมาณอยู่ระดับหลักพันถึงหลักหมื่นฉบับต่อวัน

## เลือก Azure Functions เมื่อ

- อยู่บน Azure เต็มตัวแล้ว และอยากแยก workload ไม่ให้งานส่งอีเมลไปแย่ง CPU ตอน user กำลังใช้แอป
- ปริมาณขึ้นลงแรง เช่น สิ้นเดือนยิงทีเดียวหลักแสน อยากให้ scale out เอง
- ไม่อยากมี process รันค้างตลอด จ่ายตามที่ใช้จริง
- ทีมอยาก deploy job แยก ไม่ต้อง restart แอปหลักเวลาแก้ logic อีเมล

| | Hangfire | Azure Functions |
|---|---|---|
| ที่เก็บ job | SQL Server / Redis ที่ดูแลเอง | ผูกกับ storage account |
| scale | ตามจำนวน instance ของแอป | auto scale |
| มองเห็นสถานะ job | dashboard สำเร็จรูป | ต้องดูผ่าน App Insights |
| แชร์โค้ดกับแอปหลัก | ใช้ร่วมกันตรง ๆ | ต้องแยก project หรือทำ shared library |
| ค่าใช้จ่าย | ไม่มีเพิ่ม ถ้ามี server อยู่แล้ว | จ่ายตามการใช้งาน |
| lock-in | ย้าย cloud ได้ | ผูกกับ Azure |

## จุดที่มักพลาด

Hangfire บน App Service ต้องเปิด Always On ไม่งั้นพอไม่มี request เข้ามาสักพัก IIS จะ unload แอป แล้ว worker หยุดทำงาน recurring job ไม่ยิงตามเวลา

ส่วน Functions ถ้าใช้ Consumption plan จะมี cold start งานที่ต้องตรงเวลาเป๊ะ ๆ ควรไปใช้ Premium plan

## เรื่องที่สำคัญกว่าการเลือกเครื่องมือ

ทั้งสองตัวเป็น at-least-once delivery เหมือนกัน แปลว่ามีโอกาสรัน job ซ้ำ ประเด็นพวกนี้ต้องจัดการเองไม่ว่าจะเลือกตัวไหน

1. **กันส่งซ้ำ** ทำตาราง log การส่ง ใส่ unique index ที่ `(EmployeeId, NotificationType, PeriodKey)` ก่อนส่งเช็กก่อน พนักงานจะได้ไม่โดนอีเมลเดิมสามรอบ
2. **แยกประเภท error** SMTP timeout หรือ 429 ให้ retry แบบ exponential backoff แต่ถ้าอีเมลผิด format หรือ 550 อย่า retry เพราะ retry กี่รอบก็ไม่ผ่าน
3. **rate limit** SendGrid กับ Graph API มีเพดานต่อวินาที ถ้ายิงรัวเกินจะโดน throttle ต้องหน่วงเอง
4. **timezone** cron ของ Hangfire default เป็น UTC ถ้าจะส่งเก้าโมงเช้าเวลาไทยต้องระบุ `TimeZoneInfo` ให้ชัด
5. **แตก job ย่อย** อย่าวน loop ส่งพนักงาน 500 คนใน job เดียว ให้ job แม่ query รายชื่อแล้ว enqueue job ย่อยต่อคน พังคนเดียวจะได้ไม่ล้มทั้งชุด และ retry เฉพาะคนนั้นได้

ตอนนี้แอป deploy อยู่ที่ไหนครับ แล้วอีเมลนี้เป็นแบบตั้งเวลาส่งรายวัน หรือยิงตาม event ที่เกิดในระบบ ถ้าบอกมาเดี๋ยวผมช่วยวางโครงให้ละเอียดกว่านี้ครับ
