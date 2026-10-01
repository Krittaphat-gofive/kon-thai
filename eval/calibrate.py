#!/usr/bin/env python3
"""calibrate.py — วัดว่าคนไทยใช้คำที่ linter จับถี่แค่ไหน

เทียบคำตอบของ Claude กับภาษาไทยที่คนไทยเขียนเองสองแบบ
- ข่าว Blognone (pythainlp/blognone_news, CC BY 3.0) งานเขียนไอทีที่ผ่านการเรียบเรียงแล้ว
- คอมเมนต์ Pantip (amitysolution/Pantip_QA_200000_20220220) คนไทยพิมพ์ตอบกระทู้ ใกล้กับการแชตกว่า
  แยกคอลัมน์กระทู้ไอทีออกมาอีกชุด ชุดนี้ไม่ระบุ license เลยเก็บข้อความไว้ในเครื่องเท่านั้น

กฎไหนที่คนไทยเองก็ใช้ถี่ ไม่ควรตั้งเป้าให้เป็นศูนย์ กฎไหนที่คนไทยแทบไม่ใช้ คือร่องรอยภาษาแปลจริง

วิธีใช้:
  python eval/calibrate.py --runs r2/control r2/style
  python eval/calibrate.py --refresh        ดึงตัวอย่างใหม่ (ปกติใช้ไฟล์ที่เก็บไว้)
"""

import argparse
import importlib.util
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "eval" / "corpus"
LINT = ROOT / "plugins" / "kon-thai" / "skills" / "thai-native-voice" / "scripts" / "thai_lint.py"
ROWS_API = "https://datasets-server.huggingface.co/rows?dataset={dataset}&config=default&split=train"

CORPORA = {
    "blognone": {"dataset": "pythainlp/blognone_news", "total": 18712, "batches": 15,
                 "row": lambda r: {"txt": r["txt"]}},
    "pantip": {"dataset": "amitysolution/Pantip_QA_200000_20220220", "total": 294678, "batches": 60,
               "row": lambda r: {"txt": r["comment"] or "", "topic": (r["prompt"] or "")[:300]}},
}
# คัดกระทู้ไอทีจากหัวข้อกับเนื้อกระทู้ จับแบบหยาบ แต่พอแยกเรื่องคอม มือถือ และโปรแกรมออกจากเรื่องทั่วไปได้
TECH = re.compile(r"โปรแกรม|โค้ด|code|เขียนเว็บ|เว็บไซต์|python|java|excel|windows|คอม|notebook|โน้ตบุ๊ก|server|"
                  r"database|ฐานข้อมูล|แอป|app\b|มือถือ|iphone|android|wifi|ไวไฟ|เน็ต|software|ซอฟต์แวร์|"
                  r"\bIT\b|developer|programmer|ไอที", re.I)


