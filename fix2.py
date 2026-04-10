lines = open("dashboard.py", encoding="utf-8").readlines()
for i, line in enumerate(lines):
    if "c.conflict_notes" in line:
        lines[i] = line.replace(
            "if c.conflict_notes:",
            "if getattr(c, 'conflict_notes', None):"
        ).replace(
            "st.info(c.conflict_notes)",
            "st.info(getattr(c, 'conflict_notes', ''))"
        )
        print(f"고침: {i+1}번 줄")
open("dashboard.py", "w", encoding="utf-8").writelines(lines)
print("완료")
