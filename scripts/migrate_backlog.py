"""將 docs/backlog/ 的 Markdown 項目一次性遷移到 GitHub Issues 與 GitHub Project（IS-001）。

- 以標題前綴（例如 `[US-004]`）判斷 Issue 是否已存在，可重複執行而不會重複建立。
- 已存在的 Issue 與已在 Project 中的項目不覆寫內容與欄位，避免蓋掉遷移後在 GitHub 上的修改。
- 階層：Epic → Story → Task 以 sub-issues 表示；Task 對應多個 Story 時以第一個為父項目。
- `depends_on` 轉為 issue dependencies（blocked by）。

用法（需先以 `gh auth login` 登入，scopes 含 repo、project）：

    python scripts/migrate_backlog.py --dry-run
    python scripts/migrate_backlog.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKLOG_DIR = PROJECT_ROOT / 'docs' / 'backlog'
MAPPING_FILE = BACKLOG_DIR / 'github-mapping.md'
# 遷移前最後一個含 docs/backlog/ Markdown 項目的 main commit
PRE_MIGRATION_COMMIT = '52709d3'
# 遷移時才建立、不存在於 PRE_MIGRATION_COMMIT 的項目
CREATED_DURING_MIGRATION = {'IS-001', 'IS-002', 'IS-003'}
REPO_PATTERN = re.compile(r'[A-Za-z0-9-]+/[A-Za-z0-9._-]+')

DEFAULT_REPO = 'borderchen168/tku-venue-booking-v2'
DEFAULT_PROJECT_TITLE = '淡江場地預約系統'
PROJECT_DESCRIPTION = '淡江場地預約系統（tku-venue-booking-v2）的 Product Backlog 與 Sprint 看板'

# 建立順序：父項目必須先於子項目建立，內文才能引用其 issue 編號
KIND_DIRS: dict[str, str] = {'epic': 'epics', 'story': 'stories', 'task': 'tasks', 'issue': 'issues', 'bug': 'bugs'}
KEY_PATTERN = re.compile(r'^(EP|US|T|BUG|IS)-\d{3}$')
TITLE_PATTERN = re.compile(r'^\[((?:EP|US|T|BUG|IS)-\d{3})\] ')

ROLES = [
    'product-owner',
    'scrum-master',
    'system-analyst',
    'ui-ux-designer',
    'dba',
    'backend-developer',
    'frontend-developer',
    'tester',
    'code-reviewer',
    'security-reviewer',
    'qa',
]

LABELS: list[tuple[str, str, str]] = [
    ('type:epic', '5319e7', 'Epic(史詩)：一組相關的 Story'),
    ('type:story', '0e8a16', 'Story(使用者故事)：具使用者價值的需求'),
    ('type:task', '1d76db', 'Task(任務)：Story 拆解出的開發工作'),
    ('type:bug', 'd73a4a', 'Bug(缺陷)'),
    ('type:issue', 'fbca04', 'Issue(議題)：未分類問題、雜務或待釐清事項'),
    ('severity:critical', 'b60205', 'Bug 嚴重度：critical'),
    ('severity:major', 'd93f0b', 'Bug 嚴重度：major'),
    ('severity:minor', 'fbca04', 'Bug 嚴重度：minor'),
    ('severity:trivial', 'c2e0c6', 'Bug 嚴重度：trivial'),
    *[(f'role:{role}', 'c5def5', f'負責角色（subagent）：{role}') for role in ROLES],
]
GITHUB_DEFAULT_LABELS = {
    'accessibility',
    'bug',
    'documentation',
    'duplicate',
    'enhancement',
    'good first issue',
    'help wanted',
    'invalid',
    'question',
    'wontfix',
}

STATUS_OPTIONS: list[tuple[str, str, str]] = [
    ('Todo', 'GRAY', '尚未開始'),
    ('In Progress', 'YELLOW', '開發中'),
    ('Review', 'BLUE', '審查中（Code Review / Security Review / QA）'),
    ('Done', 'GREEN', '已完成並合併'),
    ('Blocked', 'RED', '被阻擋，需排除相依或待決事項'),
]
STATUS_MAP = {'todo': 'Todo', 'in-progress': 'In Progress', 'review': 'Review', 'done': 'Done', 'blocked': 'Blocked'}

PRIORITY_OPTIONS: list[tuple[str, str, str]] = [
    ('Must', 'RED', 'MoSCoW：必須有'),
    ('Should', 'ORANGE', 'MoSCoW：應該有'),
    ('Could', 'BLUE', 'MoSCoW：可以有'),
    ("Won't", 'GRAY', 'MoSCoW：這次不做'),
]
PRIORITY_MAP = {'must': 'Must', 'should': 'Should', 'could': 'Could', 'wont': "Won't"}

SPRINT_DURATION_DAYS = 14
SPRINTS: list[tuple[str, str]] = [('Sprint 1', '2026-11-09'), ('Sprint 2', '2026-11-23'), ('Sprint 3', '2026-12-07')]

# 建立內容時 GitHub 有 secondary rate limit，每次寫入之間稍作等待
WRITE_INTERVAL_SECONDS = 1.0

type Meta = str | list[str] | None


class GhError(RuntimeError):
    """`gh` 指令執行失敗。"""


@dataclass
class Item:
    """一個 Backlog 項目（Epic / Story / Task / Issue / Bug）。"""

    key: str
    kind: str
    title: str
    path: Path
    meta: dict[str, Meta]
    body: str
    number: int | None = None
    db_id: int | None = None
    node_id: str | None = None
    is_open: bool = True
    created_now: bool = False

    @property
    def issue_title(self) -> str:
        """GitHub Issue 標題，保留原編號作為前綴。"""
        return f'[{self.key}] {self.title}'

    def meta_str(self, name: str) -> str | None:
        """取得單值欄位；空值回傳 None。"""
        value = self.meta.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value or None

    def meta_list(self, name: str) -> list[str]:
        """取得清單欄位；單值視為一個元素的清單。"""
        value = self.meta.get(name)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @property
    def parent_key(self) -> str | None:
        """sub-issue 的父項目編號。"""
        if self.kind == 'story':
            return self.meta_str('epic')
        if self.kind == 'task':
            return self.meta_str('story')
        if self.kind == 'bug':
            return self.meta_str('related')
        return None


@dataclass
class ProjectInfo:
    """GitHub Project 與其欄位的 node id。"""

    project_id: str
    url: str
    fields: dict[str, dict[str, Any]]


# ---------- Markdown 解析 ----------


def parse_frontmatter(text: str) -> tuple[dict[str, Meta], str]:
    """解析簡易 YAML frontmatter（`key: value`、`key: [a, b]`、行尾 `# 註解`）。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        raise ValueError('缺少 frontmatter')
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
    if end is None:
        raise ValueError('frontmatter 缺少結尾的 ---')
    meta: dict[str, Meta] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        name, _, raw = line.partition(':')
        value = re.sub(r'\s+#.*$', '', raw).strip()
        if value.startswith('[') and value.endswith(']'):
            meta[name.strip()] = [v.strip() for v in value[1:-1].split(',') if v.strip()]
        else:
            meta[name.strip()] = value or None
    body = '\n'.join(lines[end + 1 :]).strip()
    return meta, body


