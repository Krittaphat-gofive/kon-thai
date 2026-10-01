บน Windows สาเหตุที่เจอบ่อยที่สุดคือ Defender สแกน `node_modules` ค่ะ

ตอน install npm เขียนไฟล์เล็ก ๆ ลงดิสก์เป็นแสนไฟล์ Defender real-time protection เปิดอ่านทุกไฟล์ที่เขียนใหม่ งานที่ควรจบใน 1 นาทีเลยยืดเป็น 5-10 นาที ลองปิด real-time ชั่วคราวแล้ว install ใหม่ ถ้าเร็วขึ้นชัดเจนก็คือตัวนี้ แก้ถาวรด้วยการตั้ง exclusion ให้โฟลเดอร์งานกับ npm cache

```powershell
Add-MpPreference -ExclusionPath 'E:\gofive'
Add-MpPreference -ExclusionPath "$env:LocalAppData\npm-cache"
```

## วิธีดูว่าเวลาหมดไปกับอะไร

```powershell
npm install --timing
```

เสร็จแล้วจะได้ไฟล์ `*-timing.json` ในโฟลเดอร์ `_logs` (หาที่อยู่ด้วย `npm config get cache`) ในไฟล์จะแยกเวลาเป็นช่วง เช่น `idealTree` คือตอน resolve dependency `reify` คือตอนเขียนไฟล์ลงดิสก์ ดูว่าก้อนไหนกินเวลามากสุดก่อน จะได้ไม่ต้องเดา

## สาเหตุอื่นที่เจอบ่อย

- **ไม่มี `package-lock.json` หรือลบทิ้งบ่อย** npm ต้อง resolve ทั้ง tree ใหม่ ยิงขอ metadata จาก registry เป็นร้อยรอบ ถ้ามี lockfile อยู่แล้วและอยากได้ของตรงตาม lock ใช้ `npm ci` จะเร็วกว่า
- **peer dependency ขัดกัน** npm จะย้อนกลับไปลองเวอร์ชันอื่นหลายรอบ ช่วง `idealTree` จะนานผิดปกติ ดูได้จาก warning ตอน install
- **postinstall ที่โหลด binary** พวก puppeteer (โหลด Chromium), sharp, electron หรืออะไรที่ build ผ่าน node-gyp ตัวนี้ช้าที่เน็ตกับการ compile ไม่เกี่ยวกับ npm
- **git dependency** ถ้าใน `package.json` มี `git+https://...` npm ต้อง clone ใหม่ แคชไม่ค่อยช่วย
- **โฟลเดอร์อยู่ใน OneDrive หรือ network drive** OneDrive จะพยายาม sync ทุกไฟล์ใน `node_modules` ตามไปด้วย ย้ายโปรเจกต์ออกมาไว้นอกโฟลเดอร์ sync
- **registry ผ่าน proxy ของบริษัท** เช็กด้วย `npm config get registry` ถ้าชี้ไป Nexus หรือ Artifactory ภายใน ลองเทียบกับ `https://registry.npmjs.org/` ดูว่าต่างกันเยอะไหม

## ตัวที่ลดเวลาได้ทันที

ปิด audit กับ fund ตอน install ปกติ ส่วนนี้ยิง request เพิ่มตอนท้ายทุกครั้ง

```powershell
npm install --no-audit --no-fund
```

ถ้าอยากให้เป็นค่า default ใส่ใน `.npmrc` ของเครื่อง แล้วค่อยรัน `npm audit` แยกตอนจะ release

ถ้าแก้ทั้งหมดแล้วยังช้า ลองย้ายไป pnpm pnpm ใช้ hardlink จาก store กลางแทนการ copy ไฟล์จริง บน Windows ต่างกันชัดมากเพราะตัดงานเขียนดิสก์ออกไปเกือบหมด

ถ้าส่งไฟล์ timing หรือ `package.json` มาให้ดู เดี๋ยวชี้ให้ว่าช้าตรงไหนค่ะ
