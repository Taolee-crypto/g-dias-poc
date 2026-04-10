lines = open("src/ai_report.py", encoding="utf-8").readlines()
for i, line in enumerate(lines):
    if 'a.get("severity")' in line:
        lines[i] = line.replace(
            'a.get("severity") == "CRITICAL"',
            '(a.get("severity") if isinstance(a, dict) else getattr(a, "severity", "")) == "CRITICAL"'
        )
        print(f"고침: {i+1}번 줄")
open("src/ai_report.py", "w", encoding="utf-8").writelines(lines)
print("완료")
