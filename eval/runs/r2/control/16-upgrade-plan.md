ย้าย Angular 17 → 20 เป็นการข้าม 3 major (17→18→19→20) หลักสำคัญที่สุดคือ **ต้องไล่ทีละ major ห้ามกระโดดข้าม** เพราะ `ng update` จะรัน migration schematics ของแต่ละเวอร์ชันตามลำดับ ถ้าข้ามไปเลยจะไม่ได้ schematic กลางทางและจะต้องมาแก้มือ

## 1. เตรียมก่อนเริ่ม (pre-flight)

- **Freeze feature work** — schematics จะแตะไฟล์หลายร้อยไฟล์ ถ้ามี branch ค้างเยอะจะ conflict หนักมาก เคลียร์/merge ให้หมดก่อน
- **CI ต้องเขียวและ test ต้องเชื่อถือได้** — ถ้า test coverage บาง การ upgrade จะกลายเป็นการเดา แนะนำให้มี smoke test ของ flow หลักอย่างน้อย
- **แยก branch ต่อ 1 major** (`chore/ng18`, `chore/ng19`, …) แล้ว merge ทีละตัว อย่ารวบเป็น PR เดียว
- **Node.js** — Angular 20 ต้องการ Node 20.11.1+ / 22.11+ / 24 (Node 18 ถูกตัดแล้ว) เช็ค CI image, Dockerfile, `engines` ใน package.json, และ `.nvmrc`
- **TypeScript** — v18 ต้อง TS ~5.4, v19 ~5.5–5.6, v20 ต้อง 5.8+ ถ้าโค้ดมี `any` เยอะหรือปิด strict ไว้ TS ที่ใหม่ขึ้นมักจะเจอ type error เพิ่ม
- **RxJS** — RxJS 6 ถูกตัดใน v18 ต้องอยู่ที่ 7.x ก่อน
- **สำรวจ dependency ทั้งหมด** ว่าตัวไหนรองรับ Angular 20 — ตัวที่ต้องเช็ค: Angular Material/CDK, NgRx, Nx (ถ้าใช้), PrimeNG/ng-zorro/ng-bootstrap, `angular-eslint`, `jest-preset-angular`, ngx-translate, chart libs ตัวที่ยังไม่รองรับคือ blocker จริง ให้ตัดสินใจล่วงหน้าว่าจะรอ / หา alternative / fork

## 2. งานจริงในแต่ละช่วง

**17 → 18**
ค่อนข้างราบรื่น ส่วนใหญ่เป็น automatic migration หลัก ๆ คือ built-in control flow (`@if`/`@for`) และ deferrable views เป็น stable, Material 3 stable, package `@angular/build` เริ่มถูกแยกออกมา

**18 → 19**
เป็นช่วงที่ schematics แตะโค้ดเยอะที่สุด:
- `standalone: true` กลายเป็นค่า default → schematic จะไล่ลบ flag ออกจากทุก component และใส่ `standalone: false` ให้ตัวที่ยังอยู่ใน NgModule (diff ใหญ่ แต่ปลอดภัย)
- `allowSignalWrites` ใน `effect()` ถูกถอด (เขียน signal ใน effect ได้เลยแล้ว) และ **timing ของ effect เปลี่ยน** — ถ้าโค้ดคุณพึ่งลำดับการรันของ effect ตรงนี้คือจุดที่พังแบบเงียบ ๆ ให้ไล่ดูเอง schematic ช่วยไม่ได้
- signal-based `input()` / `output()` / `viewChild()` stable

**19 → 20**
- **Karma ถูก deprecate** — ยังใช้ได้อยู่ แต่ควรวางแผนย้ายไป Vitest/Jest ในรอบถัดไป (ยังไม่ต้องทำในรอบนี้)
- Zoneless change detection เป็น developer preview — **ไม่จำเป็นต้องทำตอนนี้** อย่าเอามารวมใน PR upgrade
- Angular Material มี theming API ใหม่ (`mat.theme()`) ถ้าคุณ custom theme ไว้เยอะ ตรงนี้กินเวลา
- Style guide ใหม่เปลี่ยนวิธีตั้งชื่อไฟล์ (`user.ts` แทน `user.component.ts`) — มีผลกับไฟล์ที่ generate ใหม่เท่านั้น ของเดิมไม่ต้องแตะ

## 3. จุดเสี่ยงที่กินเวลามากที่สุด

เรียงตามโอกาสที่จะทำให้ timeline บาน:

1. **Custom webpack / Module Federation** — ถ้าใช้ `@angular-builders/custom-webpack`, `ngx-build-plus` หรือ Module Federation แบบ webpack นี่คือ blocker อันดับหนึ่ง เพราะ application builder ตัวใหม่ใช้ esbuild/Vite ไม่ใช่ webpack ต้องประเมินแยกเป็นงานต่างหากเลย
2. **การย้าย builder** `browser` → `application` — ถ้า project ยังใช้ `@angular-devkit/build-angular:browser` อยู่ จะเจอเรื่อง CommonJS dependency warnings, polyfills ที่เปลี่ยนรูปแบบ config, และ output path structure ที่เปลี่ยน (`dist/browser/`)
3. **SSR** — ถ้ายังใช้ `@nguniversal/*` ต้องย้ายมา `@angular/ssr` ก่อน (เป็น migration ของ v17 ที่หลายโปรเจกต์ค้างไว้)
4. **Material theming** ถ้า custom หนัก
5. **Third-party lib ที่ตามไม่ทัน**

## 4. ลำดับงานที่แนะนำ

```bash
# ต่อ 1 major: branch ใหม่ → update → build → test → merge
ng update @angular/core@18 @angular/cli@18
ng update @angular/material@18   # แยกทีละ package
npm run build && npm test
```

เคล็ดลับ: หลีกเลี่ยง `--force` และ `--legacy-peer-deps` ถ้าทำได้ เพราะมันจะซ่อนปัญหา peer dependency ไว้ให้ไประเบิดตอน runtime แทน ถ้าต้องใช้ ให้จดไว้ว่าใช้กับ package ไหนเพราะอะไร

**แยกเป็น PR ทีหลัง ไม่ต้องทำในรอบ upgrade:** control flow migration (`ng generate @angular/core:control-flow`), `inject()` migration, standalone migration, signal inputs migration ทั้งหมดนี้เป็น optional และทำย้อนหลังได้ การยัดรวมใน PR upgrade จะทำให้ review ไม่ได้และหา regression ไม่เจอ

## 5. ประมาณการ

สำหรับโปรเจกต์ขนาดกลางที่ไม่มี custom webpack และ dependency ไม่แปลก: **ประมาณ 3–5 วันทำงาน** สำหรับทั้ง 3 major รวม regression test ถ้ามี custom webpack / Module Federation / SSR ให้บวกไปอีกเท่าตัวเป็นอย่างน้อย

---

รายการ breaking change แบบครบถ้วนอยู่ที่ **angular.dev/update-guide** — เลือก from 17 to 20 แล้วติ๊ก complexity level ให้ตรงกับโปรเจกต์ อันนั้นคือ source of truth ที่ควรใช้เป็น checklist จริงตอนลงมือ

ถ้าบอกได้ว่าโปรเจกต์ใช้ builder ตัวไหน มี SSR ไหม และใช้ UI library อะไร ผมช่วยไล่ประเมินจุดเสี่ยงเฉพาะเจาะจงให้ได้ครับ
