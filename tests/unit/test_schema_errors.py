"""to_field_errors 測試（error-handling.md 第 2 節、Security Review N-10）。"""

import datetime as dt
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.schemas._errors import DEFAULT_GLOBAL_MESSAGE, ERROR_TYPE_MESSAGES, GLOBAL_ERROR_TYPE_MESSAGES, to_field_errors

SENSITIVE_INPUT = 'S3cret-Pass!-<script>'

LABELS = {
    'username': '帳號',
    'expected_attendees': '預計人數',
    'date': '日期',
    'start_time': '開始時間',
    'reason_type': '原因類型',
    'note': '備註',
}


class SampleForm(BaseModel):
    model_config = ConfigDict(extra='forbid')

    username: str = Field(min_length=3, max_length=10, pattern=r'^[a-z0-9]+$')
    expected_attendees: int = Field(ge=1, le=500)
    date: dt.date
    start_time: dt.time
    reason_type: Literal['national_holiday', 'exam_week', 'major_exam', 'other']
    note: str = ''

    @field_validator('note')
    @classmethod
    def _note_rule(cls, value: str) -> str:
        if value == SENSITIVE_INPUT:
            raise ValueError(f'不允許 {value}')
        return value


class RangeForm(BaseModel):
    start: int
    end: int

    @model_validator(mode='after')
    def _check(self) -> RangeForm:
        if self.end < self.start:
            raise PydanticCustomError('range_reversed', '結束 {end} 早於開始', {'end': self.end})
        return self


def errors_for(data: dict[str, object], labels: dict[str, str] = LABELS) -> dict[str, str]:
    with pytest.raises(ValidationError) as exc_info:
        SampleForm.model_validate(data)
    return to_field_errors(exc_info.value, labels)


VALID: dict[str, object] = {
    'username': 'abc',
    'expected_attendees': '10',
    'date': '2026-11-16',
    'start_time': '08:00',
    'reason_type': 'other',
}


def test_missing_fields() -> None:
    errors = errors_for({})
    assert errors['username'] == '帳號為必填欄位'
    assert errors['date'] == '日期為必填欄位'
    assert 'note' not in errors


@pytest.mark.parametrize(
    ('field', 'value', 'expected'),
    [
        ('username', 'ab', '帳號長度不足'),
        ('username', 'a' * 11, '帳號長度超過上限'),
        ('username', 'ABC', '帳號格式不正確'),
        ('expected_attendees', 'ten', '預計人數必須為整數'),
        ('expected_attendees', '0', '預計人數超出允許範圍'),
        ('expected_attendees', '501', '預計人數超出允許範圍'),
        ('date', '2026/11/16', '日期格式不正確'),
        ('start_time', '25:00', '開始時間格式不正確'),
        ('reason_type', 'holiday', '原因類型不是有效的選項'),
        ('note', SENSITIVE_INPUT, '備註內容不正確'),
    ],
)
def test_messages_by_type(field: str, value: object, expected: str) -> None:
    errors = errors_for({**VALID, field: value})
    assert errors == {field: expected}


def test_output_never_contains_input_or_ctx() -> None:
    data = {
        'username': SENSITIVE_INPUT,
        'expected_attendees': SENSITIVE_INPUT,
        'date': SENSITIVE_INPUT,
        'start_time': SENSITIVE_INPUT,
        'reason_type': SENSITIVE_INPUT,
        'note': SENSITIVE_INPUT,
    }
    errors = errors_for(data)
    text = repr(errors)
    assert SENSITIVE_INPUT not in text
    assert 'S3cret' not in text
    assert '<script>' not in text
    # ctx 值（長度上限、pattern）也不輸出
    assert '10' not in text
    assert '[a-z0-9]' not in text
    assert set(errors) == set(data)


def test_one_message_per_field() -> None:
    errors = errors_for({**VALID, 'username': 'A'})  # 同時違反長度與 pattern
    assert list(errors) == ['username']


def test_unknown_field_goes_to_global_without_echoing_name() -> None:
    errors = errors_for({**VALID, '<b>evil</b>': 'x'})
    assert errors == {'__all__': GLOBAL_ERROR_TYPE_MESSAGES['extra_forbidden']}
    assert 'evil' not in repr(errors)


