# Career Quest API

Установка, единый запуск, доступ, AI и демонстрация описаны в [корневом README](../README.md). Из корня: `npm run setup:demo`, затем `npm run dev`. Отдельный backend: `npm run dev:backend`.

## Контракт

| Метод / маршрут | Назначение |
|---|---|
| GET /api/health | Без сессии: готовность датасета, число сотрудников, dataset_as_of, openai_enabled |
| POST /api/auth/login | username/password; заголовок X-Requested-With: CareerQuest; создаёт HttpOnly cookie |
| GET /api/auth/me | username, role, employee_id, csrf_token |
| POST /api/auth/logout | Отзывает сессию |
| GET /api/employees?search=&limit=30&offset=0 | HR: employees, total, limit, offset; сортировка по ID |
| GET /api/employees/{id} | Владелец/HR: цель, навыки, gaps, progress, история до даты снимка |
| POST /api/employees/{id}/recommendations | Владелец/HR: до трёх шагов, evidence, метаданные и reason_code |
| POST /api/employees/{id}/complete | Владелец/HR: event_id; фактические updated_skills, progress_before/after |
| GET /api/hr/summary | HR: пробелы, участие, счётчики; без AI |
| GET /api/hr/employees-without-next-step?limit=20&offset=0 | HR: сотрудники, цели, reason/reason_code, total |
| POST /api/import | HR: JSON или multipart employees/history (alias activity_history) |
| POST /api/reset | HR: сброс импорта/симуляций, аккаунты сохраняются |

Все защищённые POST требуют сессионный cookie и `X-CSRF-Token` из login/me. CORS только для разрешённых origin. Интерактивные схемы: /docs; авторизуйтесь через frontend на том же origin либо передавайте cookie/CSRF явно.

`Idempotency-Key` для complete: до 128 символов; повтор такого же запроса возвращает сохранённый ответ без начисления. Повторное использование ключа для другого события даёт 409. Отдельное новое прохождение повторяемого события получает новый ключ. Без ключа неповторяемые события всё равно защищены от двойного начисления. Устаревший прогноз не гарантируется, если состояние изменилось между подбором и выполнением.

Пример основания рекомендации:

```json
{"id":"history","factor":"participation_history","text":"Same type or format: 0 completed, 3 missed, 0 declined, 0 dropped, 0 in progress, 0 overdue."}
```

Категории: current_grade, target_requirements, skill_gaps, participation_history. Цифры и reasons формируются backend, OpenAI не переписывает их. `explanation_source` — deterministic или openai.

Пример результата импорта:

```json
{"success":true,"employees_added":3,"history_rows_added":3,"warnings":[],"imported_employee_ids":["E9001","E9002","E9003"]}
```

Ошибка валидации: HTTP 422, `detail={code:"invalid_import",message,file,row,field}`; неизвестные file/row/field могут быть null. Для JSON сотрудников row — номер записи от 1; CSV — физическая строка от 2 после заголовка.

## Проверка API из PowerShell

После настройки аккаунтов (пароль вводится локально, не вставляйте его в документы):

```powershell
$credentials = Get-Credential -UserName hr -Message "Local Career Quest account"
$body = @{username=$credentials.UserName;password=$credentials.GetNetworkCredential().Password} | ConvertTo-Json
$login = Invoke-RestMethod http://127.0.0.1:8000/api/auth/login -Method Post -ContentType application/json -Headers @{"X-Requested-With"="CareerQuest"} -Body $body -SessionVariable cqSession
$headers = @{"X-CSRF-Token"=$login.csrf_token}
$steps = Invoke-RestMethod http://127.0.0.1:8000/api/employees/E0002/recommendations -Method Post -WebSession $cqSession -Headers $headers
$steps.recommendations | Select-Object event_id,title,explanation_source
```

Не фиксируйте заранее event_id для выполнения: выбирайте его из текущего ответа. POST complete — именно изменение демо-данных. Ключи, сессии и пароли не выводите в логи.

## Внутреннее устройство

- data_loader: неизменяемый набор и его проверка.
- progress: единая формула навыков и готовности.
- recommendation/engine и scoring: допустимость, пять факторов, стабильный порядок.
- recommendation/explainer: OpenAI structured plan → проверка ID/факторов → фактический текст; таймаут/fallback.
- runtime_state: SQLite, снимок для чтения, транзакционный импорт/выполнение/reset; один backend-процесс.
- auth: PBKDF2, серверные сессии и CSRF.
- services/hr: агрегаты/список без вызова LLM.
- services/import_service: атомарная валидация JSON/CSV.

`npm run test:backend` запускает изолированные тесты. `npm run check:openai` — отдельная проверка настоящего провайдера; она не включена в обычные тесты.
