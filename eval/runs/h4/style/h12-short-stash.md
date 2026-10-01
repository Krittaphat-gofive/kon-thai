ต่างกันหลักคือ commit อยู่ใน history ของ branch ส่วน stash อยู่นอก history ครับ

- **stash**: เก็บไว้ใน stack กลาง ๆ ไม่ผูกกับ branch ไหน เอาไป `git stash pop` ที่ branch อื่นได้ แต่ push ขึ้น remote ไม่ได้ ถ้าลืมไว้นาน ๆ หรือ pop ชนกันก็หายง่าย
- **commit เก็บไว้ก่อน (WIP commit)**: ติดอยู่กับ branch นั้น มี message บอกว่าทำอะไรค้างไว้ push ขึ้น remote เป็น backup ได้ แล้วค่อย `--amend` หรือ squash รวมทีหลังตอนจะเปิด PR

เลือกแบบนี้
- สลับ branch ไปดูอะไรแป๊บเดียวแล้วกลับมาทำต่อ: stash
- งานค้างข้ามวัน ค้างหลายไฟล์ หรืออยากให้มี backup บน remote: commit ไว้ก่อน แล้วจัดระเบียบตอนจบ
