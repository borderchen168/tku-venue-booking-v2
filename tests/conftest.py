"""pytest 共用設定：fixture 分檔放在 tests/fixtures/（planning.md R7，降低平行 Task 衝突）。"""

pytest_plugins = [
    'tests.fixtures.settings',
    'tests.fixtures.clock',
    'tests.fixtures.app',
]
