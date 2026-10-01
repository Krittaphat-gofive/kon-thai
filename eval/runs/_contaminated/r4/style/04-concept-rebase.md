ต่างกันที่วิธีรวมงานกับรูปร่างของ history ครับ merge เก็บประวัติจริงว่าแตก branch ไปแล้วรวมกลับเมื่อไหร่ ส่วน rebase ทำให้ประวัติเป็นเส้นตรงเหมือนไม่เคยแตก branch

**merge**
- git สร้าง merge commit ตัวใหม่ที่มี parent สองตัว ส่วน commit เดิมอยู่ครบไม่เปลี่ยน hash
- แก้ conflict รอบเดียวจบตอน merge
- ปลอดภัยเสมอ เพราะไม่ไปแตะ commit ที่ push ขึ้น remote ไปแล้ว
- ข้อเสียคือถ้า merge main เข้า feature บ่อย ๆ log จะรก เต็มไปด้วย "Merge branch 'main' into ..."

**rebase**
- git เอา commit ของเราไปเขียนใหม่ทีละตัวบนปลาย main ฉะนั้น hash เปลี่ยนหมด ถึงเนื้อหาจะเหมือนเดิม
- `git log` อ่านง่าย ไล่ย้อนดูได้เป็นเส้นตรง `git bisect` ก็ทำงานง่ายกว่า
- conflict ต้องแก้ทีละ commit ถ้า branch ยาวหลายสิบ commit จะเหนื่อย
- ถ้า branch นั้น push ไปแล้ว ต้อง `git push --force-with-lease` (อย่าใช้ `--force` เฉย ๆ)

**กฎข้อเดียวที่ห้ามพลาด: อย่า rebase branch ที่คนอื่นทำงานร่วมอยู่** เพราะ commit เปลี่ยน hash หมด คนที่ pull branch นั้นไว้แล้วจะเจอ history สองชุดปนกัน เสียเวลาแก้ทั้งทีม

## สูตรที่แนะนำ

ใช้ทั้งคู่ แยกตามจังหวะ

1. **ระหว่างทำ feature** ตอน sync กับ main ให้ใช้ `git pull --rebase` branch เราจะสะอาด ไม่มี merge commit ขยะ ตั้งเป็นค่าเริ่มต้นได้เลยด้วย `git config --global pull.rebase true`
2. **ตอนเอางานเข้า main** ให้ merge ผ่าน PR ไม่ต้อง rebase เข้า main ตรง ๆ จะได้มีร่องรอยว่า feature นี้เข้ามาตอนไหน ผ่าน PR ไหน
3. **branch ส่วนตัวที่ยังไม่ push** rebase/squash ได้ตามสบาย จัด commit ให้สวยก่อนเปิด PR

ส่วนตอน merge PR จะเลือก squash merge หรือ merge commit ขึ้นกับว่าทีมอยากเห็นอะไรใน log ของ main

- **squash**: 1 PR = 1 commit ใน main log สะอาดมาก revert ง่าย เหมาะกับทีมที่ commit ระหว่างทางเป็นพวก "wip", "fix typo"
- **merge commit (`--no-ff`)**: เก็บ commit ย่อยไว้ครบ เหมาะกับทีมที่เขียน commit message ดีอยู่แล้ว และอยากไล่ดูว่าแต่ละขั้นคิดอะไร

ถ้าทีมยังไม่เคยคุยเรื่องนี้กันจริงจัง ผมแนะนำเริ่มที่ `pull --rebase` + squash merge ก่อน เพราะคนในทีมไม่ต้องจำกฎเยอะ และพลาดแล้วแก้ง่ายที่สุด

ถ้าบอกขนาดทีมกับว่าตอนนี้ใช้ branch model แบบไหนอยู่ (trunk-based หรือ git flow) เดี๋ยวผมช่วยจัดเป็นกติกาสั้น ๆ ให้แปะไว้ใน CONTRIBUTING ได้ครับ
