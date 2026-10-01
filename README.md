# kon-thai

Claude Code plugin ที่ทำให้ Claude ตอบภาษาไทยแบบ senior dev คนไทยคุยกับเพื่อนร่วมทีม แทนภาษาไทยแบบแปลจากอังกฤษ

*A Claude Code plugin that makes Claude reply in natural, native-sounding Thai instead of translated Thai: two output styles (ผม/ครับ and หนู/ค่ะ), a polishing skill, and a reminder hook.*

## ติดตั้ง

พิมพ์ใน Claude Code

```
/plugin marketplace add Krittaphat-gofive/kon-thai
/plugin install kon-thai@kon-thai
```

แล้วเลือก style หนึ่งครั้ง โดยเพิ่มบรรทัดนี้ใน `~/.claude/settings.json`

```json
"outputStyle": "kon-thai:thai-native"
```

| style | persona |
|---|---|
| `kon-thai:thai-native` | แทนตัวเองว่าผม ลงท้ายครับ |
| `kon-thai:thai-native-kha` | แทนตัวเองว่าหนู ลงท้ายค่ะ ถ้าผู้ใช้คุยด้วย เค้า หรือ เรา ก็ใช้ตาม |

เปิด session ใหม่ แล้ว style จะมีผลตั้งแต่ข้อความแรก ถ้าตั้งผ่านคำสั่ง `/output-style` แทน ค่าจะไปอยู่ใน `.claude/settings.local.json` ของโปรเจกต์นั้นโปรเจกต์เดียว

อัปเดตเป็นเวอร์ชันล่าสุด

```bash
claude plugin marketplace update kon-thai
claude plugin update kon-thai@kon-thai
```

ถอนการติดตั้งด้วย `claude plugin uninstall kon-thai@kon-thai` แล้วลบบรรทัด `outputStyle` ออก

## มีอะไรบ้าง

มีสามชั้น เพราะ skill อย่างเดียวคุมทุกคำตอบไม่ได้ (Claude โหลดเนื้อหา skill เฉพาะตอนเรียกใช้)

| ชั้น | ไฟล์ | หน้าที่ |
|---|---|---|
| output style | `plugins/kon-thai/output-styles/` | กำหนดน้ำเสียงของทุกคำตอบ ส่งไปกับทุก request |
| hook | `plugins/kon-thai/hooks/` | เตือนสั้น ๆ ทุกครั้งที่ส่ง prompt กันหลุดตอนทำงานยาว |
| skill | `plugins/kon-thai/skills/thai-native-voice/` | รอบขัดเกลางานเขียนยาว เรียกด้วย `/kon-thai:thai-native-voice` |

สิ่งที่ต้องมีในเครื่อง
- hook ใช้ `bash` (macOS, Linux และ Windows ที่ติดตั้ง Git Bash) ถ้าไม่มี bash hook จะไม่ทำงาน แต่ส่วนอื่นยังใช้ได้
- linter ของ skill ใช้ Python 3 ถ้าไม่มี Python skill จะไล่ตรวจตาม checklist แทน

ข้อควรรู้
- เปิด output style ได้ทีละตัว ถ้าใช้ style อื่นอยู่ (เช่น Explanatory) จะถูกแทนที่
- output style ไม่มีผลกับ subagent ถ้า subagent ต้องเขียนภาษาไทยให้คนอ่าน ใส่ `kon-thai:thai-native-voice` ในฟิลด์ `skills:` ของ subagent นั้น
- ไม่ได้ตั้ง `language` ใน settings เพราะคำสั่งที่ Claude Code ใส่ให้รวม "comments" ด้วย อาจทำให้ comment ในโค้ดกลายเป็นภาษาไทย

## ใช้งาน

- ตอบทั่วไป: ไม่ต้องทำอะไร style ทำงานเอง
- เกลางานเขียน: พิมพ์ `/kon-thai:thai-native-voice` ตามด้วยข้อความหรือไฟล์ที่จะให้เกลา หรือพิมพ์ว่า "ช่วยเกลาภาษา…" Claude จะเรียก skill เอง
- ตรวจข้อความด้วย linter โดยตรง

```bash
python plugins/kon-thai/skills/thai-native-voice/scripts/thai_lint.py draft.md
python plugins/kon-thai/skills/thai-native-voice/scripts/thai_lint.py --persona kha --summary docs/*.md
```