def test_field_without_label_goes_to_global() -> None:
    labels = {k: v for k, v in LABELS.items() if k != 'note'}
    errors = errors_for({**VALID, 'note': SENSITIVE_INPUT}, labels)
    assert errors == {'__all__': DEFAULT_GLOBAL_MESSAGE}


def test_model_level_custom_error_is_global_and_hides_ctx() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RangeForm.model_validate({'start': 987654, 'end': 5})
    errors = to_field_errors(exc_info.value, {'start': '開始', 'end': '結束'})
    assert errors == {'__all__': DEFAULT_GLOBAL_MESSAGE}
    assert '987654' not in repr(errors)
    assert '5' not in repr(errors)


def test_registered_custom_type_message(monkeypatch: pytest.MonkeyPatch) -> None:
    class MinuteForm(BaseModel):
        minute: int

        @field_validator('minute')
        @classmethod
        def _half_hour(cls, value: int) -> int:
            if value not in (0, 30):
                raise PydanticCustomError('minute_not_half_hour', '分鐘 {value} 不合法', {'value': value})
            return value

    monkeypatch.setitem(ERROR_TYPE_MESSAGES, 'minute_not_half_hour', '{label}只能是整點或半點')
    with pytest.raises(ValidationError) as exc_info:
        MinuteForm.model_validate({'minute': 17})
    assert to_field_errors(exc_info.value, {'minute': '分鐘'}) == {'minute': '分鐘只能是整點或半點'}


def test_unregistered_custom_type_uses_default_message() -> None:
    class CodeForm(BaseModel):
        code: str

        @field_validator('code')
        @classmethod
        def _rule(cls, value: str) -> str:
            raise PydanticCustomError('some_new_rule', '值 {v} 錯誤', {'v': value})

    with pytest.raises(ValidationError) as exc_info:
        CodeForm.model_validate({'code': SENSITIVE_INPUT})
    errors = to_field_errors(exc_info.value, {'code': '代碼'})
    assert errors == {'code': '代碼格式不正確'}


class PeriodForm(BaseModel):
    start_date: dt.date
    end_date: dt.date

    @model_validator(mode='after')
    def _check_range(self) -> PeriodForm:
        if self.end_date < self.start_date:
            raise PydanticCustomError('end_before_start', 'end_date is before start_date')
        return self


def test_registered_global_type_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(GLOBAL_ERROR_TYPE_MESSAGES, 'end_before_start', '結束日期不可早於開始日期')
    with pytest.raises(ValidationError) as exc_info:
        PeriodForm.model_validate({'start_date': '2026-11-20', 'end_date': '2026-11-16'})
    errors = to_field_errors(exc_info.value, {'start_date': '開始日期', 'end_date': '結束日期'})
    assert errors == {'__all__': '結束日期不可早於開始日期'}
    assert '2026' not in repr(errors)


def test_unregistered_global_type_uses_default_message() -> None:
    assert 'end_before_start' not in GLOBAL_ERROR_TYPE_MESSAGES
    with pytest.raises(ValidationError) as exc_info:
        PeriodForm.model_validate({'start_date': '2026-11-20', 'end_date': '2026-11-16'})
    assert to_field_errors(exc_info.value, {'start_date': '開始日期'}) == {'__all__': DEFAULT_GLOBAL_MESSAGE}


def test_model_before_validator_custom_type_is_global(monkeypatch: pytest.MonkeyPatch) -> None:
    class MixedForm(BaseModel):
        name: str = Field(min_length=2)
        start: int
        end: int

        @model_validator(mode='before')
        @classmethod
        def _check(cls, data: object) -> object:
            raise PydanticCustomError('mixed_rule', 'mixed rule failed')

    monkeypatch.setitem(GLOBAL_ERROR_TYPE_MESSAGES, 'mixed_rule', '整體規則不符')
    with pytest.raises(ValidationError) as exc_info:
        MixedForm.model_validate({'name': 'a', 'start': 1, 'end': 2})
    assert to_field_errors(exc_info.value, {'name': '名稱'}) == {'__all__': '整體規則不符'}
