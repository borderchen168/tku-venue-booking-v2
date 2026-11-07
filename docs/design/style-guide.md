# 介面設計規範（Style Guide）

- 對應 Task：T-002；適用：所有 `app/templates/`、`app/static/` 的開發（T-010、T-012、T-015、T-017、T-020 等）
- 實作檔：`app/static/css/main.css`、`app/templates/base.html`、`app/templates/macros/forms.html`、`app/templates/errors/`
- 依據：`docs/architecture/routes.md`（第 1、3、4、5 節）、`docs/architecture/overview.md`（第 5、8 節）、`docs/architecture/error-handling.md`、ADR-002 2.1、WCAG 2.2 AA
- 最後更新：2026-11-07（第 2 版：依 Code Review 修正；對齊 routes.md 第 4 版）

## 1. 設計原則

1. **不依賴 JavaScript**：Sprint 1 全部功能以 SSR(伺服器端渲染) ＋ HTML 表單完成；刪除確認等互動用獨立頁面。
2. **CSP(內容安全政策) 相容**：見第 12 節，違反即視為 Code Review blocking。
3. **無障礙優先**：WCAG 2.2 AA（涵蓋 T-002 完成條件要求的 WCAG 2.1 AA：2.2 AA 是 2.1 AA 的超集合，只刪除已過時的 4.1.1；對比度門檻兩版相同）；顏色只是輔助，狀態一律有文字。
4. **Mobile-first(行動優先)**：預設版面為手機單欄，寬螢幕再加欄。
5. **單一來源**：樣板變數、filter、表單欄位名稱以 routes.md 第 3、4 節為準（本文件第 11 節摘錄）；列舉中文標籤只用 filter 產生。

## 2. 色彩

所有色彩定義為 `main.css` 的 CSS custom property(自訂屬性)，樣板與其他 CSS 一律引用變數，不得自行寫色碼。

對比度以 WCAG 2.x 相對亮度公式計算，四捨五入至小數第二位。門檻：一般文字 ≥ 4.5:1、大字 ≥ 3:1、非文字元件（表單邊框、焦點框）≥ 3:1。

### 2.1 基本色

| 變數 | 色碼 | 用途 | 搭配背景 | 對比度 | 結果 |
|---|---|---|---|---|---|
| `--color-text` | `#1f2937` | 內文 | `#ffffff` | 14.68:1 | AA ✔（AAA ✔） |
| `--color-text` | `#1f2937` | 頁尾內文 | `#f3f4f6` | 13.34:1 | AA ✔ |
| `--color-text-muted` | `#4b5563` | 次要文字、說明 | `#ffffff` | 7.56:1 | AA ✔ |
| `--color-text-muted` | `#4b5563` | 頁尾 | `#f3f4f6` | 6.87:1 | AA ✔ |
| `--color-primary` | `#1d4ed8` | 連結、主要按鈕底色 | `#ffffff` | 6.70:1 | AA ✔ |
| 白字 | `#ffffff` | 主要按鈕文字 | `#1d4ed8` | 6.70:1 | AA ✔ |
| `--color-primary-hover` | `#1e40af` | 連結／按鈕 hover | `#ffffff` | 8.72:1 | AA ✔ |
| `--color-primary-hover` | `#1e40af` | 次要按鈕 hover 文字 | `#dbeafe` | 7.15:1 | AA ✔ |
| `--color-primary` | `#1d4ed8` | 連結出現在 `.notice`、`.flash--info` 內 | `#dbeafe` | 5.49:1 | AA ✔ |
| `--color-primary` | `#1d4ed8` | 連結出現在 `.flash--error` 內 | `#fee2e2` | 5.49:1 | AA ✔ |
| 白字 | `#ffffff` | 頁首文字、導覽列 | `--color-header-bg` `#1e3a8a` | 10.36:1 | AA ✔ |
| `--color-danger` | `#b91c1c` | 錯誤訊息文字、危險按鈕底色 | `#ffffff` | 6.47:1 | AA ✔ |
| 白字 | `#ffffff` | 危險按鈕 hover | `#7f1d1d` | 10.02:1 | AA ✔ |
| `--color-border` | `#6b7280` | 表單控制項邊框（非文字） | `#ffffff` | 4.83:1 | ≥ 3:1 ✔ |
| `--color-focus` | `#1d4ed8` | 焦點框（淺色背景） | `#ffffff` | 6.70:1 | ≥ 3:1 ✔ |
| `--color-focus-on-dark` | `#fbbf24` | 焦點框（深色頁首） | `#1e3a8a` | 6.20:1 | ≥ 3:1 ✔ |
| `--color-border-subtle` | `#d1d5db` | 純裝飾分隔線、卡片外框 | – | – | 不承載資訊，不適用 |

