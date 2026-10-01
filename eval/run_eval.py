#!/usr/bin/env python3
"""run_eval.py — รันชุดคำถาม baseline ผ่าน claude -p แล้วเทียบผลแต่ละ config

แต่ละ arm คือการตั้งค่าหนึ่งแบบ:
  control      ตั้งค่าเหมือนที่ใช้อยู่ ไม่มี thai-native
  style        เปิด output style thai-native
  style+hook   style + UserPromptSubmit hook เตือนทุกครั้งที่พิมพ์

ทุก arm รันใน working dir ว่างของตัวเอง ปิด tool ทั้งหมด และไม่บันทึก session

วิธีใช้:
  python eval/run_eval.py run --name r1 --arms control style
  python eval/run_eval.py report --name r1
  python eval/run_eval.py blind --name r1 --a control --b style   สร้างไฟล์ให้คนอ่านเทียบแบบไม่รู้ว่าอันไหนมาจากไหน
  python eval/run_eval.py reveal --name r1 --a control --b style  นับผลหลังเลือกเสร็จ
"""

import argparse
import concurrent.futures as cf
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "eval" / "prompts.md"
RUNS = ROOT / "eval" / "runs"
PLUGIN = ROOT / "plugins" / "kon-thai"
STYLE = PLUGIN / "output-styles" / "thai-native.md"
HOOK_TEXT = PLUGIN / "hooks" / "thai_reminder.txt"
LINT = PLUGIN / "skills" / "thai-native-voice" / "scripts" / "thai_lint.py"

SKILL = PLUGIN / "skills" / "thai-native-voice"

# tools = "" คือปิด tool ทั้งหมด, prefix คือข้อความที่เติมหน้า prompt เช่นคำสั่งเรียก skill
ARMS = {
    "control": {"style": False, "hook": False, "skill": False, "tools": "", "prefix": ""},
    "style": {"style": True, "hook": False, "skill": False, "tools": "", "prefix": ""},
    "style+hook": {"style": True, "hook": True, "skill": False, "tools": "", "prefix": ""},
    # ชุดทดสอบ skill ขัดเกลา: เปิด Read กับ Bash ให้อ่านไฟล์อ้างอิงและรัน linter ได้
    "polish-control": {"style": False, "hook": False, "skill": False, "tools": "Read,Bash", "prefix": ""},
    "polish-skill": {"style": False, "hook": False, "skill": True, "tools": "Read,Bash",
                     "prefix": "/thai-native-voice-eval "},
    "polish-skill-auto": {"style": False, "hook": False, "skill": True, "tools": "Read,Bash", "prefix": ""},
}


def find_claude():
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    found = shutil.which("claude")
    if not found:
        sys.exit("หา claude ไม่เจอ ตั้ง CLAUDE_BIN ให้ชี้ไปที่ claude.exe")
    # บน Windows ตัว claude.cmd ส่ง argument ผ่าน cmd.exe ซึ่งทำอักขระพิเศษเพี้ยน เลยเรียก exe ตรงแทน
    exe = Path(found).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    return str(exe) if exe.exists() else found


