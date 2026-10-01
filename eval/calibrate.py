#!/usr/bin/env python3
"""calibrate.py — วัดว่าคนไทยที่เขียนงานไอทีใช้คำที่ linter จับถี่แค่ไหน

ใช้ข่าว Blognone (pythainlp/blognone_news, CC BY 3.0) เป็นตัวแทนภาษาไทยที่คนไทยเขียนเอง
ในระดับภาษาที่ใกล้กับงานของเรา แล้วเทียบอัตราต่อ 1,000 ตัวอักษรกับคำตอบของ Claude
กฎไหนที่คนไทยเองก็ใช้ถี่ ไม่ควรตั้งเป้าให้เป็นศูนย์ กฎไหนที่คนไทยแทบไม่ใช้ คือร่องรอยภาษาแปลจริง

วิธีใช้:
  python eval/calibrate.py --runs r2/control r2/style
  python eval/calibrate.py --refresh        ดึงตัวอย่างข่าวใหม่ (ปกติใช้ไฟล์ที่เก็บไว้)
"""

import argparse
import importlib.util
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "eval" / "corpus" / "blognone_sample.jsonl"
LINT = ROOT / "plugins" / "kon-thai" / "skills" / "thai-native-voice" / "scripts" / "thai_lint.py"
ROWS_API = "https://datasets-server.huggingface.co/rows?dataset=pythainlp/blognone_news&config=default&split=train"
TOTAL_ROWS = 18712


def load_lint():
    spec = importlib.util.spec_from_file_location("thai_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fetch_sample(batches, per_batch=100):
    """สุ่มข่าวกระจายทั้ง dataset ผ่าน API ของ Hugging Face ไม่ต้องติดตั้ง pandas"""
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(batches):
        offset = int(i * (TOTAL_ROWS - per_batch) / max(batches - 1, 1))
        url = f"{ROWS_API}&offset={offset}&length={per_batch}"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.loads(r.read().decode("utf-8"))
                rows += [x["row"]["txt"] for x in data["rows"]]
                break
            except Exception as e:  # เครือข่ายสะดุดบ้างเป็นปกติ ลองใหม่สองรอบ
                if attempt == 2:
                    print(f"  ข้าม offset {offset}: {e}", file=sys.stderr)
                time.sleep(3)
        print(f"  ดึงแล้ว {len(rows)} ข่าว", flush=True)
    with CORPUS.open("w", encoding="utf-8") as f:
        for txt in rows:
            f.write(json.dumps({"txt": txt}, ensure_ascii=False) + "\n")
    return rows


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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="*", default=[], help="โฟลเดอร์คำตอบใน eval/runs เช่น r2/control")
    ap.add_argument("--batches", type=int, default=15, help="จำนวนชุดละ 100 ข่าว")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--persona", choices=["krab", "kha"], default="krab")
    ap.add_argument("--out", default=str(ROOT / "eval" / "corpus" / "calibration.md"))
    args = ap.parse_args()

    if args.refresh or not CORPUS.exists():
        print("ดึงข่าว Blognone จาก Hugging Face", flush=True)
        texts = fetch_sample(args.batches)
    else:
        texts = [json.loads(l)["txt"] for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]

    lint = load_lint()
    columns = {"Blognone (คนไทยเขียน)": measure(lint, texts)}
    for run in args.runs:
        files = sorted(f for f in (ROOT / "eval" / "runs" / run).glob("*.md") if not f.name.startswith("_"))
        columns[run] = measure(lint, [f.read_text(encoding="utf-8") for f in files], args.persona)

    rules = sorted({k for _, c, _, _ in columns.values() for k in c})
    lines = ["# เทียบกับภาษาไทยที่คนไทยเขียนเอง", "",
             f"ตัวอย่าง Blognone {len(texts):,} ข่าว (pythainlp/blognone_news, CC BY 3.0) ตัวเลขคือจำนวนครั้งต่อ 1,000 ตัวอักษรไทย", "",
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