### 2.2 狀態標籤配色（`.badge--*`）

標籤文字欄只說明意義；實際文字一律由 filter 產生（見表後說明）。

| 列舉值 | 標籤文字來源 | class | 文字色 | 背景色 | 對比度 | 結果 |
|---|---|---|---|---|---|---|
| `DayStatus.BOOKABLE`（空閒時段） | `day_status_label` | `badge--bookable` | `#14532d` | `#dcfce7` | 8.30:1 | AA ✔ |
| `BookingStatus.PENDING` | `status_label` | `badge--pending` | `#78350f` | `#fef3c7` | 8.15:1 | AA ✔ |
| `BookingStatus.APPROVED` | `status_label` | `badge--approved` | `#1e3a8a` | `#dbeafe` | 8.49:1 | AA ✔ |
| `DayStatus.CLOSED` | `day_status_label` ＋ `reason_type_label` | `badge--closed` | `#7f1d1d` | `#fee2e2` | 8.20:1 | AA ✔ |
| `DayStatus.OUTSIDE_SEMESTER` | `day_status_label` | `badge--outside_semester` | `#374151` | `#e5e7eb` | 8.33:1 | AA ✔ |
| `DayStatus.DEADLINE_PASSED`（空閒時段） | `day_status_label` | `badge--deadline_passed` | `#4b5563` | `#f3f4f6` | 6.87:1 | AA ✔ |

- class 後綴**等於列舉的英文值**（`badge--{{ day.status }}`、`badge--{{ booking.status }}`），樣板不需要額外對照表。
- 標籤一律有文字與 1px `currentColor` 邊框；`deadline_passed` 另用虛線框（forced-colors 模式下亦同），與 `outside_semester` 在灰階下仍可區分。
- **中文標籤文字一律由 filter 產生**，樣板不得寫死任何標籤字串（overview.md 第 5 節）：
  - 申請狀態（佔用）：`status_label`（只接受 `BookingStatus`）。
  - 日狀態：`day_status_label`（只接受 `DayStatus`，由 T-017 註冊，routes.md 3.4）。
  - 不開放原因：`reason_type_label`，多個原因以「、」連接（`closed_reason_types` 已去重排序）。
- 寫法見第 8 節。

### 2.3 Flash 訊息配色（`.flash--*`）

`FlashMessage.level` 白名單 `success` / `info` / `warning` / `error`，沿用 2.2 的同色系組合（皆 ≥ 8.15:1；flash 內若有連結，`#1d4ed8` 在 `#dbeafe`／`#fee2e2` 上為 5.49:1，見 2.1），左側 6px 色條。`error` 以 `role="alert"`、其他以 `role="status"` 輸出；不在白名單的 level 一律以 `info` 呈現。

## 3. 字型與字級

- 字型堆疊：`system-ui, -apple-system, "Segoe UI", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", "Heiti TC", sans-serif`——只用作業系統已安裝的字型，**不載入外部或自架 web font**。
- 基準字級 `1rem`（使用者瀏覽器預設，通常 16px），行高 1.6；以 `rem` 為單位，支援 200% 放大（WCAG 1.4.4）。