def load_items() -> list[Item]:
    """依建立順序讀取所有 Backlog 項目。"""
    items: list[Item] = []
    for kind, dirname in KIND_DIRS.items():
        for path in sorted((BACKLOG_DIR / dirname).glob('*.md')):
            try:
                meta, body = parse_frontmatter(path.read_text(encoding='utf-8'))
            except ValueError as exc:
                raise ValueError(f'{path}：{exc}') from exc
            key = meta.get('id')
            title = meta.get('title')
            if not isinstance(key, str) or not KEY_PATTERN.match(key) or not isinstance(title, str):
                raise ValueError(f'{path}：id 或 title 格式不正確')
            items.append(Item(key=key, kind=kind, title=title, path=path, meta=meta, body=body))
    return items


def validate(items: list[Item]) -> None:
    """在任何 GitHub 寫入之前檢查：編號不重複、參照存在、欄位值都能對應到 Label 或 Project 選項。"""
    keys = [item.key for item in items]
    duplicates = {k for k in keys if keys.count(k) > 1}
    if duplicates:
        raise ValueError(f'編號重複：{sorted(duplicates)}')
    known = set(keys)
    sprint_titles = {title for title, _ in SPRINTS}
    errors: list[str] = []
    for item in items:
        refs = [*item.meta_list('depends_on'), *(item.meta_list('story') if item.kind == 'task' else [])]
        if item.parent_key:
            refs.append(item.parent_key)
        missing = [r for r in refs if r not in known]
        if missing:
            errors.append(f'{item.key} 參照不存在的項目：{missing}')
        status = item.meta_str('status')
        if status and status not in STATUS_MAP:
            errors.append(f'{item.key} 的 status 不正確：{status}')
        priority = item.meta_str('priority')
        if priority and priority not in PRIORITY_MAP:
            errors.append(f'{item.key} 的 priority 不正確：{priority}')
        sprint = item.meta_str('sprint')
        if sprint and sprint_title(sprint) not in sprint_titles:
            errors.append(f'{item.key} 的 sprint 不在 SPRINTS 中：{sprint}')
        assignee = item.meta_str('assignee')
        if assignee and assignee not in ROLES:
            errors.append(f'{item.key} 的 assignee 不是已知角色：{assignee}')
        severity = item.meta_str('severity')
        if item.kind == 'bug' and severity and f'severity:{severity}' not in {name for name, _, _ in LABELS}:
            errors.append(f'{item.key} 的 severity 不正確：{severity}')
    if errors:
        raise ValueError('\n'.join(errors))


