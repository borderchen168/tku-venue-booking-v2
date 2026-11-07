"""設定 Backlog 項目在 GitHub Project 的 Status 欄位（AGENTS.md 3.2、3.4）。

以舊式編號（標題前綴）或 issue 編號指定項目，Status 以名稱指定，不需要手動查 node id：

    python scripts/set_status.py T-004 "In Progress"
    python scripts/set_status.py 31 Review
    python scripts/set_status.py T-004            # 只顯示目前 Status

合併 PR 時 Issue 自動關閉，Project 內建 workflow（Item closed、Pull request merged）會把 Status 改為 Done，
通常不需手動設定 Done。

請在受信任的目錄執行：腳本以 `shutil.which('gh')` 尋找 gh，Windows 上可能先找到目前目錄中的同名執行檔。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from typing import Any

REPO = 'borderchen168/tku-venue-booking-v2'
OWNER = 'borderchen168'
PROJECT_NUMBER = 2
STATUSES = ['Todo', 'In Progress', 'Review', 'Done', 'Blocked']
KEY_PATTERN = re.compile(r'(EP|US|T|BUG|IS)-\d{3}')
NUMBER_PATTERN = re.compile(r'[1-9]\d{0,5}')


def gh(*args: str) -> Any:
    """執行 gh 並解析 JSON 輸出。"""
    gh_path = shutil.which('gh')
    if gh_path is None:
        raise SystemExit('找不到 gh CLI，請先安裝並執行 gh auth login')
    proc = subprocess.run([gh_path, *args], capture_output=True, text=True, encoding='utf-8', check=False)
    if proc.returncode != 0:
        raise SystemExit(f'gh {" ".join(args[:2])} 失敗：{proc.stderr.strip()}')
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def find_issue_number(ref: str) -> int:
    """將 `T-004` 或 `31` 轉為 issue 編號。

    不使用 GitHub search（有索引延遲且忽略 `[`、`]`），改為列出全部 Issue 後在本機比對標題前綴。
    """
    if NUMBER_PATTERN.fullmatch(ref):
        return int(ref)
    if not KEY_PATTERN.fullmatch(ref):
        raise SystemExit(f'編號格式不正確：{ref}（例如 T-004 或 31）')
    # 只採信 repo 擁有者建立的 Issue（AGENTS.md 3.1）：public repo 中他人建立的同前綴 Issue 不列入比對
    issues = gh('issue', 'list', '-R', REPO, '--state', 'all', '--author', OWNER, '--limit', '5000', '--json', 'number,title')
    matches = [i['number'] for i in issues if i['title'].startswith(f'[{ref}] ')]
    if len(matches) != 1:
        raise SystemExit(f'找不到唯一的 [{ref}] Issue（找到 {len(matches)} 個）')
    return int(matches[0])


def main() -> int:
    """設定或顯示 Status。"""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('item', help='舊式編號（例如 T-004）或 issue 編號')
    parser.add_argument('status', nargs='?', choices=STATUSES, help='新的 Status；省略時只顯示目前值')
    args = parser.parse_args()

    number = find_issue_number(args.item)
    project = gh('project', 'view', str(PROJECT_NUMBER), '--owner', OWNER, '--format', 'json')
    items = gh('project', 'item-list', str(PROJECT_NUMBER), '--owner', OWNER, '--format', 'json', '--limit', '1000')['items']
    item = next((i for i in items if i.get('content', {}).get('number') == number and i['content'].get('repository') == REPO), None)
    if item is None:
        hint = f'gh project item-add {PROJECT_NUMBER} --owner {OWNER} --url <issue URL>'
        print(f'#{number} 不在 Project 中，請先加入：{hint}', file=sys.stderr)
        return 1
    if args.status is None:
        print(f'#{number} {item["title"]}：{item.get("status", "（未設定）")}')
        return 0

    fields = gh('project', 'field-list', str(PROJECT_NUMBER), '--owner', OWNER, '--format', 'json')['fields']
    status_field = next(f for f in fields if f['name'] == 'Status')
    option = next(o for o in status_field['options'] if o['name'] == args.status)
    gh(
        'project',
        'item-edit',
        '--project-id',
        project['id'],
        '--id',
        item['id'],
        '--field-id',
        status_field['id'],
        '--single-select-option-id',
        option['id'],
        '--format',
        'json',
    )
    print(f'#{number} {item["title"]}：{item.get("status", "（未設定）")} → {args.status}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
