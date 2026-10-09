import io
with io.open('client/client.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'Vuoi raccoglierlo?' in line and 'askyesno' not in line:
        lines[i-1] = lines[i-1].rstrip() + '\\n' + line.lstrip()
        lines[i] = ''
with io.open('client/client.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
