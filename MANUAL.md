# Руководство по интеграции с сервисом Beaver TTP

Этот документ описывает, как внешним клиентам взаимодействовать с сервисом для генерации троек Бивера.

## 1. Основные параметры

- **URL сервиса**: `http://84.252.132.132:8090`
- **Конечная точка (Endpoint)**: `/api/beaver/share`
- **Метод**: `POST`

## 2. Формат запроса

Для получения доли тройки Бивера необходимо отправить POST-запрос со следующей JSON-структурой:

```json
{
    "session_id": "уникальный_идентификатор_сессии",
    "party_id": 0,
    "triple_id": 123,
    "ring": "Z2^64"
}
```

### Описание полей запроса:

- `session_id` (string): Уникальный идентификатор для сессии вычислений. Должен быть одинаковым для обеих сторон (party 0 и party 1), запрашивающих одну и ту же тройку.
- `party_id` (integer): Идентификатор стороны. Может быть `0` или `1`.
- `triple_id` (integer): Уникальный идентификатор тройки внутри одной `session_id`. Должен быть одинаковым для обеих сторон.
- `ring` (string): Математическое поле, в котором генерируется тройка. Возможные значения:
    - `"Z2^64"`: Поле целых чисел по модулю 2^64.
    - `"Z2"`: Бинарное поле (числа 0 или 1).

## 3. Формат ответа

В случае успешного запроса сервис вернет JSON-объект со статусом `200 OK` и следующей структурой:

```json
{
    "session_id": "уникальный_идентификатор_сессии",
    "triple_id": 123,
    "party_id": 0,
    "share": {
        "a": "12345...",
        "b": "67890...",
        "c": "54321..."
    }
}
```

### Описание полей ответа:

- `share`: Объект, содержащий доли `(a, b, c)` тройки Бивера. Все значения возвращаются в виде строк.

## 4. Пример на Python

Вот простой пример использования сервиса с помощью библиотеки `requests` в Python.

```python
import requests
import uuid

# --- Параметры ---
TTP_URL = "http://84.252.132.132:8090/api/beaver/share"
SESSION_ID = f"client-test-{uuid.uuid4()}"
TRIPLE_ID = 0

# --- Сторона 0 (Party 0) ---
try:
    print("Party 0 запрашивает долю...")
    response_p0 = requests.post(
        TTP_URL,
        json={
            "session_id": SESSION_ID,
            "party_id": 0,
            "triple_id": TRIPLE_ID,
            "ring": "Z2^64"
        },
        timeout=5
    )
    response_p0.raise_for_status()  # Проверка на ошибки HTTP
    share0 = response_p0.json()["share"]
    print(f"Доля для Party 0 получена: a0={share0['a']}, b0={share0['b']}, c0={share0['c']}")

except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе для Party 0: {e}")


# --- Сторона 1 (Party 1) ---
try:
    print("\nParty 1 запрашивает долю...")
    response_p1 = requests.post(
        TTP_URL,
        json={
            "session_id": SESSION_ID,
            "party_id": 1,
            "triple_id": TRIPLE_ID,
            "ring": "Z2^64"
        },
        timeout=5
    )
    response_p1.raise_for_status()
    share1 = response_p1.json()["share"]
    print(f"Доля для Party 1 получена: a1={share1['a']}, b1={share1['b']}, c1={share1['c']}")

except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе для Party 1: {e}")
```

## 5. Обработка ошибок

- **400 Bad Request**: Неверный или отсутствующий параметр в запросе.
- **403 Forbidden**: Попытка повторного запроса. Каждая сторона может запросить свою долю только один раз для конкретной `(session_id, triple_id)`.
- **500 Internal Server Error**: Внутренняя ошибка сервера.