| 變數 | 大小 | 用途 |
|---|---|---|
| `--text-2xl` | 1.75rem | `<h1>`（每頁恰好一個） |
| `--text-xl` | 1.375rem | `<h2>` |
| `--text-lg` | 1.125rem | `<h3>`、網站名稱、錯誤頁主訊息 |
| `--text-base` | 1rem | 內文、表單 |
| `--text-sm` | 0.875rem | 表格、標籤、說明文字、頁尾（最小字級，不得再小） |

- 時間欄位使用 `font-variant-numeric: tabular-nums`（週檢視時段欄已設定）。

## 4. 間距與版面

- 間距以 4px 為基準：`--space-1` 0.25rem、`--space-2` 0.5rem、`--space-3` 0.75rem、`--space-4` 1rem、`--space-5` 1.5rem、`--space-6` 2rem、`--space-7` 3rem。
- 內容寬度上限 `--container-max` 72rem，左右內距 `--space-4`。
- 斷點（mobile-first，`min-width`）：

| 名稱 | 寬度 | 變化 |
|---|---|---|
| 手機 | < 40rem（640px） | 單欄；`.actions` 內按鈕撐滿寬度；`.detail-list` 上下排列 |
| 平板 | ≥ 40rem | `.card-list` 2 欄；`.field-row` 2 欄；`.detail-list` 左右排列 |
| 桌機 | ≥ 64rem（1024px） | `.card-list` 3 欄；導覽列與網站名稱同一列 |

- 寬表格（週檢視、管理清單）一律包在 `.table-scroll` 中水平捲動，**不讓整頁產生水平捲軸**（WCAG 1.4.10 Reflow）。

## 5. 版面元件（class 一覽）

| class | 用途 |
|---|---|
| `.container` | 置中的內容容器 |
| `.page-header` | 頁面標題區（`<h1>` ＋ 說明） |
| `.breadcrumb` | 麵包屑；外層 `<nav aria-label="導覽路徑">`，內層 `<ol>`，目前頁面加 `aria-current="page"` |
| `.card`、`.card-list` | 卡片、卡片清單（`<ul class="card-list">`） |
| `.detail-list` | 名稱—值清單（`<dl>`），用於場地資訊、期間詳情、申請結果 |
| `.notice` | 重要提醒（例如 R-12、R-16、「您目前不是任何社團的負責人，無法申請」） |
| `.actions` | 一列按鈕／連結 |
| `.inline-form` | 行內表單（例如頁首登出） |
| `.data-table` | 資料表格；必有 `<th scope="col">`，列標題用 `<th scope="row">`；建議加 `<caption>` |
| `.table-scroll` | 表格捲動容器；**必須**加 `role="region"`、`aria-label="…"`、`tabindex="0"` |
| `.week-table` | 週檢視表格（搭配 `.data-table`），第一欄 sticky |
| `.week-nav` | 週檢視的上一週／下一週列 |
| `.visually-hidden` | 只給螢幕閱讀器的文字 |

## 6. 按鈕與連結

| 樣式 | class | 用途 |
|---|---|---|
| 主要 | `.button` | 每個表單的主要送出（「登入」「送出申請」「儲存」）；每頁最多一個主要按鈕 |
| 次要 | `.button .button--secondary` | 次要操作（「查看借用狀況」） |
| 危險 | `.button .button--danger` | 只用於刪除確認頁的「確認刪除」 |
| 深色頁首 | `.button .button--on-dark` | 頁首「登入」「登出」 |
| 一般連結 | `<a>` | 導覽、「取消」、表格中的「檢視／編輯／刪除」 |

- **會改變狀態的操作一律是 `<form method="post">` 內的 `<button type="submit">`**；GET 連結不得有副作用（routes.md 第 1 節）。
- **導向其他頁面一律是 `<a href>`**，可套用 `.button` 外觀，但不得用 `<button>` 做導覽。
- 觸控目標最小 2.75rem（44px）高（WCAG 2.5.8 要求 24px，此處採較嚴格的 44px）。
- 連結一律有底線；不得只以顏色區分連結。
- 所有 `href` 與 `action` 使用**站內相對路徑**（例如 `/venues`），不使用 `url_for`（會以 Host 標頭組出絕對網址，overview.md 第 5 節）。