linter รายงาน "จุดน่าสงสัย" ไม่ใช่ข้อผิด ทุกจุดต้องให้คนอ่านตัดสินอีกรอบ แต่ละจุดมีประเภทกำกับ
- `แปล` ร่องรอยภาษาแปล เช่น em dash, ถูก + กริยา กับเรื่องปกติ, มันเป็น… คะแนนหลักนับเฉพาะประเภทนี้
- `ทางการ` ภาษาราชการ เช่น อย่างไรก็ตาม, ดำเนินการ ในแชตควรเลี่ยง แต่ในจดหมายใช้ได้
- `บุคคล` ผิด persona เช่น persona ผม/ครับ แต่ใช้ ค่ะ หรือ persona หนู/ค่ะ แต่เขียน นะค่ะ (ต้องเป็น นะคะ)
- `house` ตัวสะกด ไม้ยมก การเว้นวรรค เป็นแบบที่ชุดนี้เลือกใช้ ไม่ใช่ร่องรอยภาษาแปล เพราะคนไทยเองก็เขียนต่างกันบ่อย

## ทดสอบและวัดผล

`eval/run_eval.py` รันชุดคำถามผ่าน `claude -p` แล้วนับจุดน่าสงสัยด้วย linter แต่ละ arm รันใน working dir ว่างของตัวเอง ปิด tool และไม่บันทึก session

ตัวรันแยกจากของที่ติดตั้งไว้ใน `~/.claude` เสมอ เพราะ `claude -p` อ่าน user settings ด้วย ถ้าไม่แยก control จะได้ style, hook และ skill ที่ติดตั้งไว้ไปด้วย ตัวรันเลยบังคับ `outputStyle` เป็น `default` ปิด hook ทุกตัว ปิด plugin kon-thai ที่ติดตั้งไว้ และตั้งชื่อ style กับ skill ที่ทดสอบใหม่เป็น `thai-native-eval` / `thai-native-voice-eval`

```bash
python eval/run_eval.py run --name r5 --arms control style        # รันเทียบสอง arm
python eval/run_eval.py run --name r5 --arms style --style plugins/kon-thai/output-styles/thai-native-kha.md --persona kha
python eval/run_eval.py report --name r5                          # สรุปผล
python eval/run_eval.py blind --name r5 --a control --b style     # ไฟล์ให้คนอ่านเทียบแบบไม่รู้ที่มา
python eval/run_eval.py reveal --name r5 --a control --b style    # นับผลหลังเลือกเสร็จ
python eval/calibrate.py --runs r5/control r5/style               # เทียบกับข่าว Blognone ที่คนไทยเขียน
```

ชุดคำถามมีสามไฟล์
- `eval/prompts.md` 20 ข้อ ใช้ปรับ style ได้
- `eval/heldout-prompts.md` 14 ข้อ ใช้วัดผลอย่างเดียว ห้ามเอาคำตอบชุดนี้ไปทำตัวอย่างใน style ไม่งั้นจะวัดไม่ได้ว่า style ใช้กับคำถามที่ไม่เคยเห็นได้จริงไหม
- `eval/polish-prompts.md` ทดสอบ skill ขัดเกลา ใช้กับ `--arms polish-control polish-skill polish-skill-auto`

`eval/calibrate.py` ดึงข่าว Blognone (pythainlp/blognone_news, CC BY 3.0) มา 1,500 ข่าว แล้ววัดว่าคนไทยใช้แต่ละคำถี่แค่ไหน กฎไหนที่คนไทยเองก็ใช้บ่อย ไม่ควรตั้งเป้าให้เป็นศูนย์

ทุกครั้งที่แก้ style หรือ skill ให้รันทดสอบซ้ำ แล้วเพิ่ม `version` ใน `plugins/kon-thai/.claude-plugin/plugin.json` ก่อน push ไม่งั้นคนที่ติดตั้งไว้จะไม่ได้อัปเดต ตรวจโครง plugin ด้วย `claude plugin validate .` ก่อนทุกครั้ง ตัวเลขจาก linter บอกได้แค่เรื่องที่นับได้ ส่วนความเป็นธรรมชาติจริง ๆ ต้องอ่านเองด้วยไฟล์ blind ฉบับก่อนหน้าของ style เก็บไว้ใน `eval/styles/`

## ผลทดสอบ (1 ต.ค. 2569, Opus 5.5)

ตัวเลขเป็นจำนวนครั้งต่อ 1,000 ตัวอักษรไทย วัดด้วย linter ตัวล่าสุด

