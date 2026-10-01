ถ้าระบบหลักเป็น ASP.NET Core ที่ deploy เป็น web app อยู่แล้ว และมี SQL Server ใช้งานอยู่ ผมแนะนำ Hangfire ครับ

เหตุผลหลักคือแรงเสียดทานต่ำกว่ามาก job อยู่ใน solution เดียวกับ domain model เรียก `DbContext` ตัวเดิม ใช้ DI ตัวเดิม ไม่ต้องแยก repo ไม่ต้องแยก pipeline แล้ว dashboard ของ Hangfire ก็ตอบโจทย์งานแบบนี้พอดี เพราะเวลา HR ถามว่า "เมลวันที่ 1 ส่งไปกี่คน ตกไปกี่คน" เปิดดูแล้วกดสั่ง retry ใหม่ได้เลย ถ้าใช้ Functions ต้องไปไล่ใน Application Insights ซึ่งทำได้แต่เสียเวลากว่า

## เลือก Azure Functions เมื่อไหร่

- ระบบเดิมเป็น serverless อยู่แล้ว หรือไม่มี long-running host ให้ job เกาะ
- ปริมาณงานกระชากเป็นช่วง เช่น สิ้นเดือนทีเดียวหลักแสนฉบับ แล้วปกติแทบไม่มีงาน จุดนี้ Consumption plan คุ้มกว่าชัดเจน
- อยากให้ job ล่มแล้วไม่กระทบ web app เลย (Hangfire รันใน process เดียวกัน job หนัก ๆ ก็แย่ง CPU กับ request จริงได้)

| | Hangfire | Azure Functions |
|---|---|---|
| ที่เก็บ state | ต้องมี DB (SQL/Redis) | Storage account / Service Bus |
| ค่าใช้จ่าย | รวมอยู่ใน host เดิม | จ่ายตาม execution |
| scale | scale ทั้ง app | scale เองอัตโนมัติ |
| หน้าจอดูงานที่ fail | มีในตัว | ต้องพึ่ง App Insights |
| ข้อควรระวัง | App Service ต้องเปิด Always On | cold start, timeout 10 นาทีบน Consumption |

## สามข้อที่ต้องทำ ไม่ว่าจะเลือกตัวไหน

**1. อย่า loop ส่งเมลทั้งก้อนใน job เดียว** ให้ job แรกทำหน้าที่หารายชื่อ แล้วแตกเป็น job ย่อยรายคน (Hangfire ใช้ `BackgroundJob.Enqueue` ต่อคน / Functions ก็โยนเข้า queue) ไม่งั้นพอคนที่ 300 ส่งพลาด แล้ว retry ทั้ง batch คน 1 ถึง 299 จะได้เมลซ้ำ

**2. กัน duplicate ด้วยตาราง log** ทั้งสองตัวเป็น at-least-once คือมีโอกาสรันซ้ำโดยธรรมชาติ ทำตารางเก็บ `(EmployeeId, NotificationType, PeriodKey)` แล้ว unique index ไว้ ก่อนส่งเช็กก่อน ปลอดภัยกว่าหวังว่าจะไม่ซ้ำ

**3. ระวัง timezone** cron ของ Hangfire default เป็น UTC ต้องส่ง `TimeZoneInfo` ของ `"SE Asia Standard Time"` เข้าไปด้วย ส่วน Functions ตั้ง app setting `WEBSITE_TIME_ZONE` ไม่งั้นเมล "แจ้งเตือนตอน 8 โมงเช้า" จะไปโผล่บ่าย 3

ถ้าบอกได้ว่าตอนนี้ระบบ deploy อยู่บนอะไร (App Service, VM, หรือ container) กับงานนี้เป็นแบบตั้งเวลายิงหรือยิงตาม event เดี๋ยวผมเจาะให้ละเอียดขึ้นได้ครับ
