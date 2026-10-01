ยังไม่ได้เปิดดูโปรเจกต์จริงในรอบนี้ เลยตอบจากสาเหตุที่เจอบ่อยสุดบน Windows ก่อนนะคะ ส่วนใหญ่มาจาก antivirus สแกน node_modules กับ postinstall ที่โหลด binary ไม่ค่อยใช่เน็ตช้าอย่างที่คิดกัน

## หาก่อนว่าช้าช่วงไหน

รันด้วย `npm install --timing` แล้วดู stage ที่ค้างนาน npm จะเขียนไฟล์ timing ไว้ใน `_logs` ใต้ cache folder (`npm config get cache`)

- ค้างที่ `idealTree:buildDeps` นาน แปลว่าเสียเวลาตอน resolve version กับยิง registry
- ค้างที่ `reify:extract` หรือ `reify:move` นาน แปลว่าคอขวดอยู่ที่การเขียนไฟล์ลงดิสก์ ซึ่งเกือบทุกเคสคือ antivirus หรือดิสก์ช้า
- ค้างตอนท้ายหลังไฟล์ลงครบแล้ว คือ `npm audit` ยิง API

## ถ้าช้าตอนเขียนไฟล์

node_modules มีไฟล์เล็กเป็นแสนไฟล์ Defender สแกนทีละไฟล์ตอนสร้าง ทำให้ install ช้าขึ้นเท่าตัวได้สบาย ๆ เพิ่ม exclusion ให้โฟลเดอร์โปรเจกต์ cache และ process ของ node (ต้องรัน PowerShell แบบ admin)

```powershell
Add-MpPreference -ExclusionPath "E:\gofive"
Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\npm-cache"
Add-MpPreference -ExclusionProcess "node.exe"
```

อีกสองอย่างที่ทำให้ช่วงนี้ช้าคือโปรเจกต์อยู่บน HDD หรืออยู่ในโฟลเดอร์ที่ OneDrive sync อยู่ ถ้า `E:` เป็นจานหมุน ย้ายมาไว้ SSD จะเห็นผลชัดกว่าการแก้อย่างอื่นทั้งหมดรวมกัน

## ถ้าช้าตอน resolve

- ถ้ามี `package-lock.json` อยู่แล้วและไม่ได้ตั้งใจอัปเดต dependency ให้ใช้ `npm ci` แทน จะข้ามขั้นตอน resolve ไปเลย ลบ node_modules แล้วติดตั้งตาม lock ตรง ๆ
- ลองปิดงานที่ไม่จำเป็นดูก่อน: `npm install --no-audit --no-fund` ตัว audit ยิง registry ตอนท้ายแล้วบางทีค้างเป็นนาที
- ถ้า dependency มี peer version ที่ขัดกัน npm จะ backtrack ไล่ลองหลายเวอร์ชัน อันนี้ช้าแบบรู้สึกได้ ดูได้จาก log ว่าดึง metadata ของ package เดิมซ้ำหลายรอบ

## ถ้าช้าเพราะ postinstall

พวก puppeteer, playwright, sharp, electron, sass-embedded จะโหลด binary หลายร้อย MB ทุกครั้งที่ cache ไม่โดน ถ้ามีตัวพวกนี้ใน `package.json` ตั้ง env var ให้ข้ามหรือชี้ไป cache กลาง เช่น `PUPPETEER_SKIP_DOWNLOAD=true` แล้วค่อยติดตั้ง browser แยกครั้งเดียว

## ตัวเลือกที่แก้ได้ยาวกว่า

ย้ายไป pnpm ถ้าทีมโอเค pnpm ใช้ hardlink จาก store กลางแทนการ copy ไฟล์จริง เลยไม่ต้องเขียนไฟล์เป็นแสนไฟล์ใหม่ทุกโปรเจกต์ บน Windows ต่างกันเยอะมาก ติดตั้งด้วย `corepack enable` แล้วใช้ `pnpm import` แปลง lockfile เดิมได้

ถ้าส่งไฟล์ timing หรือ `package.json` มาให้ดู เดี๋ยวชี้ให้ว่าตัวไหนเป็นต้นเหตุจริงค่ะ