def load_lint():
    spec = importlib.util.spec_from_file_location("thai_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cache_path(name):
    return CORPUS_DIR / f"{name}_sample.jsonl"


def fetch_sample(name, per_batch=100):
    """สุ่มแถวกระจายทั้ง dataset ผ่าน API ของ Hugging Face ไม่ต้องติดตั้ง pandas"""
    cfg = CORPORA[name]
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    rows, seen = [], set()
    batches = cfg["batches"]
    for i in range(batches):
        offset = int(i * (cfg["total"] - per_batch) / max(batches - 1, 1))
        url = ROWS_API.format(dataset=cfg["dataset"]) + f"&offset={offset}&length={per_batch}"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.loads(r.read().decode("utf-8"))
                for x in data["rows"]:
                    row = cfg["row"](x["row"])
                    if row["txt"].strip() and row["txt"] not in seen:  # Pantip ซ้ำคำถามทุกแถว แต่คอมเมนต์ไม่ควรซ้ำ
                        seen.add(row["txt"])
                        rows.append(row)
                break
            except Exception as e:  # เครือข่ายสะดุดหรือโดนจำกัดความถี่ (429) รอนานขึ้นทีละรอบ
                if attempt == 3:
                    print(f"  ข้าม offset {offset}: {e}", file=sys.stderr)
                time.sleep(10 * (attempt + 1))
        time.sleep(1)
        print(f"  {name}: ดึงแล้ว {len(rows)} แถว", flush=True)
    with cache_path(name).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def load_corpus(name, refresh):
    path = cache_path(name)
    if refresh or not path.exists():
        print(f"ดึง {name} จาก Hugging Face", flush=True)
        return fetch_sample(name)
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def measure(lint, texts, persona="krab"):
    chars, counts, scored = 0, {}, 0
    extra = {"ปิดด้วยการเสนอช่วย": 0, "ครับ": 0, "เอกสาร": len(texts)}
    for t in texts:
        r = lint.lint(t, persona=persona)
        chars += r["thai_chars"]
        scored += r["scored"]
        extra["ปิดด้วยการเสนอช่วย"] += r["closing_offer"]
        extra["ครับ"] += r["particle"]
        for k, v in r["counts"].items():
            counts[k] = counts.get(k, 0) + v
    return chars, counts, scored, extra


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="*", default=[], help="โฟลเดอร์คำตอบใน eval/runs เช่น r2/control")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--persona", choices=["krab", "kha"], default="krab")
    ap.add_argument("--out", default=str(CORPUS_DIR / "calibration.md"))
    args = ap.parse_args()

    blognone = load_corpus("blognone", args.refresh)
    pantip = load_corpus("pantip", args.refresh)
    pantip_tech = [r for r in pantip if TECH.search(r["topic"])]

    lint = load_lint()
    columns = {
        "ข่าว Blognone": measure(lint, [r["txt"] for r in blognone]),
        "คอมเมนต์ Pantip": measure(lint, [r["txt"] for r in pantip]),
        "Pantip กระทู้ไอที": measure(lint, [r["txt"] for r in pantip_tech]),
    }
    for run in args.runs:
        files = sorted(f for f in (ROOT / "eval" / "runs" / run).glob("*.md") if not f.name.startswith("_"))
        columns[run] = measure(lint, [f.read_text(encoding="utf-8") for f in files], args.persona)

    rules = sorted({k for _, c, _, _ in columns.values() for k in c})
    lines = ["# เทียบกับภาษาไทยที่คนไทยเขียนเอง", "",
             "ตัวเลขคือจำนวนครั้งต่อ 1,000 ตัวอักษรไทย ยิ่งน้อยยิ่งห่างจากภาษาแปล "
             "แต่ถ้าคนไทยเองก็ใช้ถี่ แปลว่าคำนั้นไม่ใช่ปัญหา", "",
             f"- ข่าว Blognone {len(blognone):,} ข่าว (pythainlp/blognone_news, CC BY 3.0)",
             f"- คอมเมนต์ Pantip {len(pantip):,} คอมเมนต์ (amitysolution/Pantip_QA_200000_20220220) "
             f"ในนี้เป็นกระทู้ไอที {len(pantip_tech):,} คอมเมนต์ ชุดนี้ไม่ระบุ license จึงไม่ได้เก็บข้อความไว้ใน repo", "",
             "| กฎ | " + " | ".join(columns) + " |", "|---|" + "---:|" * len(columns)]
    for rule in rules:
        cells = [f"{c.get(rule, 0) * 1000 / chars:.2f}" if chars else "-" for chars, c, _, _ in columns.values()]
        lines.append(f"| {rule} | " + " | ".join(cells) + " |")
    lines.append("| **คะแนนภาษาแปล (high + medium)** | " + " | ".join(
        f"**{s * 1000 / ch:.2f}**" if ch else "-" for ch, _, s, _ in columns.values()) + " |")
    lines.append("| คำลงท้าย ต่อ 1,000 ตัวอักษร | " + " | ".join(
        f"{e['ครับ'] * 1000 / ch:.2f}" if ch else "-" for ch, _, _, e in columns.values()) + " |")
    lines.append("| ปิดด้วยการเสนอช่วย | " + " | ".join(
        f"{e['ปิดด้วยการเสนอช่วย']}/{e['เอกสาร']}" for _, _, _, e in columns.values()) + " |")
    lines.append("| ตัวอักษรไทยทั้งหมด | " + " | ".join(f"{ch:,}" for ch, _, _, _ in columns.values()) + " |")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
