#!/usr/bin/env python3
"""thai_lint.py — หาร่องรอยภาษาแปลในข้อความภาษาไทย

ผลที่ได้เป็น "จุดน่าสงสัย" ไม่ใช่ error ทุกจุดต้องให้คนอ่านตัดสินอีกรอบ
คะแนนหลักนับเฉพาะร่องรอยภาษาแปล ส่วนภาษาทางการ persona และ house style (ตัวสะกด ไม้ยมก
การเว้นวรรค) แยกนับต่างหาก เพราะคนไทยเองก็เขียนแบบนั้นกันบ่อย
เช่น "ถูก" อาจแปลว่าถูกต้องหรือราคาถูกก็ได้ ส่วน code block, inline code
และ URL ข้ามไปทั้งหมด

วิธีใช้:
  python thai_lint.py answer.md other.md
  python thai_lint.py -                  อ่านจาก stdin
  python thai_lint.py --json answer.md   ผลแบบ JSON ไว้ให้สคริปต์อื่นใช้ต่อ
  python thai_lint.py --summary *.md     แสดงแค่ตัวเลขสรุปของแต่ละไฟล์
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict

THAI = "฀-๿"
THAI_LETTER = "ก-ๅ็-๎"  # ตัวอักษรไทยทั้งหมด ยกเว้น ๆ และตัวเลขไทย


@dataclass
class Rule:
    id: str
    severity: str  # high = ภาษาแปลชัด, medium = มักเป็นภาษาแปล, info = แล้วแต่บริบท ไม่นับคะแนน
    pattern: str
    message: str
    kind: str = "แปล"  # แปล = ร่องรอยภาษาแปล, ทางการ = ภาษาราชการ, บุคคล = persona, house = แบบที่ชุดนี้เลือกใช้


# ถูก + กริยาเชิงลบ เป็นภาษาไทยปกติ ไม่นับ
ADVERSE = "ขโมย|จับ|ทำร้าย|แฮ็ก|โจมตี|โกง|หลอก|ด่า|ตำหนิ|ลงโทษ|ทำโทษ|ไล่ออก|ปฏิเสธ|บล็อก|แบน|ยิง|ฆ่า|ปล้น|รังแก|เอาเปรียบ|ละเมิด"

# ระดับความรุนแรงเทียบกับข่าว Blognone ที่คนไทยเขียนเอง (eval/calibrate.py)
# กฎที่คนไทยใช้ถี่กว่า Claude อยู่แล้ว เช่น สามารถ ไม่นับเป็นร่องรอยภาษาแปล
RULES = [
    # --- โครงสร้างประโยคแบบอังกฤษ ---
    Rule("ถูก-passive", "high",
         rf"(?<!ราคา)(?<!ของ)ถูก(?!ต้อง|ใจ|กว่า|ที่สุด|มาก|ลง|\s*ๆ|ที่|ทาง|จุด|วิธี|แล้ว|ไหม|เหรอ|หรือ|นะ|ครับ|ค่ะ|คะ|ด้วย|และ|เลย|กัน|คอ|หวย|รางวัล|$|{ADVERSE})",
         "ถูก + กริยา กับเรื่องปกติ ลองเขียนแบบไม่มีประธาน ใส่ผู้กระทำเฉพาะตอนที่รู้แน่ว่าใครทำ"),
    Rule("ทำการ", "high", r"(?<!วัน)(?<!เวลา)ทำการ(?!บ้าน)",
         "ตัด ทำการ ทิ้ง เช่น ทำการติดตั้ง → ติดตั้ง"),
    Rule("มีความ", "medium", r"มีความ(?!หมาย|รู้|สุข|ทุกข์|ลับ|ผิด|คิด|เห็น|จำ)",
         "ตัด มีความ ได้ไหม เช่น มีความซับซ้อน → ซับซ้อน"),
    Rule("มันเป็น", "high", r"มัน(?:เป็น|คือ)",
         "ขึ้นต้นแบบ It is… ให้พูดถึงตัวเรื่องเลย เช่น มันเป็นอะไรที่ยาก → เรื่องนี้ยาก"),
    # มัน ที่หมายถึงสิ่งที่เพิ่งพูดถึง dev ไทยใช้กันปกติ เลยเป็นแค่ข้อสังเกต ส่วน มันเป็น/มันคือ ยังนับ
    Rule("มัน-แทน-it", "info",
         rf"(?<!น้ำ)(?<!ไข)(?<!ความ)มัน(?!ฝรั่ง|สมอง|สำปะหลัง|เทศ|ส์|เป็น|คือ|[่้๊๋])",
         "มัน ใช้แทนสิ่งที่เพิ่งพูดถึงได้ แต่ถ้าใช้ถี่หรือไม่ชัดว่าหมายถึงอะไร ให้เรียกชื่อสิ่งนั้น"),
    Rule("ได้รับการ", "medium", r"ได้รับการ",
         "ได้รับการ + กริยา ก็คือ passive อีกแบบ ลองเขียนเป็นประโยค active"),
    Rule("ง่ายต่อการ", "high", r"(?:ง่าย|ยาก)(?:ต่อ|แก่)การ",
         "สลับเป็น กริยา + ง่าย/ยาก เช่น ง่ายต่อการเข้าใจ → เข้าใจง่าย"),
    Rule("ในความคิดของ", "high", r"ในความคิด(?:เห็น)?ของ",
         "เขียนว่า X คิดว่า… แทน"),
    # ต้องอยู่ต้นวลี ไม่งั้นจะไปจับ อาการที่ / รายการที่ / ต้องการที่
    Rule("การที่", "info", r"(?:^|(?<=[\s(\"']))การที่",
         "การที่…นั้น เป็นโครงประโยคแบบอังกฤษ ลองขึ้นต้นด้วยตัวเรื่องเลย"),
    Rule("เพื่อที่จะ", "medium", r"เพื่อที่จะ|ในการที่จะ",
         "ใช้ เพื่อ หรือ จะได้ ก็พอ"),
    Rule("ให้แน่ใจว่า", "medium", r"(?:ตรวจสอบ|เช็ก|เช็ค)?ให้แน่ใจว่า|ทำให้มั่นใจว่า",
         "แปลมาจาก ensure that ลองพูดตรง ๆ เช่น ตรวจสอบให้แน่ใจว่าปิด connection → อย่าลืมปิด connection"),
    Rule("ให้ฉัน-let-me", "high", r"(?:^|\s)ให้(?:ฉัน|ผม)(?:อธิบาย|ช่วย|ลอง|ดู|สรุป|แสดง|แนะนำ|บอก)",
         "แปลมาจาก Let me… ใช้ ขอ… หรือ เดี๋ยว… หรือเข้าเรื่องเลย"),
    Rule("คุณสามารถ", "medium", r"คุณสามารถ",
         "ละ คุณ แล้วใช้ …ได้ เช่น คุณสามารถใช้… → ใช้…ได้"),
    Rule("ของคุณ", "medium", r"ของคุณ", "แปลมาจาก your ส่วนใหญ่ละได้ เช่น method ของคุณ → method นี้"),
    Rule("สำนวนแปล", "medium",
         r"กฎทอง|ตัวเปลี่ยนเกม|ยาแก้ปวด|กระสุนเงิน|ช้างในห้อง|ผลไม้ที่ห้อยต่ำ|ในตอนท้ายของวัน|ดำดิ่ง|ปัญหาคลาสนี้|มาเจาะลึก|เจาะลึกกัน",
         "สำนวนอังกฤษแปลตรงตัว เขียนความหมายในบริบทนั้นแบบที่คนไทยพูด หรือคงคำอังกฤษไว้"),
    Rule("อ้างกลับลอย ๆ", "info", r"สิ่งนี้|ดังกล่าว",
         "ถ้าอ่านแล้วไม่ชัดว่าหมายถึงอะไร ให้เรียกชื่อสิ่งนั้นตรง ๆ"),
    Rule("em-dash", "high", r"—", "em dash แบบอังกฤษ คนไทยแทบไม่ใช้ ใช้เว้นวรรค ขึ้นบรรทัดใหม่ หรือ : แทน"),

    # --- ภาษาทางการ: ใช้ในจดหมายหรือประกาศได้ แต่ในแชตฟังแข็ง ---
    Rule("อย่างไรก็ตาม", "medium", r"อย่างไรก็ตาม", "ในแชตใช้ แต่ ก็พอ", "ทางการ"),
    Rule("นอกจากนี้", "info", r"นอกจากนี้", "เปลี่ยนเรื่องด้วย แล้วก็… / อีกเรื่องคือ… หรือขึ้นย่อหน้าใหม่", "ทางการ"),
    Rule("ดำเนินการ", "medium", r"ดำเนินการ", "ในแชตใช้กริยาตรง ๆ เช่น ดำเนินการแก้ไข → แก้", "ทางการ"),
    Rule("ประสบ", "medium", r"ประสบ(?!การณ์|ความสำเร็จ)", "ใช้ เจอ หรือ พบ", "ทางการ"),
    Rule("วลีสำเร็จรูป", "medium",
         r"ในยุคปัจจุบัน|เป็นที่ทราบกันดีว่า|โดยสรุปแล้ว|นั่นเอง|ในแง่ของ|ในกรณีของ|ในอนาคตอันใกล้|นำมาซึ่ง|ก่อให้เกิด|เต็มไปด้วย|ทั้งนี้|อนึ่ง|เป็นสิ่งที่|สิ่งที่สำคัญคือ|ให้ความสนใจ|เป็นอย่างมาก|อย่างมีประสิทธิภาพ|ได้อย่างง่ายดาย",
         "วลีสำเร็จรูป ลองพูดให้ตรงกว่านี้", "ทางการ"),
    Rule("ในขณะที่", "info", r"ในขณะที่", "ส่วนใหญ่ใช้ ขณะที่ หรือ ส่วน… ก็พอ", "ทางการ"),

    # --- น้ำเสียง ใช้ได้ทุก persona ---
    Rule("ปิดแบบ-chatbot", "medium",
         r"คำถามที่ดี|คำถามดีมาก|ยินดีที่ได้ช่วย|หวังว่าจะเป็นประโยชน์|หากมีคำถามเพิ่มเติม|ถ้ามีคำถามเพิ่มเติม|อย่าลังเลที่จะ",
         "ประโยคเปิดหรือปิดแบบ chatbot ตัดทิ้งได้", "บุคคล"),

    # --- house style: คนไทยเองก็เขียนต่างจากนี้บ่อย ไม่ใช่ร่องรอยภาษาแปล ---
    Rule("อัศเจรีย์", "info", rf"[{THAI}]\s?!", "งานกึ่งทางการใช้ ! เท่าที่จำเป็น", "house"),
    Rule("ไทยติดอังกฤษ", "medium", rf"[{THAI_LETTER}][A-Za-z0-9]|[A-Za-z0-9][{THAI_LETTER}]",
         "เว้นวรรคระหว่างคำไทยกับคำอังกฤษหรือตัวเลข", "house"),
]

# กฎตาม persona: krab = ผม/ครับ, kha = หนู/ค่ะ
QUESTION_END = r"(?:ไหม|มั้ย|หรือเปล่า|หรือยัง|อะไร|ยังไง|อย่างไร|เหรอ|ที่ไหน|เมื่อไหร่|กี่)"
PERSONA_RULES = {
    "krab": [
        Rule("ฉัน", "medium", r"(?<!ดิ)ฉัน(?!ท์)", "persona นี้ใช้ ผม หรือละสรรพนามไปเลย", "บุคคล"),
        Rule("ดิฉัน-ค่ะ", "medium", rf"ดิฉัน|(?<![{THAI}])(?:ค่ะ|คะ)(?![{THAI}])|(?<=[{THAI}])(?:ค่ะ|คะ)(?=\s|$)",
             "persona นี้ใช้ ผม/ครับ", "บุคคล"),
    ],
    "kha": [
        Rule("ผม", "medium", r"(?<!เส้น)(?<!ทรง)ผม(?!ร่วง|หงอก|ยาว)", "persona นี้ใช้ หนู หรือละสรรพนามไปเลย", "บุคคล"),
        Rule("ดิฉัน", "info", r"ดิฉัน", "ดิฉัน ฟังทางการในแชต ใช้ หนู หรือละสรรพนาม เก็บ ดิฉัน ไว้ใช้ในจดหมาย", "บุคคล"),
        Rule("ครับ", "medium", r"ครับ", "persona นี้ลงท้าย ค่ะ หรือ คะ", "บุคคล"),
        Rule("นะค่ะ", "medium", r"นะค่ะ", "นะ ตามด้วย คะ เสมอ: นะคะ", "บุคคล"),
        Rule("คำถาม-ค่ะ", "medium", rf"{QUESTION_END}\s*ค่ะ", "ประโยคคำถามลงท้าย คะ ไม่ใช่ ค่ะ", "บุคคล"),
        # ประโยคที่บอกว่าจะทำอะไรให้ (เดี๋ยว…) หรือจบด้วยคำบอกเล่า เป็นประโยคบอกเล่า ต้องลงท้าย ค่ะ
        Rule("บอกเล่า-คะ", "medium",
             r"(?:เดี๋ยว(?:(?!ค่ะ|คะ)[^\n]){0,200}?|ให้|เลย|แล้ว|ด้วย|ก่อน)"
             r"(?<!ไหม)(?<!มั้ย)(?<!หรือเปล่า)(?<!หรือยัง)(?<!นะ)คะ(?=\s*$|\s)",
             "ประโยคบอกเล่าลงท้าย ค่ะ ไม่ใช่ คะ เช่น เดี๋ยวดูให้ค่ะ", "บุคคล"),
    ],
}
PARTICLE = {"krab": re.compile(r"ครับ"), "kha": re.compile(r"ค่ะ|คะ(?!แนน)")}

# ตัวสะกดคำทับศัพท์ตามราชบัณฑิตยสถาน
SPELLING = {
    "เช็ค": "เช็ก", "อัพเดท": "อัปเดต", "อัพเดต": "อัปเดต", "อัปเดท": "อัปเดต", "อัพโหลด": "อัปโหลด",
    "โปรเจค": "โปรเจกต์", "โปรเจ็ค": "โปรเจกต์", "โปรเจ็กต์": "โปรเจกต์", "ลิงค์": "ลิงก์", "อีเมล์": "อีเมล",
    "เวอร์ชั่น": "เวอร์ชัน", "ฟังก์ชั่น": "ฟังก์ชัน", "เซอร์เวอร์": "เซิร์ฟเวอร์", "แอพ": "แอป",
    "เฟรมเวิร์ค": "เฟรมเวิร์ก", "ซอฟท์แวร์": "ซอฟต์แวร์", "เว็บไซท์": "เว็บไซต์", "อินเตอร์เน็ต": "อินเทอร์เน็ต",
    "ดิจิตอล": "ดิจิทัล", "อ็อบเจ็กต์": "อ็อบเจกต์", "ออบเจ็กต์": "อ็อบเจกต์", "ออบเจกต์": "อ็อบเจกต์",
    "คอมเม้นต์": "คอมเมนต์", "คอมเม้นท์": "คอมเมนต์", "เทมเพลท": "เทมเพลต",
}

CONNECTIVES = {"ซึ่ง": r"ซึ่ง", "โดย": r"โดย(?!เฉพาะ|ปกติ|ตรง|รวม|ทั่วไป|ประมาณ|เร็ว|ด่วน)", "ดังนั้น": r"ดังนั้น"}

FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]+`")
URL = re.compile(r"https?://\S+")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
THAI_CHAR = re.compile(rf"[{THAI}]")
SENTENCE_PERIOD = re.compile(rf"(\S*[{THAI}])\.(?=\s|$|\*|\))")
BULLET_END_KRAP = re.compile(r"^\s*(?:[-*+]|\d+\.)\s.*ครับ\s*$")
BULLET_END_KHA = re.compile(r"^\s*(?:[-*+]|\d+\.)\s.*(?:ค่ะ|คะ)\s*$")


@dataclass
class Hit:
    rule: str
    severity: str
    line: int
    text: str
    message: str
    kind: str = "แปล"


def clean_lines(text):
    """ลบ code block, inline code, URL ออก แต่คงจำนวนบรรทัดไว้ให้เลขบรรทัดตรง"""
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
            continue
        line = INLINE_CODE.sub(" ", line)
        line = URL.sub(" ", line)
        line = LINK_TARGET.sub("]", line)
        out.append(line)
    return out


def context(line, start, end, width=18):
    left = max(0, start - width)
    right = min(len(line), end + width)
    return ("…" if left else "") + line[left:right].strip() + ("…" if right < len(line) else "")


def is_abbreviation(token):
    # ม.ค. / พ.ศ. / ก. / สคส. / กทม. มีจุดอยู่แล้ว สั้นแค่ 1–2 ตัว หรือมีแต่พยัญชนะ ถือว่าเป็นคำย่อ
    letters = re.sub(rf"[^{THAI}.]", "", token)
    if "." in letters or len(letters) <= 2:
        return True
    return all("ก" <= ch <= "ฮ" for ch in letters)


def lint(text, yamok="spaced", persona="krab"):
    lines = clean_lines(text)
    hits = []
    compiled = [(r, re.compile(r.pattern, re.MULTILINE)) for r in RULES + PERSONA_RULES[persona]]

    for no, line in enumerate(lines, 1):
        if not THAI_CHAR.search(line):
            continue
        for rule, rx in compiled:
            for m in rx.finditer(line):
                hits.append(Hit(rule.id, rule.severity, no, context(line, m.start(), m.end()), rule.message, rule.kind))
        for wrong, right in SPELLING.items():
            for m in re.finditer(wrong, line):
                hits.append(Hit("ตัวสะกด", "medium", no, context(line, m.start(), m.end()),
                                f"{wrong} → {right} (ราชบัณฑิตฯ)", "house"))
        for m in SENTENCE_PERIOD.finditer(line):
            if not is_abbreviation(m.group(1)):
                hits.append(Hit("จุดท้ายประโยค", "medium", no, context(line, m.start(), m.end()),
                                "ภาษาไทยไม่ใส่จุดท้ายประโยค ใช้เว้นวรรคแทน"))
        if yamok == "spaced":
            for m in re.finditer(rf"[{THAI_LETTER}]ๆ", line):
                hits.append(Hit("ไม้ยมก", "info", no, context(line, m.start(), m.end()),
                                "ราชบัณฑิตฯ ให้เว้นวรรคหน้าและหลัง ๆ เช่น ต่าง ๆ", "house"))
        for m in re.finditer(rf"ๆ(?=[{THAI_LETTER}])", line):
            hits.append(Hit("ไม้ยมก", "info", no, context(line, m.start(), m.end()),
                            "เว้นวรรคหลัง ๆ", "house"))

    # คำเชื่อมเกินโควตา: คำละไม่เกินหนึ่งครั้งต่อย่อหน้า
    paragraph, start_no = [], 1
    for no, line in enumerate(lines + [""], 1):
        if line.strip():
            if not paragraph:
                start_no = no
            paragraph.append(line)
            continue
        if paragraph:
            block = " ".join(paragraph)
            for word, pattern in CONNECTIVES.items():
                n = len(re.findall(pattern, block))
                if n > 1:
                    hits.append(Hit("คำเชื่อมถี่", "info", start_no, f"{word} {n} ครั้งในย่อหน้าเดียว",
                                    f"{word} ถี่ในย่อหน้าเดียว ถ้าประโยคยาวเกินลองแยกประโยค"))
            paragraph = []

    # ลงท้าย ครับ ทุก bullet ฟังเป็นสูตร
    bullet_end = BULLET_END_KRAP if persona == "krab" else BULLET_END_KHA
    bullet_particle = [no for no, line in enumerate(lines, 1) if bullet_end.match(line)]
    if len(bullet_particle) > 1:
        hits.append(Hit("คำลงท้ายถี่", "medium", bullet_particle[0], f"bullet มีคำลงท้าย {len(bullet_particle)} ข้อ",
                        "ไม่ต้องใส่คำลงท้ายทุกข้อ ใส่ตอนจบย่อหน้าหรือจบคำตอบก็พอ", "บุคคล"))

    thai_chars = sum(len(THAI_CHAR.findall(l)) for l in lines)
    # คะแนนหลักนับเฉพาะร่องรอยภาษาแปล ส่วนภาษาทางการ persona และ house style แยกนับ
    by_kind = {}
    for h in hits:
        if h.severity in ("high", "medium"):
            by_kind[h.kind] = by_kind.get(h.kind, 0) + 1
    counts = {}
    for h in hits:
        counts[h.rule] = counts.get(h.rule, 0) + 1
    scored = by_kind.get("แปล", 0)
    return {
        "thai_chars": thai_chars,
        "particle": sum(len(PARTICLE[persona].findall(l)) for l in lines),
        "closing_offer": closing_offer(lines),
        "hits": [asdict(h) for h in sorted(hits, key=lambda h: h.line)],
        "counts": counts,
        "by_kind": by_kind,
        "scored": scored,
        "per_1000": round(scored * 1000 / thai_chars, 2) if thai_chars else 0.0,
    }


OFFER = re.compile(r"(ถ้า|หาก|อยาก|บอก|ส่ง|แปะ).*(เดี๋ยว|ได้เลย|ได้ครับ|ไหมครับ|ให้ครับ)|ไหมครับ\s*$")


def closing_offer(lines):
    """ย่อหน้าสุดท้ายเป็นการเสนอช่วยต่อหรือถามกลับไหม ถ้าทุกคำตอบปิดแบบนี้ อ่านแล้วเหมือนแม่แบบ"""
    paragraphs = [p.strip() for p in "\n".join(lines).split("\n\n") if p.strip()]
    return bool(paragraphs) and bool(OFFER.search(paragraphs[-1]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="หาร่องรอยภาษาแปลในข้อความภาษาไทย")
    ap.add_argument("files", nargs="+", help="ไฟล์ที่จะตรวจ ใช้ - เพื่ออ่านจาก stdin")
    ap.add_argument("--json", action="store_true", help="แสดงผลเป็น JSON")
    ap.add_argument("--summary", action="store_true", help="แสดงแค่ตัวเลขสรุป")
    ap.add_argument("--persona", choices=["krab", "kha"], default="krab",
                    help="krab = ผม/ครับ (ค่าเริ่มต้น), kha = หนู/ค่ะ")
    ap.add_argument("--yamok", choices=["spaced", "attached"], default="spaced",
                    help="แบบไม้ยมกที่ใช้: spaced = ต่าง ๆ (ราชบัณฑิตฯ), attached = ต่างๆ")
    args = ap.parse_args()

    results = {}
    for path in args.files:
        if path == "-":
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        results[path] = lint(text, args.yamok, args.persona)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return

    for path, r in results.items():
        k = r["by_kind"]
        print(f"{path}  ภาษาไทย {r['thai_chars']:,} ตัวอักษร  ภาษาแปล {r['scored']} "
              f"({r['per_1000']} ต่อ 1,000)  ทางการ {k.get('ทางการ', 0)}  persona {k.get('บุคคล', 0)}  "
              f"house style {k.get('house', 0)}")
        if args.summary:
            continue
        for h in r["hits"]:
            print(f"  L{h['line']:<4} [{h['kind']}:{h['rule']}|{h['severity']}] {h['text']}")
            print(f"        → {h['message']}")


if __name__ == "__main__":
    main()
