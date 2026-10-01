## สรุปความต่างแบบสั้น

**merge** = เอาประวัติสองสายมาบรรจบกัน แล้วสร้าง merge commit ที่มี parent สองตัว ประวัติเดิมไม่ถูกแตะต้องเลย

**rebase** = ยกคอมมิตของเราไปวางต่อท้าย base ใหม่ โดย "เขียนใหม่" ทุกคอมมิต (SHA เปลี่ยนหมด แม้เนื้อหาเหมือนเดิม) ได้ประวัติเป็นเส้นตรง

ภาพประกอบ — สมมติแตก `feature` จาก `main` แล้ว `main` เดินหน้าไป:

```
# ก่อน
A---B---C  main
     \
      D---E  feature

# git merge main (ยืนอยู่บน feature)
A---B---C-------M  main/feature
     \         /
      D-------E

# git rebase main
A---B---C---D'---E'  feature   (D' E' เป็นคอมมิตใหม่คนละตัวกับ D E)
```

| | merge | rebase |
|---|---|---|
| ประวัติ | จริงตามที่เกิด แตกกิ่งเยอะ | เส้นตรง อ่านง่าย |
| SHA เดิม | คงอยู่ | เปลี่ยนใหม่หมด |
| conflict | แก้ครั้งเดียวตอน merge | อาจต้องแก้ทีละคอมมิต |
| ปลอดภัยกับ branch ที่แชร์ | ปลอดภัย | **อันตราย** ต้อง force push |
| `git bisect` / `git blame` | รกกว่านิดหน่อย | สะอาดกว่า |
| ย้อนกลับ | `git revert -m 1` | ใช้ `git reflog` |

## กฎเหล็กข้อเดียวที่ต้องจำ

**ห้าม rebase branch ที่คนอื่นดึงไปใช้แล้ว** — เพราะ SHA เปลี่ยน คนอื่น pull มาจะเจอประวัติซ้อนกันพังทั้งทีม  
rebase ได้เฉพาะคอมมิตที่ยังอยู่ใน local หรือ feature branch ที่มีเราคนเดียวทำ

## ที่ผมแนะนำสำหรับทีมส่วนใหญ่: ใช้ทั้งคู่ คนละหน้าที่

**1. ซิงก์งานตัวเอง → rebase**
```powershell
git config --global pull.rebase true   # ตั้งครั้งเดียว กัน merge commit ขยะจาก pull
git fetch origin
git rebase origin/main                 # อัปเดต feature branch ให้ทันก่อนเปิด PR
```
ช่วยกำจัด merge commit ประเภท "Merge branch 'main' into 'main'" ที่ไม่มีความหมายอะไรเลย

**2. เอางานเข้า main → merge ผ่าน PR** (`--no-ff` หรือ squash merge)  
จะได้เห็นชัดว่า feature นี้เข้ามาตอนไหน ประกอบด้วยอะไรบ้าง และ revert ทั้งก้อนได้ง่าย

**3. ก่อนเปิด PR ให้จัดคอมมิตตัวเองให้สวย**
```powershell
git rebase -i origin/main   # ยุบ "fix typo", "wip", "แก้อีกรอบ" ให้เหลือคอมมิตที่สื่อความหมาย
```

**เลือก merge strategy บน PR ยังไง:**
- **Squash merge** — เหมาะที่สุดถ้าทีมยังไม่ชินกับการเขียน commit message ดีๆ ได้ main ที่สะอาด 1 PR = 1 คอมมิต revert ง่ายมาก (ผมแนะนำอันนี้เป็น default ถ้าไม่แน่ใจ)
- **Merge commit (`--no-ff`)** — เหมาะเมื่อทีมเขียนคอมมิตเป็นระเบียบอยู่แล้ว และอยากเก็บรายละเอียดระหว่างทาง
- **Rebase merge** — ได้เส้นตรงสวยสุด แต่เสียความสามารถในการ revert ทั้ง feature ด้วยคำสั่งเดียว

## ข้อควรรู้เพิ่มเติม

- ถ้า rebase แล้วต้อง push ใช้ `git push --force-with-lease` **ห้ามใช้** `--force` เฉยๆ เพราะ `--force-with-lease` จะไม่ทับงานคนอื่นที่เพิ่ง push เข้ามา
- เปิด `git config --global rerere.enabled true` — Git จะจำวิธีแก้ conflict ที่เคยแก้แล้ว ช่วยได้มากเวลา rebase branch ยาวๆ
- ล็อก branch `main` / `develop` ไว้ใน GitHub/GitLab (ห้าม force push) จะกันอุบัติเหตุได้เกือบหมด
- rebase พลาดไม่ใช่จุดจบ — `git reflog` แล้ว `git reset --hard HEAD@{n}` กู้คืนได้เสมอ

**ถ้าทีมยังใหม่กับ Git** ให้เริ่มจาก merge อย่างเดียวก่อนก็ได้ครับ ประวัติรกหน่อยแต่ไม่มีใครทำงานหาย พอทุกคนเข้าใจ reflog กับ force-with-lease แล้วค่อยเพิ่ม rebase เข้ามา — ต้นทุนความผิดพลาดของ rebase สูงกว่าชัดเจน
