ถ้าแอปหลักเป็น ASP.NET Core ที่รันบน App Service อยู่แล้ว ผมแนะนำ Hangfire ครับ

## ทำไมถึงเลือก Hangfire

- enqueue job จากโค้ดเดิมได้เลย `BackgroundJob.Enqueue(() => ...)` ใช้ DbContext, DI, config, email template ชุดเดิมทั้งหมด ไม่ต้องย้าย domain logic ไปอยู่อีก deployment หรือเปิด API ให้ตัวเองเรียก
- recurring job เขียน cron ได้ตรง ๆ เหมาะกับงานแจ้งเตือนตามรอบ เช่น แจ้งเอกสารใกล้หมดอายุทุกเช้า
- dashboard มาให้พร้อม ops เห็นว่า job ไหน fail retry ไปกี่รอบ แล้วสั่งรันซ้ำจากหน้าเว็บได้ งานอีเมลพลาดแล้วต้องตามส่งใหม่บ่อย ตรงนี้ช่วยได้เยอะ
- ถ้าใช้ SQL Server storage ตัวเดียวกับแอป จะ enqueue job ใน transaction เดียวกับการบันทึกข้อมูลได้ ลดเคสที่บันทึกสำเร็จแต่ไม่ได้ส่งเมล หรือส่งเมลไปแล้วแต่ข้อมูล rollback

ข้อควรระวังสองเรื่อง: ต้องเปิด Always On ไม่งั้น App Service idle แล้ว worker หยุดทำงาน และถ้าปริมาณเมลเยอะ job จะแย่ง thread pool กับ request ของผู้ใช้ แก้ด้วยการแยก worker ไปอยู่ App Service อีกตัวที่ชี้ storage เดียวกัน ตัวนั้นไม่ต้อง map route อะไรเลย

## เมื่อไหร่ควรไป Azure Functions

- ไม่มี host ที่รันตลอดอยู่แล้ว เช่น frontend เป็น Static Web App, backend เป็น Functions อยู่แล้ว กรณีนี้ไม่มีเหตุผลต้องตั้ง App Service ขึ้นมาเลี้ยง Hangfire
- โหลดกระจุกเป็นช่วง เช่น สิ้นเดือนยิงทีละแสนฉบับ แล้วที่เหลือเงียบ แบบนี้ queue trigger บน consumption plan คุ้มกว่าและ scale ให้เอง
- อยากแยก lifecycle ชัด ๆ ให้ทีมที่ดูแล notification deploy เองได้โดยไม่กระทบ API หลัก

ถ้าเลือก Functions ให้ใช้ Queue trigger (Storage Queue หรือ Service Bus) เป็นหลัก ส่วน Timer trigger ให้ทำหน้าที่แค่หยิบรายการที่ถึงกำหนดแล้วโยนเข้า queue อย่าให้ Timer วน query แล้วส่งเมลเองทั้งรอบ เพราะ retry ของ Timer ไม่ได้แยกเป็นราย job ถ้าพังกลางทางจะไล่ไม่ออกว่าส่งไปถึงคนไหนแล้ว

## เรื่องที่ต้องทำเหมือนกันทั้งสองทาง

ทั้ง Hangfire และ Functions รับประกันแค่ at-least-once แปลว่ามีโอกาสส่งซ้ำ ถ้า worker ตายหลังส่งเมลออกไปแล้วแต่ยังไม่ทันบันทึกว่าเสร็จ

- ทำตาราง notification log ที่มี unique key เช่น `{employeeId}_{eventType}_{refId}` แล้วเช็กก่อนส่งทุกครั้ง
- แยก "สร้างรายการที่ต้องส่ง" ออกจาก "ส่งจริง" ตัวแรกอยู่ใน transaction เดียวกับ business logic ส่วนตัวหลังเป็น job ที่ retry ซ้ำได้โดยไม่พัง
- ตัว provider จะใช้ SendGrid หรือ Azure Communication Services ก็ได้ เรื่องนี้แยกจากการเลือก Hangfire กับ Functions

ถ้าบอกได้ว่าตอนนี้แอปหลัก deploy แบบไหน แล้วการแจ้งเตือนเป็น event-driven หรือเป็นรอบตามเวลา เดี๋ยวผมชี้ให้ชัดกว่านี้ครับ