## 7. 表單

### 7.1 強制規則

1. `<form>` 一律 `method="post"`（狀態變更）或 `method="get"`（查詢，例如週檢視的 `week_start`）。
2. **不得使用 `enctype="multipart/form-data"`**，也不要寫 `enctype` 屬性（預設即 `application/x-www-form-urlencoded`）。非 urlencoded 的 POST 會被 `FormContentTypeMiddleware` 以 415 擋下（routes.md 第 1 節、ADR-002 2.1）。
3. 每個 `method="post"` 的表單第一個子元素必須是 `{{ forms.csrf_field() }}`（輸出 `<input type="hidden" name="csrf_token" value="…">`）。Token 只經此隱藏欄位傳遞，不放 URL。
4. `action` 寫明確的站內相對路徑（例如 `action="/bookings"`）。
5. 單一表單欄位數 ≤ 50（`FORM_MAX_FIELDS`，含 `csrf_token`）。
6. 驗證失敗重新渲染時，保留已填值（密碼除外）；`form` 字典由 route 提供。
7. 不加 `novalidate`：保留瀏覽器原生 `required` 等提示作為第一層輔助；**伺服器端驗證才是依據**，所有錯誤都必須由 `errors` 呈現。

### 7.2 巨集（`macros/forms.html`）

每個使用表單的樣板都要自行匯入，且**必須 `with context`**（否則巨集讀不到 `csrf_token`、`form`、`errors`）：

```jinja
{% import 'macros/forms.html' as forms with context %}
```

| 巨集 | 說明 |
|---|---|
| `forms.csrf_field()` | CSRF 隱藏欄位；`csrf_token` 為 None 時輸出空值（伺服器端 403），不會渲染失敗 |
| `forms.hidden(name, value)` | 一般隱藏欄位（例如登入的 `forms.hidden('next', next_path)`） |
| `forms.form_errors(title='送出失敗，請修正以下問題', id='error-summary')` | 錯誤摘要：`errors['__all__']` 段落＋各欄位錯誤連結（`#field-<name>`），`role="alert"`；空字串訊息不列出。標題元素 id 為 `<id>-title`，同一頁出現兩次時請給不同 `id` |
| `forms.input(name, label, type='text', required=false, help=none, id=none, value=none, autocomplete=none, maxlength=none, minlength=none, min=none, max=none, step=none, inputmode=none, pattern=none, short=false)` | 單行輸入；`type` 白名單 `text`/`password`/`date`/`number`/`email`/`tel`/`search`；`password` 永不輸出 `value` |
| `forms.textarea(name, label, required=false, help=none, id=none, value=none, rows=5, maxlength=none, minlength=none)` | 多行文字 |
| `forms.select(name, label, options, required=false, help=none, id=none, value=none, placeholder='請選擇', short=false)` | 下拉選單；`options` 為 `(value, label)` 配對，以字串比對已選值 |
| `forms.submit(label, variant='primary')` | 送出按鈕；`variant`：`primary`/`secondary`/`danger` |

巨集輸出結構（以 `forms.input('activity_name', '活動名稱', required=true, maxlength=100)` 且有錯誤為例）：

```html
<div class="field field--error">
    <label class="field__label" for="field-activity_name">活動名稱<span class="field__required">（必填）</span></label>
    <p class="field__error" id="field-activity_name-error"><span class="visually-hidden">錯誤：</span>活動名稱不可空白</p>
    <input class="field__control" type="text" id="field-activity_name" name="activity_name" value="" required maxlength="100"
        aria-invalid="true" aria-describedby="field-activity_name-error">
</div>
```