def sprint_title(sprint: str) -> str:
    """`sprint-01` → `Sprint 1`；格式不符時原樣回傳（交由 validate 報錯）。"""
    match = re.fullmatch(r'sprint-(\d+)', sprint)
    return f'Sprint {int(match.group(1))}' if match else sprint


def build_body(item: Item, by_key: dict[str, Item]) -> str:
    """組合 Issue 內文：原始資訊表 + 原 Markdown 內文（去掉重複的 H1 標題）。"""

    def ref(key: str) -> str:
        target = by_key[key]
        return f'#{target.number}（{key}）' if target.number else key

    rows: list[tuple[str, str]] = [('原編號', item.key)]
    if item.kind == 'task':
        rows.append(('相關 Story', '、'.join(ref(k) for k in item.meta_list('story'))))
    for name, label in [('type', '類型'), ('severity', '嚴重度'), ('assignee', '負責角色'), ('reported_by', '回報者')]:
        value = item.meta_str(name)
        if value:
            rows.append((label, value))
    branch = item.meta_str('branch')
    if branch:
        rows.append(('Branch', f'`{branch}`'))
    created = item.meta_str('created')
    if created:
        rows.append(('建立日期', created))
    rows.append(('遷移來源', f'`{item.path.relative_to(PROJECT_ROOT).as_posix()}`'))

    table = '\n'.join(['| 項目 | 內容 |', '|---|---|', *[f'| {k} | {v} |' for k, v in rows]])
    body = re.sub(rf'^#\s+{re.escape(item.key)}\b[^\n]*\n*', '', item.body, count=1)
    return f'{table}\n\n---\n\n{body}\n'


# ---------- gh 包裝 ----------


