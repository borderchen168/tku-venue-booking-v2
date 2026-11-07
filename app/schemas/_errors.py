"""Pydantic `ValidationError` → 逐欄繁體中文錯誤訊息（error-handling.md 第 2 節）。

只使用錯誤的 `loc` 與 `type` 產生訊息，**不輸出** `input`、`ctx` 中的原始值（防止密碼或個資回顯、進日誌，
Security Review N-10）。Pydantic 的 `msg` 也不使用，因此在驗證器中寫的訊息文字**不會**顯示給使用者。

需要特定訊息的自訂驗證寫法：

- **單一欄位**（`field_validator`）：拋 `PydanticCustomError('<type>', '<僅供除錯的英文說明>')`，
  並在 `ERROR_TYPE_MESSAGES` 登記該 type 的樣板（只能使用 `{label}`）。訊息歸到該欄位。
- **跨欄位**（`model_validator(mode='after')`，錯誤的 `loc` 為空）：拋 `PydanticCustomError('<type>', ...)`，
  並在 `GLOBAL_ERROR_TYPE_MESSAGES` 登記完整訊息（不含 `{label}`）。訊息歸到 `__all__`（表單頂部）。例如：

  ```python
  @model_validator(mode='after')
  def _check_range(self) -> ClosedPeriodInput:
      if self.end_date < self.start_date:
          raise PydanticCustomError('end_before_start', 'end_date is before start_date')
      return self
  ```

  並在本模組的 `GLOBAL_ERROR_TYPE_MESSAGES` 字面值新增 `'end_before_start': '結束日期不可早於開始日期'`。

- type 名稱用 snake_case 英文，**不可**把使用者輸入放進 `PydanticCustomError` 的 message 或 context。
- 未登記的 type：欄位錯誤用 `DEFAULT_FIELD_MESSAGE`，`__all__` 用 `DEFAULT_GLOBAL_MESSAGE`。
"""

from collections.abc import Mapping
from typing import Final

from pydantic import ValidationError

GLOBAL_ERROR_KEY: Final = '__all__'

DEFAULT_FIELD_MESSAGE: Final = '{label}格式不正確'
DEFAULT_GLOBAL_MESSAGE: Final = '輸入資料不正確，請檢查後再送出'

ERROR_TYPE_MESSAGES: Final[dict[str, str]] = {
    'missing': '{label}為必填欄位',
    'string_type': '{label}格式不正確',
    'string_too_short': '{label}長度不足',
    'string_too_long': '{label}長度超過上限',
    'string_pattern_mismatch': '{label}格式不正確',
    'int_type': '{label}必須為整數',
    'int_parsing': '{label}必須為整數',
    'int_from_float': '{label}必須為整數',
    'greater_than': '{label}超出允許範圍',
    'greater_than_equal': '{label}超出允許範圍',
    'less_than': '{label}超出允許範圍',
    'less_than_equal': '{label}超出允許範圍',
    'date_type': '{label}格式不正確',
    'date_parsing': '{label}格式不正確',
    'date_from_datetime_parsing': '{label}格式不正確',
    'date_from_datetime_inexact': '{label}格式不正確',
    'time_type': '{label}格式不正確',
    'time_parsing': '{label}格式不正確',
    'enum': '{label}不是有效的選項',
    'literal_error': '{label}不是有效的選項',
    'bool_parsing': '{label}格式不正確',
    'value_error': '{label}內容不正確',
    'assertion_error': '{label}內容不正確',
}
"""欄位錯誤：Pydantic 錯誤 type → 訊息樣板（只能使用 `{label}`）。後續 Task 可新增 type，不可改既有語意。"""

GLOBAL_ERROR_TYPE_MESSAGES: Final[dict[str, str]] = {
    'extra_forbidden': '表單含有不允許的欄位，請重新整理頁面後再試',
}
"""歸到 `__all__` 的錯誤：type → 完整訊息（不含 `{label}`）。跨欄位 `model_validator` 的自訂 type 登記於此。"""


def to_field_errors(exc: ValidationError, labels: Mapping[str, str]) -> dict[str, str]:
    """把 `ValidationError` 轉成「欄位名 → 繁體中文訊息」，供 `FieldErrors` 與表單重新渲染使用。

    - 欄位以 `loc` 第一層決定；同一欄位只保留第一則訊息。
    - `loc` 第一層不在 `labels` 中（model 層級驗證、陣列索引、多餘欄位等）一律歸到 `__all__`，
      避免把使用者送出的欄位名稱回顯在頁面上；訊息查 `GLOBAL_ERROR_TYPE_MESSAGES`，未登記用預設訊息。
    - 訊息只由 `type` 決定，不使用 Pydantic 的 `msg`、`input`、`ctx`。
    """
    result: dict[str, str] = {}
    for error in exc.errors(include_url=False, include_context=False, include_input=False):
        loc = error['loc']
        field = loc[0] if loc else None
        error_type = error['type']
        if isinstance(field, str) and field in labels:
            key = field
            message = ERROR_TYPE_MESSAGES.get(error_type, DEFAULT_FIELD_MESSAGE).format(label=labels[field])
        else:
            key = GLOBAL_ERROR_KEY
            message = GLOBAL_ERROR_TYPE_MESSAGES.get(error_type, DEFAULT_GLOBAL_MESSAGE)
        result.setdefault(key, message)
    return result