- 欄位 `id` 預設 `field-<name>`；說明文字 id `<id>-help`、錯誤訊息 id `<id>-error`，以 `aria-describedby` 關聯（routes.md 第 3 節）。
- 錯誤訊息放在 label 與控制項之間，並以紅色粗體＋欄位左側紅線呈現（不只靠顏色）；錯誤欄位加 `aria-invalid="true"`。
- 必填以文字「（必填）」標示，不只用星號。
- 巨集只接受具名參數白名單，**不接受任意 HTML 屬性**，避免產生 `style=`、`on*=`。

### 7.3 範例

```jinja
{% extends 'base.html' %}
{% import 'macros/forms.html' as forms with context %}
{% block title %}新增不開放期間｜{{ super() }}{% endblock %}
{% block content %}
<h1>新增不開放期間</h1>
<form class="form" method="post" action="/admin/closed-periods">
    {{ forms.csrf_field() }}
    {{ forms.form_errors() }}
    <div class="field-row">
        {{ forms.input('start_date', '起日', type='date', required=true, short=true) }}
        {{ forms.input('end_date', '迄日', type='date', required=true, short=true, help='可與起日同一天') }}
    </div>
    {{ forms.select('reason_type', '原因類型', reason_options, required=true) }}
    {{ forms.input('description', '說明', required=true, maxlength=100) }}
    <div class="actions">
        {{ forms.submit('儲存') }}
        <a href="/admin/closed-periods">取消</a>
    </div>
</form>
{% endblock %}
```

`reason_options` 由 route 以列舉成員與 `reason_type_label` 準備，或在樣板中以 filter 組出；**不得**在樣板寫死 `('exam_week', '考試週')` 這類對照。

### 7.4 各表單欄位對照（routes.md 第 4 節，名稱不得更改）

| 表單 | `action` / `method` | 欄位 `name` 與屬性 |
|---|---|---|
| 共用 | – | `csrf_token`（`forms.csrf_field()`） |
| 登入 | `POST /login` | `username`（`autocomplete="username"`、`maxlength="50"`）、`password`（`type="password"`、`autocomplete="current-password"`、`maxlength="128"`）、`next`（**只能**以 `forms.hidden('next', next_path)` 輸出；`next_path` 為 route 已經 `is_safe_next()` 過濾的值，不合格為 `/`。樣板不得讀 `request.query_params['next']`，`next` 與 `next_path` **永遠不得**出現在 `<a href>`、`<form action>`、`<meta http-equiv="refresh">` 或任何 URL 屬性，routes.md 2.6） |
| 登出 | `POST /logout` | 只有 `csrf_token`（已內建於 `base.html` 頁首） |
| 不開放期間 | `POST /admin/closed-periods`、`POST /admin/closed-periods/{period_id}/edit` | `start_date`、`end_date`（`type="date"`）、`reason_type`（`<select>`：`national_holiday`/`exam_week`/`major_exam`/`other`）、`description`（`maxlength="100"`） |
| 刪除確認 | `POST /admin/closed-periods/{period_id}/delete` | 只有 `csrf_token` |
| 借用申請 | `POST /bookings` | `club_id`（select）、`venue_id`（select）、`date`（`type="date"`）、`start_time`、`end_time`（select，08:00～22:00 每 30 分）、`activity_name`（`maxlength="100"`）、`activity_description`（textarea，`maxlength="1000"`）、`expected_attendees`（`type="number"`、`min="1"`、`max="9999"`、`inputmode="numeric"`） |
| 週檢視查詢 | `GET /venues/{venue_id}/availability` | `week_start`（`type="date"`；GET 表單**不加** `csrf_field`）。**必須**傳 `value=week.week_start.isoformat()`：此頁沒有 `form` 字典，且 422 時頁面已改顯示本週，欄位應顯示實際呈現的週一，不回填無效輸入。例：`{{ forms.input('week_start', '選擇週', type='date', value=week.week_start.isoformat(), short=true) }}` |

### 7.5 錯誤呈現