def load_lint():
    spec = importlib.util.spec_from_file_location("thai_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_prompts(path=PROMPTS):
    items, current = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        # id ต้องขึ้นต้นด้วยตัวเลขสองหลัก เพราะข้อความที่ให้เกลามีหัวข้อ markdown ของตัวเองปนอยู่
        m = re.match(r"^## ([a-z]*\d{2}-[A-Za-z0-9-]+) \| (.+)$", line)
        if m:
            current = {"id": m.group(1), "category": m.group(2).strip(), "lines": []}
            items.append(current)
        elif current is not None:
            current["lines"].append(line)
    for it in items:
        it["prompt"] = "\n".join(it.pop("lines")).strip()
    return items


EVAL_STYLE = "thai-native-eval"
EVAL_SKILL = "thai-native-voice-eval"


def rename_frontmatter(text, name):
    return re.sub(r"^name: .*$", f"name: {name}", text, count=1, flags=re.M)


def prepare_arm(run_dir, arm, style=STYLE):
    """สร้าง working dir ของ arm พร้อมไฟล์ style และ settings ที่ต้องใช้

    แยกจากของที่ติดตั้งไว้ใน ~/.claude: ตั้งชื่อ style กับ skill ที่ทดสอบใหม่ไม่ให้ชนกับตัวที่ติดตั้ง
    arm ที่ไม่มี style บังคับ outputStyle เป็น default และปิด hook ทุกตัว (รวม hook ของ plugin)
    ไม่งั้น claude -p จะหยิบ style กับ hook ที่ติดตั้งไว้มาใช้ด้วย ทำให้ control ไม่ใช่ control จริง
    """
    work = run_dir / arm / "_work"
    work.mkdir(parents=True, exist_ok=True)
    # ปิด plugin kon-thai ที่ติดตั้งไว้ และซ่อน skill ที่ติดตั้งแบบเดิม ไม่งั้น arm ที่เปิด Read ได้จะหยิบ skill มาใช้เอง
    settings = {"outputStyle": "default", "enabledPlugins": {"kon-thai@kon-thai": False},
                "skillOverrides": {SKILL.name: "off", f"kon-thai:{SKILL.name}": "off"}}
    if not ARMS[arm]["hook"]:
        settings["disableAllHooks"] = True
    if ARMS[arm]["skill"]:
        dst = work / ".claude" / "skills" / EVAL_SKILL
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(SKILL, dst, ignore=shutil.ignore_patterns("__pycache__"))
        md = dst / "SKILL.md"
        md.write_text(rename_frontmatter(md.read_text(encoding="utf-8"), EVAL_SKILL), encoding="utf-8")
    if ARMS[arm]["style"]:
        styles = work / ".claude" / "output-styles"
        styles.mkdir(parents=True, exist_ok=True)
        text = Path(style).read_text(encoding="utf-8")
        (styles / f"{EVAL_STYLE}.md").write_text(rename_frontmatter(text, EVAL_STYLE), encoding="utf-8")
        shutil.copy(style, run_dir / arm / "_style.md")  # เก็บไว้ดูทีหลังว่ารอบนี้ใช้ style ฉบับไหน
        settings["outputStyle"] = EVAL_STYLE
    if ARMS[arm]["hook"]:
        settings["hooks"] = {"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": f'cat "{HOOK_TEXT.as_posix()}"', "shell": "bash", "timeout": 10}
        ]}]}
    settings_file = run_dir / arm / "_settings.json"
    settings_file.write_text(json.dumps(settings, ensure_ascii=False, indent=1), encoding="utf-8")
    return work, settings_file


# ทุก arm ได้ข้อความนี้เหมือนกัน ไม่งั้นบางคำตอบจะพยายามเรียก tool ที่ปิดไว้ แล้วพิมพ์ tool call ปลอมออกมาแทนคำตอบ
HARNESS_NOTE = ("This is a text-only session: there are no project files and no tools. "
                "Answer the user's message directly in prose; do not try to call tools or skills.")
HARNESS_NOTE_TOOLS = "There are no project files in this directory. Answer the user's message directly."
MIN_THAI_CHARS = 50


def run_one(claude, arm, item, run_dir, work, settings_file, args):
    out = run_dir / arm / f"{item['id']}.md"
    if out.exists() and not args.force:
        return arm, item["id"], "skip", 0.0
    tools = ARMS[arm]["tools"]
    cmd = [claude, "-p", "--tools", tools, "--no-session-persistence", "--output-format", "text",
           "--append-system-prompt", HARNESS_NOTE_TOOLS if tools else HARNESS_NOTE]
    if "Bash" in tools:
        cmd += ["--allowedTools", "Bash(python *)", "Read"]
    if settings_file:
        cmd += ["--settings", str(settings_file)]
    if args.model:
        cmd += ["--model", args.model]
    if args.effort:
        cmd += ["--effort", args.effort]
    start = time.time()
    status = "ok"
    for attempt in range(1, args.retries + 2):
        try:
            prompt = ARMS[arm]["prefix"] + item["prompt"]
            r = subprocess.run(cmd, cwd=work, input=prompt.encode("utf-8"),
                               capture_output=True, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            status = "timeout"
            continue
        text = r.stdout.decode("utf-8", errors="replace")
        if r.returncode != 0 or not text.strip():
            (run_dir / arm / f"{item['id']}.err.txt").write_text(
                r.stderr.decode("utf-8", errors="replace"), encoding="utf-8")
            status = f"error {r.returncode}"
            continue
        out.write_text(text, encoding="utf-8")
        thai = len(re.findall(r"[฀-๿]", text))
        status = "ok" if attempt == 1 else f"ok (รอบที่ {attempt})"
        if thai >= MIN_THAI_CHARS:
            break
        status = f"ไทยแค่ {thai} ตัว"
    return arm, item["id"], status, time.time() - start


def cmd_run(args):
    claude = find_claude()
    items = parse_prompts(args.prompts)
    if args.only:
        items = [it for it in items if it["id"] in args.only]
    run_dir = RUNS / args.name
    jobs = []
    for arm in args.arms:
        if ARMS[arm]["style"] and not Path(args.style).exists():
            sys.exit(f"ไม่มีไฟล์ {args.style}")
        work, settings_file = prepare_arm(run_dir, arm, Path(args.style))
        jobs += [(arm, it, work, settings_file) for it in items]
    print(f"รัน {len(jobs)} งาน ({len(items)} คำถาม × {len(args.arms)} arm) ทีละ {args.jobs} งาน", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, claude, arm, it, run_dir, work, sf, args) for arm, it, work, sf in jobs]
        for f in cf.as_completed(futures):
            arm, pid, status, took = f.result()
            print(f"  {arm:<11} {pid:<28} {status} ({took:.0f}s)", flush=True)
    cmd_report(args)


