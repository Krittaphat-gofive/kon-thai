I'll check for relevant skills and look at the project first.


<invoke name="Bash">
<parameter name="command">ls -la "C:/Users/<user>/.claude/skills" 2>/dev/null | head -50; echo "---PLUGINS---"; ls "C:/Users/<user>/.claude/plugins" 2>/dev/null | head -20</parameter>
<parameter name="description">List available skills on disk</parameter>
</invoke>
<invoke name="Bash">
<parameter name="command">cd "E:/gofive/kon-thai-skill/eval/runs/r1-baseline/control/_work" && ls -la && echo "---TREE---" && find . -maxdepth 3 -not -path '*/node_modules/*' -not -path '*/.git/*' | head -60</parameter>
<parameter name="description">Inspect working directory</parameter>
</invoke>


---PLUGINS---
config.json
repos
marketplace
cache
installed
---
