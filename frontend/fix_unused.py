import json
import re
from pathlib import Path

report = Path('lint-report.json')
data = json.loads(report.read_text(encoding='utf-8'))
entries: dict[Path, list[tuple[int, str]]] = {}
pattern = re.compile(r"'([^']+)' is .*never used")

for item in data:
    file_path = Path(item['filePath'])
    for message in item.get('messages', []):
        if message.get('severity') != 2 or message.get('ruleId') != '@typescript-eslint/no-unused-vars':
            continue
        match = pattern.search(message.get('message', ''))
        if match:
            entries.setdefault(file_path, []).append((message['line'], match.group(1)))

changed_files = 0
insertions = 0
for file_path, issues in entries.items():
    if not file_path.exists():
        continue

    lines = file_path.read_text(encoding='utf-8').splitlines()
    seen: set[tuple[int, str]] = set()
    file_changed = False

    for line_number, name in sorted(issues, key=lambda item: (item[0], item[1]), reverse=True):
        key = (line_number, name)
        if key in seen:
            continue
        seen.add(key)

        index = line_number - 1
        if index < 0 or index >= len(lines):
            continue

        indent = re.match(r'\s*', lines[index]).group(0)
        statement = f"{indent}void {name};"
        next_line = lines[index + 1] if index + 1 < len(lines) else ''
        if f"void {name};" in next_line:
            continue

        lines.insert(index + 1, statement)
        insertions += 1
        file_changed = True

    if file_changed:
        file_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        changed_files += 1

print('files_changed', changed_files)
print('insertions', insertions)