| 錯誤 | 呈現 |
|---|---|
| 逐欄錯誤（`FieldErrors`、Pydantic） | 該欄位下方訊息＋頂部摘要連結 |
| 全域錯誤（`errors['__all__']`：商業規則 422、重疊 409、表單情境 503、登入失敗 400） | 頂部 `.error-summary` 段落 |
| 週檢視 `week_start` 無效（422） | 頁面頂部 `.error-summary`（同一巨集，鍵 `week_start` 或 `__all__`）。這是 GET 查詢錯誤，不是「送出失敗」，須傳合適標題，例如 `forms.form_errors(title='無法顯示所選的週')` |
| 非表單錯誤（403/404/422 路徑參數/500 等） | `errors/*.html` 統一錯誤頁 |

- 登入失敗只能放 `errors['__all__']`，不得標示在 `username` 或 `password` 欄位（不透露哪一個錯）。

### 7.6 樣板空白控制（`trim_blocks`、`lstrip_blocks`）

`app/core/templating.py` 的 Jinja2 環境開啟 `trim_blocks=True` 與 `lstrip_blocks=True`：獨佔一行的 `{% %}`（及 `{# #}`）標籤，連同其縮排與行尾換行會整行消失。因此：

- **預設不加 `-`**：控制標籤（`if`、`for`、`set`、`block`、`endblock`…）各自獨佔一行、不加 `-`，輸出時每個 HTML 標籤自成一行。加了 `-` 反而會吃掉**前一行**的換行，造成 `</li>                    <li>` 這類黏行。
- **只在下列情況使用 `-`**：
  1. `<!DOCTYPE html>` 之前（`base.html` 開頭的 `import`、`macro`、`set`）與 `extends` 子樣板中區塊之外的頂層標籤：確保文件開頭沒有空白。
  2. `{%- endmacro %}`：去掉巨集本體最後的換行，讓呼叫端那一行的換行決定斷行（不產生空行）。
  3. 同一個 HTML 標籤的多行屬性：`{%- if … %} attr="…"{% endif %}` 把屬性接回同一行。
  4. 行內片段（同一行內的 `{% if %}…{% endif %}`、單行的 `{% block title %}…{% endblock %}`）本來就不受影響，不需要 `-`。
- 子樣板的 `{% block content %}`、`{% endblock %}` 各自獨佔一行，內容最後保留換行，`</main>` 才會從新的一行開始。
- `{{ … -}}` 只用於 `_label_block` 這種「輸出固定以換行結尾」的內部 helper 之後。

## 8. 狀態與時間顯示

- 申請狀態（佔用）：

  ```jinja
  <span class="badge badge--{{ b.status }}">{{ b.status | status_label }}</span>
  ```

- 日狀態（含不開放原因）：

  ```jinja
  {%- set reasons = day.closed_reason_types | map('reason_type_label') | join('、') %}
  <span class="badge badge--{{ day.status }}">{{ day.status | day_status_label }}{% if day.status == 'closed' %}（{{ reasons }}）{% endif %}</span>
  ```

- 既有佔用在任何日狀態下都要顯示（routes.md 2.3、US-002 AC8），週檢視版面見 sprint-01-page-flow.md 3.5。
- 時間：`local_dt`（`YYYY-MM-DD HH:MM`）、`local_date`、`hhmm`、`weekday_label`（一～日）。日期可包在 `<time datetime="{{ d.isoformat() }}">` 中。
- 時段範圍以「–」（en dash）連接，例如 `18:00–20:00`；日期範圍以「～」連接。

## 9. 導覽列與 base layout（`base.html`）

- `<html lang="zh-Hant-TW">`；每頁以 `{% block title %}頁面名稱｜{{ super() }}{% endblock %}` 設定唯一標題。
- 結構：跳到主要內容連結 → `<header>`（網站名稱、`<nav aria-label="主要導覽">`、帳號區）→ `<main id="main">`（flash 區＋`{% block content %}`）→ `<footer>`。
- 導覽項目（依 `current_user`）：所有人「場地清單」；`is_student`「申請場地」（`/bookings/new`）；`is_staff`「不開放期間管理」（`/admin/closed-periods`）。Sprint 1 未實作的「我的申請」「待審核」**不顯示**。
- 登入者顯示 `display_name` 與「登出」按鈕（`POST /logout` ＋ `forms.csrf_field()`）；訪客顯示「登入」連結（`/login`）。
- 目前頁面：完全相符 `aria-current="page"`，子頁面 `aria-current="true"`。
- `current_user`、`csrf_token`、`messages`、`app_timezone`、`request` 任一未定義或為 None 時仍可渲染（500 頁），此時顯示訪客版。
- 子樣板只覆寫 `title` 與 `content` 兩個區塊。