class GitHub:
    """以 `gh` CLI 呼叫 GitHub REST / GraphQL API；dry-run 時只印出寫入動作。"""

    def __init__(self, repo: str, *, dry_run: bool) -> None:
        gh_path = shutil.which('gh')
        if gh_path is None:
            raise GhError('找不到 gh CLI，請先安裝並執行 gh auth login')
        self.gh = gh_path
        self.repo = repo
        self.dry_run = dry_run
        self.writes = 0

    def _run(self, args: list[str], payload: Any = None) -> Any:
        proc = subprocess.run(
            [self.gh, *args],
            input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False,
        )
        if proc.returncode != 0:
            raise GhError(f'gh {" ".join(args[:3])} 失敗：{proc.stderr.strip()}')
        out = proc.stdout.strip()
        return json.loads(out) if out else None

    def get(self, path: str) -> Any:
        """GET（自動分頁，回傳合併後的清單或單一物件）。"""
        pages = self._run(['api', '--paginate', '--slurp', path])
        if isinstance(pages, list) and pages and all(isinstance(p, list) for p in pages):
            return [x for page in pages for x in page]
        return pages[0] if isinstance(pages, list) and len(pages) == 1 else pages

    def query(self, query: str, **variables: Any) -> Any:
        """唯讀 GraphQL 查詢。"""
        return self._run(['api', 'graphql', '--input', '-'], {'query': query, 'variables': variables})['data']

    def write(
        self, description: str, method: str = '', path: str = '', payload: Any = None, *, graphql: str = '', quiet: bool = False
    ) -> Any:
        """寫入動作：dry-run 時只印出說明，否則執行並稍作等待。quiet 時不印出說明（由呼叫端彙整輸出）。"""
        prefix = '[dry-run] ' if self.dry_run else ''
        if not quiet:
            print(f'  {prefix}{description}')
        if self.dry_run:
            return None
        if graphql:
            result = self._run(['api', 'graphql', '--input', '-'], {'query': graphql, 'variables': payload or {}})['data']
        else:
            args = ['api', '-X', method, path]
            if payload is not None:
                args += ['--input', '-']
            result = self._run(args, payload)
        self.writes += 1
        time.sleep(WRITE_INTERVAL_SECONDS)
        return result


# ---------- Labels ----------


def ensure_labels(gh: GitHub, *, delete_defaults: bool) -> None:
    """建立缺少的 Labels，並可刪除 GitHub 預設 Labels。"""
    print('\n== Labels')
    existing = {label['name'] for label in gh.get(f'repos/{gh.repo}/labels?per_page=100')}
    for name, color, description in LABELS:
        if name not in existing:
            gh.write(f'建立 label {name}', 'POST', f'repos/{gh.repo}/labels', {'name': name, 'color': color, 'description': description})
    if delete_defaults:
        for name in sorted(existing & GITHUB_DEFAULT_LABELS):
            gh.write(f'刪除 GitHub 預設 label {name}', 'DELETE', f'repos/{gh.repo}/labels/{quote(name)}')


# ---------- Project ----------

FIELDS_QUERY = """
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          ... on ProjectV2FieldCommon { id name dataType }
          ... on ProjectV2SingleSelectField { options { id name } }
          ... on ProjectV2IterationField { configuration { iterations { id title startDate } } }
        }
      }
    }
  }
}
"""


