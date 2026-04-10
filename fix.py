lines = open("dashboard.py", encoding="utf-8").readlines()
for i, line in enumerate(lines):
    if 'fillcolor' in line and '"22"' in line:
        lines[i] = lines[i].replace('fillcolor=dsi_color(dsi_val) + "22"', 'fillcolor="rgba(22,163,74,0.13)"')
        print(f"고침: {i+1}번 줄")
open("dashboard.py", "w", encoding="utf-8").writelines(lines)
print("완료")