## 10. 錯誤頁（`errors/`）

- 共用 `errors/_layout.html`：狀態小字、`<h1>`、主要訊息、建議、錯誤代碼、「回首頁」按鈕。
- 訊息文字**寫死在樣板**（error-handling.md 第 3 節），不輸出例外訊息、`reason`、請求路徑或任何使用者輸入。
- 錯誤代碼：優先使用 handler 傳入的 `request_id`，否則讀 `request.state.request_id`；都沒有則不顯示。提示文字不得依賴錯誤代碼一定存在。
- 錯誤頁不顯示也不消耗 flash：由 handler 設定 `request.state.skip_flash = True` 控制（routes.md 3.3），不得在 context 傳 `messages`。
- `errors/403.html` 以 `error_kind == 'csrf'` 切換為「表單已失效，請重新整理頁面後再試」，否則顯示「您沒有權限執行此操作」。
- 沒有 `415.html`：415、TrustedHost 400、`Content-Length` 400／413 由 middleware 回純文字（error-handling.md 3.2）。

## 11. 樣板 context 約定（摘錄 routes.md 第 3 節，以 routes.md 為唯一來源）

| 變數 | 型別 | 說明 |
|---|---|---|
| `request` | `Request` | 必填 |
| `current_user` | `CurrentUser \| None` | `id`、`username`、`display_name`、`role`、`is_staff`、`is_student` |
| `csrf_token` | `str \| None` | 以 `forms.csrf_field()` 輸出 |
| `messages` | `list[FlashMessage]` | `level`（`success`/`info`/`warning`/`error`）、`text`；由 `base.html` 統一顯示，頁面不需處理。`request.state.skip_flash` 為真時為空 list（3.3） |
| `app_timezone` | `str` | 頁尾顯示 |
| `form` | `dict[str, str]` | 表單頁已填值 |
| `errors` | `dict[str, str]` | 欄位名 → 訊息；全域錯誤鍵 `__all__` |
| `next_path` | `str` | 只用於 `auth/login.html`，已過濾的站內路徑，只能放在隱藏欄位 `next`（routes.md 2.6、3.2） |
| `request_id` | `str \| None` | 只用於 `errors/*.html`（routes.md 3.2） |
| `error_kind` | `Literal['csrf'] \| None` | 只用於 `errors/403.html`（routes.md 3.2） |

- **保留名稱**：`current_user`、`csrf_token`、`messages`、`app_timezone`、`request` 由 context processor／Starlette 提供，route 與 handler **不得**在 context 傳入同名鍵（會被覆寫而無效，routes.md 3.1）。

Jinja2 filter（routes.md 3.4）：`local_dt`、`local_date`、`hhmm`、`status_label`（只接受 `BookingStatus`）、`reason_type_label`、`category_label`、`weekday_label`、`day_status_label`（只接受 `DayStatus`，**由 T-017 註冊**）。Sprint 1 不提供 `role_label`（routes.md 3.5）。

## 12. CSP 與資安規則（overview.md 第 8 節、AGENTS.md 2.3）

