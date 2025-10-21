# Beaver TTP Service

Trusted Third Party для генерации троек Бивера в протоколах MPC.

## Быстрый старт

### Запуск
```bash
docker-compose up --build -d # в режиме демона
```

### Проверка
```bash
curl http://localhost:8090/api/health
```
#### Ошибка
curl: (7) Failed to connect to localhost port 8090 after 0 ms: В соединении отказано
#### Успех
{"redis":"connected","status":"healthy"}

### Остановка
```bash
docker-compose down --remove-orphans
```

## API

### POST /api/beaver/share
Получить долю тройки Бивера.

**Request:**
```json
{
    "session_id": "alice-bob-session",
    "party_id": 0,
    "triple_id": 42,
    "ring": "Z2^64"
}
```

**Response:**
```json
{
    "session_id": "alice-bob-session",
    "triple_id": 42,
    "party_id": 0,
    "share": {
        "a": "123456789",
        "b": "987654321",
        "c": "111111111"
    }
}
```

### GET /api/health
Health check endpoint.

### GET /api/stats
Статистика использования (без раскрытия данных).

## Тестирование

```bash
# Локально
python client.py

# Тесты
pytest test_beaver.py -v
```

## Безопасность

- Истинная случайность (CSPRNG)
- Детекция нарушения протокола (двойные запросы)
- Автоматическая очистка памяти (TTL 5 минут)
- Без логирования чувствительных данных

## Порты

- HTTP API: 8090
- Redis: 6380