### ชุด held-out 14 ข้อ (style ไม่เคยเห็นคำถามชุดนี้)

| | ข่าว Blognone (คนไทยเขียน) | control | style v1 | style v2 |
|---|---:|---:|---:|---:|
| คะแนนภาษาแปล | 0.84 | 4.72 | 0.11 | 0.11 |
| em dash | 0 | 3.59 | 0 | 0 |
| ถูก + กริยา กับเรื่องปกติ | 0.43 | 1.07 | 0.11 | 0.11 |
| ครับ | | 0.97 | 1.90 | 1.36 |
| ปิดท้ายด้วยการเสนอช่วย | | 8/14 | 11/14 | 7/14 |

v1 แก้ภาษาแปลได้ แต่ทำให้ทุกคำตอบปิดท้ายด้วยการเสนอช่วยจนเป็นแม่แบบ v2 แก้เรื่องนี้ โดยยังได้คะแนนภาษาแปลเท่าเดิม ผลเต็มอยู่ใน `eval/runs/h3/`, `eval/runs/h4/` และ `eval/corpus/heldout-compare.md`

style แบบหนู/ค่ะ (held-out 6 ข้อ กับชุดทดสอบ persona 3 ข้อ): คะแนนภาษาแปล 0 ไม่มี em dash ส่วนใหญ่ละสรรพนาม ตอนที่ต้องแทนตัวเองใช้ "หนู" เช่น "ข้อมูลที่หนูไม่มี" และไม่มี "ดิฉัน", "ผม" หรือ "ครับ" หลุดมาเลย รอบก่อนหน้า Claude ใส่ "คะ" ผิดในประโยคบอกเล่าที่มีคำถามซ้อน เช่น "เดี๋ยวบอกได้ว่าควรใช้ข้อไหนคะ" 3 จุด พอแก้กฎใน style แล้วเหลือ 0 ผลเต็มอยู่ใน `eval/runs/h7-kha/` กับ `eval/runs/x2-kha/`

### ชุดแรก 20 ข้อ (รันตอนยังไม่ได้ติดตั้ง และยังมี hook ของ superpowers ทำงานอยู่)

| | control | style v1 |
|---|---:|---:|
| คะแนนภาษาแปล | 6.94 | 0.18 |
| em dash (ครั้ง) | 143 | 0 |
| ปิดท้ายด้วยการเสนอช่วย | 10/20 | 19/20 |

### skill เกลาภาษา (3 ข้อความจากคำตอบเดิมที่มีภาษาแปลเยอะที่สุด)

| | ต้นฉบับ | เกลาโดยไม่มี skill | เกลาด้วย skill v2 |
|---|---:|---:|---:|
| คะแนนภาษาแปลของตัวงาน | 12.57 | 6.32 | 0 |

ถ้าไม่มี skill Claude มักคง em dash ไว้ทั้งหมด (2 ใน 3 ข้อ) ผลเต็มอยู่ใน `eval/runs/p5/`

ผลที่ใช้ไม่ได้เพราะตอนนั้นตัวรันยังไม่ได้แยกจากของที่ติดตั้งไว้ เก็บไว้ใน `eval/runs/_contaminated/` พร้อมเหตุผล

## ที่มาของกฎ

กฎในชุดนี้มาจากสี่ทาง
- คำตอบจริงของ Claude ตอนยังไม่มี style (ดูใน `eval/runs/`)
- แหล่งอ้างอิงภาษาไทย ได้แก่ สรุปสัมมนาการใช้ภาษาไทยในบทแปลของราชบัณฑิตยสถาน หลักเกณฑ์การเว้นวรรคของราชบัณฑิตยสถาน Microsoft Thai Style Guide แนวทางการเขียนของ Blognone และ skill kien-thai
- ข้อความที่ dev ไทยเขียนจริงใน Blognone, Pantip และบล็อก กับผลวัดเทียบข่าว Blognone (`research/2026-10-01-thai-online-writing.md`, `eval/corpus/calibration.md`)
- ความเห็นของ ChatGPT ที่ถามครั้งเดียว (`research/2026-10-01-codex-consult.md`) เอามาใช้เฉพาะข้อที่มีหลักฐานอื่นรองรับ

รายละเอียดกับลิงก์อยู่ใน `plugins/kon-thai/skills/thai-native-voice/references/`

## License

MIT ดู [LICENSE](LICENSE)