def cmd_report(args):
    lint = load_lint()
    run_dir = RUNS / args.name
    items = parse_prompts(args.prompts)
    arms = [a for a in ARMS if (run_dir / a).is_dir()]
    if not any((run_dir / a / f"{it['id']}.md").exists() for a in arms for it in items):
        sys.exit(f"ไม่เจอคำตอบใน {run_dir} ที่ตรงกับคำถามใน {args.prompts} "
                 "ถ้าตอนรันใช้ชุดคำถามอื่น ให้ใส่ --prompts เป็นไฟล์เดียวกัน")
    rows, totals, extra = [], {}, {}
    for arm in arms:
        chars = scored = 0
        counts = {}
        no_thai, no_krap, offers = [], [], 0
        kinds = {}
        for it in items:
            f = run_dir / arm / f"{it['id']}.md"
            if not f.exists():
                continue
            r = lint.lint(f.read_text(encoding="utf-8"), persona=args.persona)
            if r["thai_chars"] < MIN_THAI_CHARS:
                no_thai.append(it["id"])
                continue
            if r["particle"] == 0:
                no_krap.append(it["id"])
            offers += r["closing_offer"]
            for k, v in r["by_kind"].items():
                kinds[k] = kinds.get(k, 0) + v
            chars += r["thai_chars"]
            scored += r["scored"]
            for k, v in r["counts"].items():
                counts[k] = counts.get(k, 0) + v
            rows.append((arm, it["id"], r["thai_chars"], r["scored"], r["per_1000"]))
        totals[arm] = (chars, scored, counts)
        extra[arm] = (no_thai, no_krap, offers, kinds)

    lines = [f"# ผลรัน {args.name}", "", "## ภาพรวม", "",
             "คะแนนหลักนับเฉพาะร่องรอยภาษาแปล ภาษาทางการ persona และ house style แยกนับ", "",
             "| arm | ภาษาไทย (ตัวอักษร) | ภาษาแปล | ต่อ 1,000 ตัวอักษร | ทางการ | persona | house style "
             "| ปิดด้วยการเสนอช่วย | ไม่มีคำลงท้าย | ไม่ใช่ภาษาไทย |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, (chars, scored, _) in totals.items():
        rate = round(scored * 1000 / chars, 2) if chars else 0
        no_thai, no_krap, offers, kinds = extra[arm]
        answered = len([1 for a, *_ in rows if a == arm])
        lines.append(f"| {arm} | {chars:,} | {scored} | {rate} | {kinds.get('ทางการ', 0)} | {kinds.get('บุคคล', 0)} "
                     f"| {kinds.get('house', 0)} | {offers}/{answered} | {len(no_krap)} | {len(no_thai)} |")
    for arm, (no_thai, *_rest) in extra.items():
        if no_thai:
            lines.append(f"\n{arm}: ไม่นับคำตอบที่แทบไม่มีภาษาไทย {', '.join(no_thai)}")
    rules = sorted({k for _, _, c in totals.values() for k in c})
    lines += ["", "## แยกตามกฎ (นับรวมทุกระดับ)", "", "| กฎ | " + " | ".join(totals) + " |",
              "|---|" + "---:|" * len(totals)]
    for rule in rules:
        lines.append(f"| {rule} | " + " | ".join(str(c.get(rule, 0)) for _, _, c in totals.values()) + " |")
    lines += ["", "## รายคำถาม", "", "| arm | คำถาม | ตัวอักษร | จุด | ต่อ 1,000 |", "|---|---|---:|---:|---:|"]
    lines += [f"| {a} | {p} | {c:,} | {s} | {r} |" for a, p, c, s, r in rows]
    report = run_dir / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8 + len(totals)]))
    print(f"\nรายงานเต็ม: {report}")


