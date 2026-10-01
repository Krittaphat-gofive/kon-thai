# git rebase vs git merge

## แก่นความต่างจริง ๆ

**merge** = เอาสองสายมาบรรจบกันด้วย commit ใหม่ 1 ตัว (merge commit) — ประวัติเดิมไม่ถูกแตะ commit hash ไม่เปลี่ยน

**rebase** = ยก commit ของเราไป "ต่อท้าย" ฐานใหม่ แล้วเขียน commit ใหม่ทั้งชุด — ประวัติเป็นเส้นตรง แต่ **hash เปลี่ยนหมด** (คนละ commit แล้ว แม้เนื้อหาเหมือนเดิม)

```
เริ่มต้น:           A---B---C  main
                         \
                          D---E  feature

merge:              A---B---C---M  main
                         \     /
                          D---E

rebase feature:     A---B---C  main
                             \
                              D'--E'  feature   (D,E ถูกเขียนใหม่)
```

## ข้อแลกเปลี่ยน

| | merge | rebase |
|---|---|---|
| ประวัติ | ตรงตามที่เกิดจริง แต่เป็นร่างแห | เป็นเส้นตรง อ่าน `git log` ง่าย |
| ความปลอดภัย | ปลอดภัยเสมอ | เขียนประวัติใหม่ — อันตรายถ้า branch ถูกแชร์ |
| conflict | แก้ครั้งเดียวจบ | อาจต้องแก้ซ้ำทีละ commit |
| `git bisect` / `revert` | merge commit ทำให้งงได้ | ทำงานสะอาดกว่า |
| ร่องรอยว่าใครแตกสาขาเมื่อไหร่ | เก็บไว้ | หายไป |

## กฎทองข้อเดียวที่ห้ามพลาด

> **อย่า rebase branch ที่ push ขึ้นไปแล้วและมีคนอื่นทำงานอยู่ด้วย**

เพราะ hash เปลี่ยน คนอื่นจะ pull มาแล้วประวัติชนกันทันที ต้องมานั่งแก้กันทั้งทีม — rebase ใช้กับ branch ที่ "เป็นของเราคนเดียว" เท่านั้น

## ที่แนะนำสำหรับทีม

ลูกผสม — ใช้ทั้งคู่คนละจังหวะ:

**1. ระหว่างทำ feature — ใช้ rebase ดึง main ล่าสุด**
```bash
git config --global pull.rebase true     # pull = rebase เป็น default
git fetch origin && git rebase origin/main
git push --force-with-lease              # ไม่ใช่ --force เฉย ๆ
```
ทำให้ branch เราอยู่บนฐานล่าสุดเสมอ ลด conflict ก้อนใหญ่ตอน merge PR

**2. ตอน merge PR เข้า main — ใช้ merge**
- **Squash merge** ถ้าทีมอยากได้ 1 PR = 1 commit ใน main (แนะนำถ้าทีมยัง commit แบบ "wip", "fix typo" เยอะ)
- **Merge --no-ff** ถ้า commit ในแต่ละ PR เขียนดีอยู่แล้วและอยากเก็บไว้

ผลลัพธ์: `main` สะอาด อ่านง่าย ย้อน revert ได้ทีละฟีเจอร์ แต่ไม่มีใครต้องเสี่ยงกับประวัติที่ถูกเขียนใหม่บน branch ร่วม

**3. เปิด rerere ช่วยจำวิธีแก้ conflict**
```bash
git config --global rerere.enabled true
```
มีประโยชน์มากเวลา rebase branch อายุยาวแล้วเจอ conflict เดิมซ้ำ

## ตัวแปรที่อาจเปลี่ยนคำตอบ

ถ้าทีมอยู่ในสาย **audit/compliance เข้ม** ที่ต้องพิสูจน์ได้ว่า commit ไหนเกิดเมื่อไหร่จริง ๆ → ใช้ merge อย่างเดียว ห้าม rebase ทั้งหมด เพราะ rebase ทำให้ timestamp ของการ "เกิดจริง" กับ "ลำดับใน log" ไม่ตรงกัน

ถ้าทีมเล็กและทุกคนถนัด git อยู่แล้ว → rebase แล้ว fast-forward เข้า main ไปเลยก็ได้ ประวัติจะเป็นเส้นตรงล้วน

## ท่าแก้เวลา rebase พัง

```bash
git rebase --abort        # ถอยกลับจุดเริ่ม ปลอดภัยเสมอ
git rebase --continue     # แก้ conflict เสร็จแล้วไปต่อ
git reflog                # หา commit เดิมถ้าเผลอทำหาย — กู้ได้เกือบทุกกรณี
```

บอกได้ว่าทีมขนาดไหนและ review ผ่าน GitHub/GitLab/Azure DevOps ตัวไหน เดี๋ยวช่วยเขียนเป็น branching policy กับ setting ที่ต้องเปิดในหน้า repo ให้ตรงกับที่ใช้จริง