| 禁止 | 替代做法 |
|---|---|
| inline `<script>`、`<script src>` 指向外站 | Sprint 1 不需要 JS；日後需要時放 `app/static/js/` 並經 Security Review |
| `<style>` 區塊、`style="…"` 屬性 | 在 `main.css` 新增 class |
| `onclick=` 等任何 `on*=` 屬性、`javascript:` URL | 用表單、連結或獨立確認頁 |
| `data:` URI（圖片、字型、背景） | 放實體檔於 `app/static/img/` |
| 外部 CDN、Google Fonts 等外部資源 | 只引用 `/static/` 下的檔案 |
| `|safe`、`Markup()` 輸出使用者輸入 | 依賴 autoescape；需要結構時用樣板標記組合 |
| `confirm()` 確認刪除 | GET 確認頁 ＋ POST 表單 |
| 在樣板寫死列舉中文對照（含「可申請」「不開放」等日狀態） | `status_label`、`day_status_label`、`reason_type_label`、`category_label` filter |
| `next`／`next_path` 放進 `<a href>`、`<form action>` 等 URL 屬性 | 只放在隱藏欄位 `next`（routes.md 2.6） |
| 在 `nav_link` 等產生 `href` 的巨集傳入使用者資料 | 只傳站內字面路徑（例如 `'/venues'`） |

其他：

- 使用者輸入（活動名稱、社團名稱、說明、帳號回填）只能放在文字節點或加雙引號的 `value` 屬性中；不得放進 `href`、`class`、`id` 或任何未加引號的位置。`class` 後綴只放白名單列舉值（第 2.2 節）。
- 公開頁面（借用狀況）只顯示 US-002 AC2 的欄位，不顯示申請人姓名等個資。

## 13. 無障礙檢查清單（每個新頁面 PR 自我檢查）

- [ ] `{% block title %}` 有唯一標題；頁面恰好一個 `<h1>`，標題層級不跳級。
- [ ] 所有表單欄位使用 `forms.*` 巨集（有 `<label for>`）；錯誤以 `aria-describedby` 關聯。
- [ ] 所有狀態以文字呈現，不只靠顏色；新顏色組合 ≥ 4.5:1 並補到第 2 節。
- [ ] 只用鍵盤可完成所有操作；焦點順序合理；焦點框可見（不得 `outline: none` 而無替代）。
- [ ] 表格有 `<th scope>`；捲動容器有 `role="region"`、`aria-label`、`tabindex="0"`。
- [ ] 重複出現的連結（「編輯」「申請此場地」）以 `.visually-hidden` 補上對象資訊。
- [ ] 400% 放大（320px 寬）時除表格外不出現水平捲軸。
- [ ] 沒有任何第 12 節禁止的寫法。

## 14. 設計決議紀錄（原待確認事項，已依 routes.md 第 4 版結案）

| # | 事項 | 結論 |
|---|---|---|
| 1 | 錯誤頁如何取得 `request_id` | **已定案，見 routes.md 3.2**：T-023 handler 明確傳入 `request_id`；樣板 fallback 讀 `request.state.request_id`，兩者皆無則不顯示（`errors/_layout.html` 已實作）。`request_id` 由伺服器隨機產生，不採用請求標頭 |
| 2 | 403 兩種訊息（權限／CSRF）如何區分 | **已定案，見 routes.md 3.2**：`csrf_error_handler` 傳 `error_kind='csrf'`；其他一律為權限訊息；訊息寫死於樣板 |
| 3 | `DayStatus` 標籤 filter | **已定案，見 routes.md 3.4**：新增 `day_status_label`（由 T-017 註冊）；`status_label` 不擴充 |
| 4 | 角色中文名稱 | **已定案，見 routes.md 3.5**：Sprint 1 不提供 `role_label`，導覽列只顯示 `display_name`（`base.html` 現行做法） |
| 5 | 錯誤頁不得消耗 flash、不得因 flash 再碰 DB | **已定案，見 routes.md 3.3**：T-023 的錯誤頁 handler 在渲染前設定 `request.state.skip_flash = True`；context processor（T-007）見旗標為真即回傳 `messages=[]` 且不呼叫 `pop_flashes()`。route／handler 在 context 傳 `messages=[]` **無效**（保留名稱，會被 processor 覆寫）。`base.html` 對 `messages` 為 None／未定義仍有防護 |