def _options(options: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [{'name': n, 'color': c, 'description': d} for n, c, d in options]


def ensure_project(gh: GitHub, title: str) -> ProjectInfo | None:
    """建立或找到 Project，設為公開、連結 repo，並建立所需欄位。dry-run 且 Project 不存在時回傳 None。"""
    print('\n== Project')
    owner, name = gh.repo.split('/')
    data = gh.query(
        'query($login: String!, $owner: String!, $name: String!) {'
        ' user(login: $login) { id projectsV2(first: 100) { nodes { id title url } } }'
        ' repository(owner: $owner, name: $name) { id } }',
        login=owner,
        owner=owner,
        name=name,
    )
    project = next((p for p in data['user']['projectsV2']['nodes'] if p['title'] == title), None)
    if project is None:
        created = gh.write(
            f'建立 Project「{title}」並連結 {gh.repo}',
            payload={'ownerId': data['user']['id'], 'title': title, 'repositoryId': data['repository']['id']},
            graphql='mutation($ownerId: ID!, $title: String!, $repositoryId: ID!) {'
            ' createProjectV2(input: {ownerId: $ownerId, title: $title, repositoryId: $repositoryId}) { projectV2 { id url } } }',
        )
        if created is None:
            for line in [
                '設定 Project 為公開並加上簡短說明',
                'Status 欄位選項改為 ' + ' / '.join(n for n, _, _ in STATUS_OPTIONS),
                '建立 Priority 欄位：' + ' / '.join(n for n, _, _ in PRIORITY_OPTIONS),
                '建立 Story Points 欄位（number）',
                '建立 Sprint 欄位（iteration）：' + '、'.join(f'{t} {s} 起' for t, s in SPRINTS) + f'，各 {SPRINT_DURATION_DAYS} 天',
            ]:
                print(f'  [dry-run] {line}')
            return None
        project = created['createProjectV2']['projectV2']
        _configure_new_project(gh, project['id'])
    else:
        print(f'  已存在：{project["url"]}')
    return _ensure_fields(gh, project['id'], project['url'])


def _configure_new_project(gh: GitHub, project_id: str) -> None:
    gh.write(
        '設定 Project 為公開並加上簡短說明',
        payload={'id': project_id, 'desc': PROJECT_DESCRIPTION},
        graphql='mutation($id: ID!, $desc: String!) {'
        ' updateProjectV2(input: {projectId: $id, public: true, shortDescription: $desc}) { projectV2 { id } } }',
    )


REQUIRED_FIELDS = ('Status', 'Priority', 'Story Points', 'Sprint')


def _ensure_fields(gh: GitHub, project_id: str, url: str) -> ProjectInfo | None:
    fields = {f['name']: f for f in gh.query(FIELDS_QUERY, id=project_id)['node']['fields']['nodes'] if f}
    status = fields['Status']
    if [o['name'] for o in status['options']] != [n for n, _, _ in STATUS_OPTIONS]:
        gh.write(
            '更新 Status 欄位選項',
            payload={'fieldId': status['id'], 'options': _options(STATUS_OPTIONS)},
            graphql='mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {'
            ' updateProjectV2Field(input: {fieldId: $fieldId, singleSelectOptions: $options}) { projectV2Field { __typename } } }',
        )
    create_field = 'mutation($input: CreateProjectV2FieldInput!) { createProjectV2Field(input: $input) { projectV2Field { __typename } } }'
    if 'Priority' not in fields:
        gh.write(
            '建立 Priority 欄位',
            payload={
                'input': {
                    'projectId': project_id,
                    'dataType': 'SINGLE_SELECT',
                    'name': 'Priority',
                    'singleSelectOptions': _options(PRIORITY_OPTIONS),
                }
            },
            graphql=create_field,
        )
    if 'Story Points' not in fields:
        gh.write(
            '建立 Story Points 欄位',
            payload={'input': {'projectId': project_id, 'dataType': 'NUMBER', 'name': 'Story Points'}},
            graphql=create_field,
        )
    if 'Sprint' not in fields:
        iterations = [{'title': t, 'startDate': s, 'duration': SPRINT_DURATION_DAYS} for t, s in SPRINTS]
        gh.write(
            '建立 Sprint 欄位（iteration）',
            payload={
                'input': {
                    'projectId': project_id,
                    'dataType': 'ITERATION',
                    'name': 'Sprint',
                    'iterationConfiguration': {
                        'startDate': SPRINTS[0][1],
                        'duration': SPRINT_DURATION_DAYS,
                        'iterations': iterations,
                    },
                }
            },
            graphql=create_field,
        )
    if not gh.dry_run:
        fields = {f['name']: f for f in gh.query(FIELDS_QUERY, id=project_id)['node']['fields']['nodes'] if f}
    if any(name not in fields for name in REQUIRED_FIELDS):
        # 只會發生在 dry-run：欄位尚未建立，無法取得選項 id
        return None
    return ProjectInfo(project_id, url, fields)


# ---------- Issues ----------


LIST_ISSUES_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, after: $after, states: [OPEN, CLOSED]) {
      nodes { number title state databaseId id }
      pageInfo { hasNextPage endCursor }
    }
    pullRequests(last: 1) { nodes { number } }
  }
}
"""


def load_existing_issues(gh: GitHub, items: list[Item]) -> int:
    """以標題前綴對應既有 Issue；回傳下一個可能的 issue 編號（供 dry-run 預估）。

    使用 GraphQL：新 repo 的 REST 列表 API 與 search 有索引延遲，可能暫時回傳 0 筆。
    """
    by_key = {item.key: item for item in items}
    owner, name = gh.repo.split('/')
    max_number = 0
    after = None
    while True:
        repo = gh.query(LIST_ISSUES_QUERY, owner=owner, name=name, after=after)['repository']
        for pr in repo['pullRequests']['nodes']:
            max_number = max(max_number, int(pr['number']))
        for issue in repo['issues']['nodes']:
            max_number = max(max_number, int(issue['number']))
            match = TITLE_PATTERN.match(issue['title'])
            if match and match.group(1) in by_key:
                item = by_key[match.group(1)]
                item.number, item.db_id, item.node_id = issue['number'], issue['databaseId'], issue['id']
                item.is_open = issue['state'] == 'OPEN'
        if not repo['issues']['pageInfo']['hasNextPage']:
            break
        after = repo['issues']['pageInfo']['endCursor']
    return max_number + 1


def ensure_issues(gh: GitHub, items: list[Item]) -> None:
    """建立缺少的 Issue；狀態為 done 的項目在建立時一併關閉（既有 Issue 的開關狀態不更動）。"""
    print('\n== Issues')
    by_key = {item.key: item for item in items}
    next_number = load_existing_issues(gh, items)
    for item in items:
        if item.number is None:
            labels = [f'type:{item.kind}']
            assignee = item.meta_str('assignee')
            if assignee:
                labels.append(f'role:{assignee}')
            severity = item.meta_str('severity')
            if item.kind == 'bug' and severity:
                labels.append(f'severity:{severity}')
            result = gh.write(
                f'建立 #{next_number if gh.dry_run else "?"} {item.issue_title}  labels={labels}',
                'POST',
                f'repos/{gh.repo}/issues',
                {'title': item.issue_title, 'body': build_body(item, by_key), 'labels': labels},
            )
            item.created_now = True
            if result is None:
                item.number = next_number
            else:
                item.number, item.db_id, item.node_id = result['number'], result['id'], result['node_id']
            next_number += 1
        if item.created_now and item.meta_str('status') == 'done' and item.is_open:
            gh.write(
                f'關閉 #{item.number} {item.key}（status: done）',
                'PATCH',
                f'repos/{gh.repo}/issues/{item.number}',
                {'state': 'closed', 'state_reason': 'completed'},
            )
            item.is_open = False


def ensure_sub_issues(gh: GitHub, items: list[Item]) -> None:
    """依 epic / story / related 建立 sub-issue 階層。"""
    print('\n== Sub-issues')
    by_key = {item.key: item for item in items}
    children: dict[str, list[Item]] = {}
    for item in items:
        if item.parent_key:
            children.setdefault(item.parent_key, []).append(item)
    for parent_key, kids in children.items():
        parent = by_key[parent_key]
        existing: set[int] = set()
        if not parent.created_now:
            existing = {i['number'] for i in gh.get(f'repos/{gh.repo}/issues/{parent.number}/sub_issues?per_page=100')}
        for kid in kids:
            if kid.number not in existing:
                gh.write(
                    f'#{parent.number} {parent.key} ← 子項目 #{kid.number} {kid.key}',
                    'POST',
                    f'repos/{gh.repo}/issues/{parent.number}/sub_issues',
                    {'sub_issue_id': kid.db_id},
                )


def ensure_dependencies(gh: GitHub, items: list[Item]) -> None:
    """將 depends_on 轉為 blocked-by 關聯。"""
    print('\n== Dependencies（blocked by）')
    by_key = {item.key: item for item in items}
    for item in items:
        deps = item.meta_list('depends_on')
        if not deps:
            continue
        existing: set[int] = set()
        if not item.created_now:
            existing = {i['number'] for i in gh.get(f'repos/{gh.repo}/issues/{item.number}/dependencies/blocked_by?per_page=100')}
        for dep_key in deps:
            dep = by_key[dep_key]
            if dep.number not in existing:
                gh.write(
                    f'#{item.number} {item.key} blocked by #{dep.number} {dep.key}',
                    'POST',
                    f'repos/{gh.repo}/issues/{item.number}/dependencies/blocked_by',
                    {'issue_id': dep.db_id},
                )


# ---------- Project items ----------

ITEMS_QUERY = """
query($id: ID!, $after: String) {
  node(id: $id) {
    ... on ProjectV2 {
      items(first: 100, after: $after) {
        nodes {
          id
          content { ... on Issue { number repository { nameWithOwner } } }
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue { field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldNumberValue { field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldIterationValue { field { ... on ProjectV2FieldCommon { name } } }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

SET_FIELD = """
mutation($project: ID!, $item: ID!, $field: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(input: {projectId: $project, itemId: $item, fieldId: $field, value: $value}) {
    projectV2Item { id }
  }
}
"""


def field_values(item: Item, project: ProjectInfo | None) -> list[tuple[str, str, dict[str, Any]]]:
    """計算要寫入 Project 的欄位：(欄位名稱, 顯示值, GraphQL value)。"""

    def option(field: str, name: str) -> dict[str, Any]:
        if project is None:
            return {}
        return {'singleSelectOptionId': next(o['id'] for o in project.fields[field]['options'] if o['name'] == name)}

    values: list[tuple[str, str, dict[str, Any]]] = []
    status = STATUS_MAP.get(item.meta_str('status') or 'todo', 'Todo')
    values.append(('Status', status, option('Status', status)))
    priority = item.meta_str('priority')
    if priority:
        values.append(('Priority', PRIORITY_MAP[priority], option('Priority', PRIORITY_MAP[priority])))
    points = item.meta_str('story_points')
    if points is not None and points.isdigit():
        values.append(('Story Points', points, {'number': float(points)}))
    sprint = item.meta_str('sprint')
    if sprint:
        title = sprint_title(sprint)
        iteration: dict[str, Any] = {}
        if project is not None:
            its = project.fields['Sprint']['configuration']['iterations']
            iteration = {'iterationId': next(i['id'] for i in its if i['title'] == title)}
        values.append(('Sprint', title, iteration))
    return values


def ensure_project_items(gh: GitHub, items: list[Item], project: ProjectInfo | None) -> None:
    """把 Issue 加入 Project，並只補寫尚未設定的欄位（已設定的欄位不覆寫）。"""
    print('\n== Project 項目與欄位')
    existing: dict[int, tuple[str, set[str]]] = {}
    if project is not None:
        after = None
        while True:
            page = gh.query(ITEMS_QUERY, id=project.project_id, after=after)['node']['items']
            for node in page['nodes']:
                content = node['content']
                if content and content.get('repository', {}).get('nameWithOwner') == gh.repo:
                    filled = {v['field']['name'] for v in node['fieldValues']['nodes'] if v and v.get('field')}
                    existing[content['number']] = (node['id'], filled)
            if not page['pageInfo']['hasNextPage']:
                break
            after = page['pageInfo']['endCursor']
    for item in items:
        values = field_values(item, project)
        if item.number in existing:
            item_id: str | None = existing[item.number][0]
            filled = existing[item.number][1]
        else:
            summary = '、'.join(f'{name}={shown}' for name, shown, _ in values)
            added = gh.write(
                f'加入 #{item.number} {item.key}：{summary}',
                payload={'project': project.project_id if project else '', 'content': item.node_id},
                graphql='mutation($project: ID!, $content: ID!) {'
                ' addProjectV2ItemById(input: {projectId: $project, contentId: $content}) { item { id } } }',
            )
            item_id = added['addProjectV2ItemById']['item']['id'] if added else None
            filled = set()
        for name, shown, value in values:
            if name in filled:
                continue
            if item.number in existing:
                print(f'  {"[dry-run] " if gh.dry_run else ""}補寫 #{item.number} {item.key} 的 {name}={shown}')
            if project is None or item_id is None:
                continue
            gh.write(
                f'  設定 #{item.number} {name}={shown}',
                payload={'project': project.project_id, 'item': item_id, 'field': project.fields[name]['id'], 'value': value},
                graphql=SET_FIELD,
                quiet=True,
            )


# ---------- 對照表 ----------


def write_mapping(gh: GitHub, items: list[Item], project_url: str) -> None:
    """產生舊編號 ↔ GitHub Issue 對照表。"""
    kind_names = {'epic': 'Epic', 'story': 'Story', 'task': 'Task', 'issue': 'Issue', 'bug': 'Bug'}
    lines = [
        '# Backlog 編號對照表（Markdown → GitHub Issues）',
        '',
        f'Backlog 已於 2026-11-07 遷移到 GitHub（IS-001），之後以 [GitHub Issues](https://github.com/{gh.repo}/issues) '
        f'與 [GitHub Project「{DEFAULT_PROJECT_TITLE}」]({project_url}) 為唯一依據。',
        f'原 Markdown 檔已自 repo 移除，遷移前的版本可於 commit `{PRE_MIGRATION_COMMIT}` 查閱'
        '（IS-001～IS-003 於遷移時建立，只存在於 GitHub）。',
        '本表由 `scripts/migrate_backlog.py` 產生，供文件與 ADR 中的舊編號對照使用。',
        '',
        '| 舊編號 | 類型 | GitHub Issue | 標題 | 原始檔 |',
        '|---|---|---|---|---|',
    ]
    for item in items:
        url = f'https://github.com/{gh.repo}/issues/{item.number}'
        rel = '—' if item.key in CREATED_DURING_MIGRATION else f'`{item.path.relative_to(PROJECT_ROOT).as_posix()}`'
        lines.append(f'| {item.key} | {kind_names[item.kind]} | [#{item.number}]({url}) | {item.title} | {rel} |')
    MAPPING_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'\n已寫入 {MAPPING_FILE.relative_to(PROJECT_ROOT).as_posix()}')


def main() -> int:
    """執行遷移。"""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', default=DEFAULT_REPO, help='owner/name')
    parser.add_argument('--project-title', default=DEFAULT_PROJECT_TITLE)
    parser.add_argument('--dry-run', action='store_true', help='只列出將執行的寫入動作')
    parser.add_argument('--keep-default-labels', action='store_true', help='保留 GitHub 預設 labels')
    parser.add_argument('--force', action='store_true', help='對照表已存在（遷移已完成）時仍執行，並覆寫對照表')
    args = parser.parse_args()

    if not REPO_PATTERN.fullmatch(args.repo):
        parser.error(f'--repo 格式不正確：{args.repo}（應為 owner/name）')
    if MAPPING_FILE.exists() and not args.force:
        print(f'{MAPPING_FILE.relative_to(PROJECT_ROOT).as_posix()} 已存在，遷移已完成，不執行任何動作（需要重跑請加 --force）。')
        return 0
    try:
        items = load_items()
    except ValueError as exc:
        print(f'Backlog 檔案解析失敗，未對 GitHub 做任何寫入：\n{exc}', file=sys.stderr)
        return 1
    if not items:
        print('docs/backlog/ 沒有待遷移的項目，不執行任何動作。')
        return 0
    try:
        validate(items)
    except ValueError as exc:
        print(f'Backlog 資料檢查失敗，未對 GitHub 做任何寫入：\n{exc}', file=sys.stderr)
        return 1
    counts = {kind: sum(1 for i in items if i.kind == kind) for kind in KIND_DIRS}
    print(f'讀取 {len(items)} 個項目：{counts}')

    try:
        gh = GitHub(args.repo, dry_run=args.dry_run)
        ensure_labels(gh, delete_defaults=not args.keep_default_labels)
        project = ensure_project(gh, args.project_title)
        ensure_issues(gh, items)
        ensure_sub_issues(gh, items)
        ensure_dependencies(gh, items)
        ensure_project_items(gh, items, project)
    except GhError as exc:
        print(f'\n錯誤：{exc}', file=sys.stderr)
        return 1

    if args.dry_run:
        print('\n[dry-run] 未寫入任何資料；對照表不產生。')
    else:
        write_mapping(gh, items, project.url if project else '')
        print(f'完成，共 {gh.writes} 次寫入。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
