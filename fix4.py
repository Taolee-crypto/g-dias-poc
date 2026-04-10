lines = open("dashboard.py", encoding="utf-8").readlines()
for i, line in enumerate(lines):
    if "force_refresh=True" in line:
        lines[i] = line.replace("force_refresh=True", "force=True")
        print(f"고침: {i+1}번 줄")
    if "force_refresh=False" in line:
        lines[i] = line.replace("force_refresh=False", "force=False")
        print(f"고침: {i+1}번 줄")
open("dashboard.py", "w", encoding="utf-8").writelines(lines)
print("완료")