def cmd_blind(args):
    run_dir = RUNS / args.name
    rng = random.Random(args.seed)
    key, parts = {}, [f"# เทียบแบบ blind ({args.name})", "",
                      "อ่านแต่ละข้อแล้วเขียน A หรือ B หลังคำว่า `เลือก:` ว่าอันไหนฟังเป็นคนไทยกว่า",
                      "ถ้าพอ ๆ กันให้เขียน = เสร็จแล้วรัน `reveal`", ""]
    for it in parse_prompts(args.prompts):
        fa, fb = run_dir / args.a / f"{it['id']}.md", run_dir / args.b / f"{it['id']}.md"
        if not (fa.exists() and fb.exists()):
            continue
        pair = [(args.a, fa), (args.b, fb)]
        rng.shuffle(pair)
        key[it["id"]] = {"A": pair[0][0], "B": pair[1][0]}
        parts += [f"## {it['id']}", "", "> " + it["prompt"].replace("\n", "\n> "), "",
                  "### A", "", pair[0][1].read_text(encoding="utf-8").strip(), "",
                  "### B", "", pair[1][1].read_text(encoding="utf-8").strip(), "",
                  "เลือก: ", "", "---", ""]
    sheet = run_dir / f"blind-{args.a}-vs-{args.b}.md"
    sheet.write_text("\n".join(parts), encoding="utf-8")
    (run_dir / f"blind-{args.a}-vs-{args.b}.key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"ไฟล์ให้เลือก: {sheet} ({len(key)} ข้อ)")


def cmd_reveal(args):
    run_dir = RUNS / args.name
    sheet = (run_dir / f"blind-{args.a}-vs-{args.b}.md").read_text(encoding="utf-8")
    key = json.loads((run_dir / f"blind-{args.a}-vs-{args.b}.key.json").read_text(encoding="utf-8"))
    tally = {args.a: 0, args.b: 0, "เสมอ": 0}
    # id ต้องขึ้นต้นด้วยตัวเลข ไม่งั้นหัวข้อในคำตอบอย่าง "## สรุป" จะโดนนับเป็นข้อใหม่
    for pid, choice in re.findall(r"^## ([a-z]*\d{2}-[A-Za-z0-9-]+)$.*?^เลือก:[ \t]*(\S*)", sheet, flags=re.M | re.S):
        choice = choice.strip().upper()
        if choice in ("A", "B"):
            tally[key[pid][choice]] += 1
        elif choice == "=":
            tally["เสมอ"] += 1
    print(" | ".join(f"{k}: {v}" for k, v in tally.items()))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run")
    p.add_argument("--name", required=True)
    p.add_argument("--arms", nargs="+", choices=list(ARMS), default=["control", "style"])
    p.add_argument("--only", nargs="+", help="รันเฉพาะ id ที่ระบุ")
    p.add_argument("--jobs", type=int, default=6)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--retries", type=int, default=2, help="รันซ้ำเมื่อคำตอบแทบไม่มีภาษาไทย")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--force", action="store_true", help="รันทับคำตอบเดิม")
    p.add_argument("--style", default=str(STYLE), help="ไฟล์ output style ที่จะทดสอบ")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report")
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_report)

    for name, func in (("blind", cmd_blind), ("reveal", cmd_reveal)):
        p = sub.add_parser(name)
        p.add_argument("--name", required=True)
        p.add_argument("--a", default="control")
        p.add_argument("--b", default="style")
        p.add_argument("--seed", type=int, default=7)
        p.set_defaults(func=func)

    for sp in sub.choices.values():
        sp.add_argument("--prompts", default=str(PROMPTS), help="ไฟล์คำถาม (ค่าเริ่มต้น eval/prompts.md)")
        sp.add_argument("--persona", choices=["krab", "kha"], default="krab", help="persona ที่ใช้ตรวจ: krab = ผม/ครับ, kha = หนู/ค่ะ")
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
