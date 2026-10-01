ขึ้นกับว่าแอปหลักตอนนี้ deploy ยังไงครับ ถ้าเป็น ASP.NET Core ตัวเดียวที่รันอยู่บน App Service หรือ container อยู่แล้ว เริ่มที่ Hangfire ง่ายกว่าเยอะ ถ้าระบบแยกเป็นหลายส่วนอยู่แล้ว หรือปริมาณอีเมลพุ่งเป็นช่วง ๆ ค่อยไป Azure Functions

## เทียบสั้น ๆ

| | Hangfire | Azure Functions |
|---|---|---|
| เริ่มงาน | เพิ่ม package ใน โปรเจกต์เดิม ใช้ DbContext กับ service เดิมได้เลย | แยก โปรเจกต์ แยก pipeline แยก config |
| ดู job ที่ fail | dashboard ในตัว กด requeue เองได้ | ดูผ่าน Application Insights หรือ poison queue |
| scale | ตาม instance ของแอปหลัก | scale out เองตามคิว |
| ค่าใช้จ่าย | ไม่มีเพิ่ม (ใช้ DB เดิมเป็น storage) | จ่ายตามการใช้งาน ถ้าต้องเลี่ยง cold start ก็ต้องขึ้น plan |

## เลือก Hangfire ถ้า

งานส่งอีเมลผูกกับข้อมูลในแอปหลัก เช่น ดึงรายชื่อพนักงานที่ต้องแจ้ง แล้วประกอบ template จาก service เดิม ย้ายไป Functions แปลว่าต้องแชร์ DbContext กับ template ข้าม โปรเจกต์ ซึ่งลงเอยที่ต้องแตก shared library ออกมาอีก

ข้อที่ต้องระวัง
- บน App Service ต้องเปิด Always On ไม่งั้นพอไม่มี request เข้ามาสักพัก process หลับ job ไม่รัน
- worker รันใน process เดียวกับ web ถ้ารอบหนึ่งส่งเป็นพันฉบับ จะแย่ง thread กับ request ของผู้ใช้ ทางแก้คือแยก worker เป็นอีก process ที่ต่อ storage เดียวกัน
- scale out หลาย instance แล้วชี้ไปคนละ storage จะได้อีเมลซ้ำตามจำนวน instance
- หน้า dashboard ต้องใส่ authorization filter ก่อนขึ้น production ค่าเริ่มต้นเปิดให้เข้าได้ทุกคนที่รู้ URL

## เลือก Azure Functions ถ้า

ปริมาณไม่สม่ำเสมอ เช่น ปกติวันละไม่กี่ฉบับ แต่สิ้นเดือนยิงทีเดียวเป็นหมื่น แบบนี้ Queue trigger scale out ให้เอง ไม่ต้องเผื่อ instance ของ API ไว้รองรับ หรือกรณีที่ตัวกระตุ้นมาจาก event ข้างนอกอยู่แล้ว เช่น Service Bus

ข้อที่ต้องระวัง
- Consumption plan มี timeout (ค่าเริ่มต้น 5 นาที ปรับได้ถึง 10) ถ้าเขียนเป็น loop ส่งทีละคนในฟังก์ชันเดียวจะชนเพดาน ต้องออกแบบให้ 1 message = 1 อีเมล แล้วให้ตัว timer ทำหน้าที่แค่หว่าน message ลงคิว
- cold start ทำให้ฉบับแรกของรอบช้าไปหลายวินาที ซึ่งงานแจ้งเตือนพนักงานส่วนใหญ่รับได้

## สองทางนี้ต้องทำเหมือนกัน

กันส่งซ้ำ เพราะทั้ง Hangfire retry และ queue แบบ at-least-once ทำให้ job เดิมรันซ้ำได้ ให้มีตาราง log การส่ง ตั้ง unique index บน (employeeId, notificationType, period) แล้วเช็กก่อนยิงทุกครั้ง

อีกเรื่องคืออย่าต่อ SMTP ตรงจากโค้ด ส่งผ่าน SendGrid หรือ Azure Communication Services แล้วปล่อยให้ provider จัดคิวกับ retry ฝั่ง delivery ให้ ตัว job จะได้จบเร็วและไม่ค้างรอ network

รอบหนึ่งส่งประมาณกี่ฉบับ และแอปหลักรันบนอะไรอยู่ครับ เดี๋ยวฟันธงให้ชัดกว่านี้
