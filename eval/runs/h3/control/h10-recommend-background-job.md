ตอบสั้น ๆ ก่อน: **ถ้าแอปเป็น ASP.NET ตัวเดียวที่รันอยู่ตลอดอยู่แล้ว เอา Hangfire** จบไวสุดและของน้อยชิ้นสุด ส่วน **ถ้าอยู่บน Azure อยู่แล้วและเมลมาเป็น burst (เช่นสิ้นเดือนยิงทีละพันฉบับ) ไป Azure Functions + Queue**

ตัวตัดสินจริง ๆ คือ host ที่ใช้อยู่ ไม่ใช่ตัว library

## Hangfire

ข้อดีคือใช้ DI, EF context, service เดิมได้หมด ไม่ต้องแยก project ไม่ต้องแยก pipeline เขียน `BackgroundJob.Enqueue(() => _mailer.Send(id))` แล้วจบ มี dashboard ดู job ที่ fail + retry ให้ในตัว

จุดที่มักพลาด:
- ต้องเปิด **Always On** (App Service) ไม่งั้นแอปหลับแล้ว job ไม่วิ่ง ส่วน IIS app pool recycle กลางคัน job จะค้างสถานะ Processing จนกว่า invisibility timeout จะหมด
- Dashboard default เปิดให้ใครเข้าก็ได้ตอน deploy จริง ต้องใส่ authorization filter ให้เรียบร้อย
- job กิน CPU/memory ก้อนเดียวกับเว็บ ถ้าวันไหนยิงเมลหนัก ๆ หน้าเว็บจะหน่วงตาม ทางแก้คือแยก worker process (console app / Windows Service) ที่ชี้ Hangfire storage เดียวกัน
- storage บน SQL เดิมได้ แต่ถ้า job เยอะมันกิน IO พอตัว เผื่อ Redis ไว้

## Azure Functions

เหมาะกว่าเมื่ออยากให้งานเมลสเกลแยกจากเว็บ และจ่ายตามที่ใช้จริง แพตเทิร์นที่ควรทำคือ **อย่าให้ Timer trigger วน loop ส่งเมลเองทั้งก้อน** — ให้ Timer อ่านรายชื่อแล้ว enqueue เข้า Service Bus/Storage Queue จากนั้นมี Queue trigger ส่งทีละฉบับ ได้ retry รายฉบับ + poison queue ฟรี ฉบับไหนพังก็ไม่ลากฉบับอื่นตาย

จุดที่มักพลาด:
- Consumption plan มี timeout (5 นาที default, สูงสุด 10) กับ cold start ถ้าทนไม่ได้ต้องขึ้น Premium ซึ่งค่าใช้จ่ายเริ่มไม่ถูกแล้ว
- code ที่ใช้ร่วมกับเว็บต้องแยกเป็น class library ไม่งั้น logic เมลจะเริ่มแตกเป็นสองชุด
- เพิ่ม pipeline, เพิ่ม config, เพิ่มที่ต้องดู log อีกที่

## เรื่องที่ต้องทำไม่ว่าเลือกอันไหน

ทั้งคู่เป็น **at-least-once** คือมีโอกาสส่งซ้ำ ไม่ใช่ปัญหาของ Hangfire หรือ Functions แต่เป็นธรรมชาติของ retry ฉะนั้นต้องมีตารางประมาณ `NotificationLog` เก็บว่า (employeeId, notificationType, period) นี้ส่งไปแล้ว แล้วเช็กก่อนยิงทุกครั้ง ไม่งั้นพนักงานได้เมลซ้ำ 3 ฉบับตอน provider timeout แล้ว retry

คำแนะนำสุดท้าย: เริ่มที่ Hangfire ไปก่อนถ้ายังไม่มี Azure infra พร้อม เพราะย้ายไป Functions ทีหลังง่ายถ้าแยก logic ส่งเมลเป็น service ไว้ตั้งแต่แรก — ตัว job ก็แค่ shell ที่เรียก service นั้น

ถ้าบอกได้ว่าตอนนี้ deploy อยู่บนอะไร (App Service / VM / on-prem) กับเมลเป็นแบบ scheduled หรือ event-driven เดี๋ยวฟันธงให้ชัดกว่านี้
