# ภาษาไทยที่คนไทยเขียนจริงบนออนไลน์ (1 ต.ค. 2569)

รายงานจาก research agent ที่ดึงหน้าเว็บสาธารณะ (Blognone, Pantip, บล็อก dev ไทย, README บน GitHub, ข่าวและบทความเรื่องภาษาอินเทอร์เน็ต) แล้วยกข้อความจริงพร้อมลิงก์ ตัวเลขทุกตัวนับแบบจับคำตรงตัว ยังไม่แยกความหมายของคำ เช่น "ถูก" ที่แปลว่าราคาถูก

---

## How I collected this (2026-10-01)

I downloaded public pages with curl and pulled the text out with small Python scripts, so the quotes are copied character for character from the page text. Typos are kept as found. Where a quote contains " / ", that is a line break my script inserted. Pantip comments came from Pantip's public comment endpoint (`/forum/topic/render_comments`), which needs no login. I stopped at about 30 tool calls.

## A. Thai developer communities

**Sources sampled**
- Blognone comments on four articles: [node/130710](https://www.blognone.com/node/130710) (TypeScript at 10), [node/135472](https://www.blognone.com/node/135472) (Rust survey), [node/151102](https://www.blognone.com/node/151102) (TypeScript 7), [node/151761](https://www.blognone.com/node/151761) (DHH and Rust).
- Pantip comments on four threads: [33649391](https://pantip.com/topic/33649391), [40543391](https://pantip.com/topic/40543391), [41038200](https://pantip.com/topic/41038200), [42433626](https://pantip.com/topic/42433626).
- Blogs: [devahoy.com](https://devahoy.com/blog) by Chai Phonbopit ("Senior Software Engineer ประสบการณ์กว่า 12 ปี"), posts [intro-to-open-code](https://devahoy.com/blog/intro-to-open-code/) and [setup-multiple-llm-providers-in-claude-code](https://devahoy.com/blog/setup-multiple-llm-providers-in-claude-code/); the [somkiat.cc](https://www.somkiat.cc/) front page.
- GitHub READMEs: [earthchie/jquery.Thailand.js](https://github.com/earthchie/jquery.Thailand.js) and [PyThaiNLP README_TH.md](https://github.com/PyThaiNLP/pythainlp/blob/dev/README_TH.md) (README_TH is probably translated from English).

### A1. Particles
- Short replies often open with or end on ครับ: "พังครับ ต้อง setup builder ด้วยตอนขึ้น prod" ([130710#comment-1263832](https://www.blognone.com/node/130710#comment-1263832)), "เจอเหมือนกันครับ เอ๊ะอะนึกอะไรไม่ออกก็ any 😅" ([#comment-1263841](https://www.blognone.com/node/130710#comment-1263841))
- นะครับ: "ตัวโครงการ TypeScript น่าจะไม่มี runtime นะครับ" ([151102#comment-1354552](https://www.blognone.com/node/151102#comment-1354552)), "นั่นสิครับ เรียกว่าอะไรรึครับ? ถ้า c++ ยากเพราะ pointer rust มี pointer หลายชนิดกว่าอีกนะครับ" ([135472#comment-1292554](https://www.blognone.com/node/135472#comment-1292554))
- ครับ first, plain sentences after: "ผมมองว่ามันยากคนละแบบอ่ะครับ C++ นี่เอาเข้าจริงมัน "หยวน" กับ Code กว่าครับ ... แต่ Rust ก็อย่างคอมเมนต์อื่นบอกล่ะครับ ละเอียดแล้ว strict มากจนบางทีผมรำคาญก็มีนะ" ([#comment-1292582](https://www.blognone.com/node/135472#comment-1292582)), "ไม่เกี่ยวกับ pointer น่ะครับ" ([#comment-1292562](https://www.blognone.com/node/135472#comment-1292562))
- No ครับ at all: "แต่อ่าน code เข้าใจนะ" ([151761#comment-1356527](https://www.blognone.com/node/151761#comment-1356527)), "แต่ก็ยังมีคนเขียน type ด้วย any อยู่ดีสิน่า" ([#comment-1263835](https://www.blognone.com/node/130710#comment-1263835)), devahoy: "ไม่เหมือนกันเนอะ ลองดูครับ"
- คับ and ครับผม did not appear in the dev sample.

| Source | ครับ count | Thai characters | ครับ per 1,000 Thai chars |
|---|---|---|---|
| Pantip comments | 826 (plus 130 นะครับ) | 70,313 | about 11.7 |
| Blognone comments | 22 | 4,687 | about 4.7 |
| devahoy, 2 posts | 8 | 2,292 | about 3.5 |

### A2. First-person pronouns
- ผม is the default for men: "อันนี้ผมยืนยัน ผมไม่เคยเขียน python เลย" ([#comment-1356527](https://www.blognone.com/node/151761#comment-1356527)), "บริษัทผมรับ Consult การพอร์ต C/C++ มา Rust นะครับ" ([#comment-1292561](https://www.blognone.com/node/135472#comment-1292561)), devahoy: "ซึ่งปัจจุบัน ผมใช้งานหลักๆ ตอนนี้คือ Claude Code และ Codex"
- เรา as an inclusive "we/you": devahoy: "เราสามารถใช้ OpenCode ผ่าน Terminal ได้ในหลายๆโปรแกรม", "ปกติเราเรียกใช้งาน Claude Code แบบนี้ใช่มั้ย"; Blognone: "มันยากที่เราต้องเรียนรู้ concept ใหม่ๆ เพิ่มครับ" ([#comment-1292560](https://www.blognone.com/node/135472#comment-1292560))
- Addressing the reader: blogs say "เพื่อนๆ"; the README uses คุณ/ของคุณ ("ในกรณีที่ Server ของคุณรองรับ gzip เราแนะนำเป็นอย่างยิ่งให้คุณใช้ฐานข้อมูลชนิด json"); only one peer comment used คุณ, as a generic "you".

### A3. Mixing in English
- Most technical terms stay in Latin script: setup builder, prod, superset, runtime, bundle, doc, Package Manager, learning curve, testcase, best practice.
- Some loanwords in Thai script: "เพราะต้องหัด เขียน เทส และใช้งาน แก้บั๊ก" ([33649391](https://pantip.com/topic/33649391)), "ติด unknown รันไม่ออก" ([40543391](https://pantip.com/topic/40543391)), "ดูฟีเจอร์ใหม่ๆบ้างแล้ว" ([#comment-1354518](https://www.blognone.com/node/151102#comment-1354518)), "เฉยๆโค๊ดก็ไม่พัง" ([#comment-1263831](https://www.blognone.com/node/130710#comment-1263831)), "ลิ้งนี้สอนเข้าใจง่ายดีครับ" ([42433626](https://pantip.com/topic/42433626))
- Casual writers often use non-Royal-Institute spellings (อัพ, เซ็ตอัพ, ตรวจเช็ค, โปรเจค, โค๊ด); RI spellings also appear (โปรเจกต์, เวอร์ชัน).
- Edited blogs space English terms consistently; casual comments often do not ("ค่าtokenยังคุ้มกว่าไปจ้างdevจริงๆมาดูแลเยอะอยู่ดี", [#comment-1356579](https://www.blognone.com/node/151761#comment-1356579)).

### A4. Punctuation and spacing
- No sentence-final periods anywhere; a space or line break separates sentences.
- Question marks on real questions: "OpenCode คืออะไร?" (devahoy); somkiat.cc puts a space before it.
- Parentheses for asides; quotation marks around slang or a key phrase.
- Em dash: zero in all the dev text sampled. In the Wisesight corpus, 31 of 26,737 messages (0.1%) contain one.
- ไม้ยมก: in casual writing the unspaced form dominates (Pantip 218 vs 23 spaced, Blognone 22 vs 6, devahoy 23 vs 0); somkiat.cc uses the spaced form.

### A5. Emoji and 555
- Used in banter, not in explanations: "หลอกให้เข้าลัทธิได้ค่อยบอกครับ 55555" ([#comment-1263833](https://www.blognone.com/node/130710#comment-1263833)); emoji 😂 😅, ":)", "O_O". devahoy signs off with "❤️ Happy Coding".

### A6. How explanations open and close
- Blog openings: "วันนี้มาลองใช้งาน OpenCode กันดูครับ ว่า OpenCode คืออะไร? และใช้งานเบื้องต้นกันดู" (devahoy)
- Blog closings: "เพื่อนๆ ลองไปใช้งานกันดูนะครับ ว่าถูกใจหรือเปล่า", "หวังว่าจะมีประโยชน์นะครับ"
- Comments give the answer first ("พังครับ ...", "ผมว่าอยู่ที่การวางระบบ", "เริ่มที่ใช้ภาษาอะไร แต่ละอันมีทางของมันอยู่ครับ") and have no formal closing. They simply stop.

### A7. Dev slang seen in the sample
พัง, ขึ้น prod / ขึ้น project, ติดบั๊ก / แก้บั๊ก, รันไม่ออก, หยวน, ดีงาม, โหดจัด, +1, ฟีล. เวิร์ก, เอาอยู่ and งานงอก did not appear in the sample.

### A8. Markers our rules touch, as natives use them
- มัน for "it" is common: "ที่มันสำเร็จได้เพราะมันเป็น superset ของ JavaScript ธรรมดาด้วยแหละ" (1263831), "ถ้ามันแจ้ง error ว่าหาไฟล์ไม่เจอ ก็ค่อยให้ระบุค่าลงไป" (earthchie README), "(Plan mode ข้อดีคือ มันจะไม่แก้ไขโค๊ดของเรา ...)" (devahoy)
- Neutral ถูก passive is also used: "จน compiler ใหม่ถูกนำมาใช้แล้ว" (1354518), "Credentials จะถูกเก็บไว้ที่ ~/.local/share/opencode/auth.json" (devahoy), "ถูกพัฒนาด้วย JavaScript (TypeScript)" (somkiat.cc)
- สามารถ is heavy in tutorials (12 times in two devahoy posts); ซึ่ง as a loose connector; การ nominalization ("การพอร์ตในที่นี้ไม่ใช่การ Rewrite ทั้งหมดในคราวเดียวนะครับ").

| Source | Thai chars | ถูก | สามารถ | มัน | ซึ่ง | โดย | การ | ความ | Em dash |
|---|---|---|---|---|---|---|---|---|---|
| Blognone comments | 4,687 | 3 | 2 | 23 | 1 | 5 | 23 | 5 | 0 |
| Pantip comments | 70,313 | 20 | 16 | 143 | 9 | 27 | 359 | 206 | 0 |
| devahoy, 2 posts | 2,292 | 2 | 12 | 2 | 4 | 2 | 14 | 0 | 0 |

## B. General and teen social media

- Matichon, 30 Apr 2017 ([news_545520](https://www.matichon.co.th/lifestyle/news_545520)): "...บ่องตง-บอกตรงๆ, ช่ะ-ใช่ป่ะ, จุงเบย-จังเลย, ฝุดๆ-สุดๆ ไปจนถึง น้ามคาน-น่ารำคาญ, อัลไล-อะไร และ น่าร็อคอ่ะ-น่ารักอ่ะ"; "“ถถถ” ใครเล่าจะรู้ว่าแปลงมาจาก “555” ที่ลืมเปลี่ยนภาษาในแป้นพิมพ์"; headline: "จะน่ารักถ้าใช้ถูกกาลเทศะ"
- The Matter, 6 Oct 2022 ([interview](https://thematter.co/social/interview-phonetics/187250)): "อย่างคำว่า ‘งับ’ จริงๆ รูปแบบของมันมาจาก ครับ ที่ออกเสียงควบกล้ำก่อน..."
- The Matter, 7 Nov 2025 ([variations of ครับ](https://thematter.co/social/the-variations-of-krub/252220)): "ไม่ว่าจะเป็น ค้าบ, ครัช, ครัฟ, งับ หรือ ฮ้าฟฟู่ ที่เราพบได้ทั่วไปในโซเชียลมีเดีย"; "ส่วน ‘คับ’ ก็ถือว่าเป็นการออกเสียง ‘ครับ’ แบบขี้เกียจในระดับที่คนทั่วไปยังพอรับได้อยู่"
- Thai Wikipedia [ภาษาวิบัติ](https://th.wikipedia.org/wiki/ภาษาวิบัติ): quotes the Royal Institute's secretary-general: "วัยรุ่นใช้ภาษาแช็ตเฉพาะบนอินเทอร์เน็ต และสื่อสารภายในวัยรุ่นเท่านั้น ยังไม่พบนำมาใช้ในการเขียนหรือการทำงาน"

Wisesight Sentiment (26,737 messages, simple string matching): 555+ 7.4%, stretched letters 10.1%, emoji 9.8%, ครับ 9.4%, ค่ะ 8.9%, จ้า 3.5%, คับ 2.0%, ถถถ 0.1%, em dash 0.1%.

| Category | Traits |
|---|---|
| Fits semi-formal dev chat | ครับ/นะครับ at the start or end of a reply; occasional นะ, แหละ, เนอะ; parentheses for asides; quotes around slang; slang like พัง, ขึ้น prod, รันไม่ผ่าน, ติดบั๊ก |
| Borderline (jokes only) | 555 and a single 😅 or 😂 |
| Does not fit | Playful respellings (จุงเบย, อัลไล, บ่องตง, ชิมิ); cute particles (งับ, ค้าบ, ครัช, ฮ้าฟฟู่, จ้า); stretched vowels; ถถถ; heavy emoji; teen pronouns; กู/มึง; คับ |

## C. Native Thai corpora

| Corpus | Register | Size | License | Link | Closeness to semi-formal tech writing |
|---|---|---|---|---|---|
| pythainlp/blognone_news | Blognone editorial tech news | 18,712 rows | CC BY 3.0 | [HF](https://huggingface.co/datasets/pythainlp/blognone_news) | High |
| Noxturnix/blognone-20230430 | Blognone posts 2020–2023 | 18,623 posts | CC BY 3.0 TH | [HF](https://huggingface.co/datasets/Noxturnix/blognone-20230430) | High |
| Wisesight Sentiment | Informal social media 2016–2019 | 26,737 messages | CC0 | [GitHub](https://github.com/PyThaiNLP/wisesight-sentiment) | Low (informal baseline) |
| Wongnai reviews | Restaurant reviews | 10K–100K | LGPL-3.0 | [GitHub](https://github.com/wongnai/wongnai-corpus) | Low |
| prachathai-67k | News | 67,889 articles | Apache-2.0 | [GitHub](https://github.com/PyThaiNLP/prachathai-67k) | Low to medium |
| Thai Wikipedia dump | Encyclopedic | ~500 MB bz2 | CC BY-SA (not checked) | [dumps](https://dumps.wikimedia.org/thwiki/latest/) | Medium-low |
| LST20 (NECTEC) | News, POS-tagged | 3.16M words | Non-commercial/research | [HF](https://huggingface.co/datasets/lst-nectec/lst20) | Low (POS tags could separate passive ถูก) |
| OSCAR 23.01 / CulturaX | Web text | very large | access-restricted / mC4+OSCAR terms | [OSCAR](https://huggingface.co/datasets/oscar-corpus/OSCAR-2301), [CulturaX](https://huggingface.co/datasets/uonlp/CulturaX) | Mixed |
| Pantip_QA_200000_20220220 | Pantip Q&A | 100K–1M | no license declared | [HF](https://huggingface.co/datasets/amitysolution/Pantip_QA_200000_20220220) | Medium |
| TNC word frequencies | Thai National Corpus unigrams | 33.5M tokens | PyThaiNLP data | [tnc_freq.txt](https://raw.githubusercontent.com/PyThaiNLP/pythainlp/dev/pythainlp/corpus/tnc_freq.txt) | Baseline |
| scb-mt-en-th-2020 (translated side) | EN–TH pairs | >1M pairs | CC BY-SA 4.0 | [HF](https://huggingface.co/datasets/airesearch/scb_mt_enth_2020) | Translated counterpart |
| generated_reviews_enth | Google-translated generated reviews | 100K–1M | not checked | [HF](https://huggingface.co/datasets/airesearch/generated_reviews_enth) | Negative examples |

Native baselines per million tokens (all word senses): TNC ถูก 1,660 · โดน 176 · ได้รับ 1,253 · สามารถ 1,329 · มัน 1,969 · ซึ่ง 3,586 · โดย 3,307 · การ 17,654 · ความ 6,886 · ครับ 696.

Kenny & Satthachai (2018), *Meta* 63(3) ([PDF](https://doras.dcu.ie/29993/1/Kenny%20and%20Satthachai%20(2018)%20Meta%201060165ar.pdf)), translated treaties vs Thai legislation: ถูก 2,089.36 vs 1,290.64 per million (about 1.62×); ได้รับ 5,710.90 vs 3,257.75 (about 1.75×). Legal text only. No published native-vs-translated figures turned up for มัน, em dash, ซึ่ง, โดย, or การ/ความ.

## D. Where ChatGPT's Thai ability might come from

- GPT-4 Technical Report ([PDF](https://cdn.openai.com/papers/gpt-4.pdf)): MMLU translated with Azure Translate; Thai scores 71.8% in Figure 5 (label matched by order, check against the figure).
- OpenAI's MMMLU benchmark does not include Thai.
- Thailand market news (ChatGPT Go launch, partnerships) says nothing about how the model learned Thai.
- No credible OpenAI publication describes Thai training data or Thai-specific tuning.

## Candidate rules from the evidence

Do: ผม for the speaker and เรา as inclusive "we"; ครับ on the opening/answer sentence and the closing line; answer first; English terms in Latin script with spaces; parentheses for asides; keep the no-em-dash rule; no periods.
Don't: teen respellings, cute particles, stretched vowels, ถถถ, คับ; no 555 or emoji inside explanations.
Pushback: natives use มัน for tools and code, and neutral ถูก, so prefer density thresholds over bans; สามารถ alone is not a translationese marker; unspaced ๆ and spellings like อัพ, เช็ค are common native usage, so the linter should not count them as translationese.

Not reached: openai.com GPT-4o page (403), Bangkok Post (paywall), TNC site (404). Not attempted: X, Facebook groups, YouTube, Medium, the Satthachai thesis.
