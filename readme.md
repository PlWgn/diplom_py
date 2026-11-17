# Искра - знакомства и общение

Итоговый проект (диплом) по курсу «Backend Python».

Это REST API для сайта знакомств на Django REST Framework. Пользователь заполняет анкету, смотрит случайные анкеты с фильтрами и ставит лайк или дизлайк. При взаимной симпатии можно пригласить на свидание, обменяться контактами и переписываться.

## Что реализовано

- регистрация и вход по email, авторизация по JWT;
- анкета: ФИО, пол, возраст, город, увлечения, статус, фотогалерея с заглавной фотографией, количество лайков, настройки приватности;
- случайная анкета с фильтрами по полу, возрасту, городу, статусу и увлечению;
- лайки и дизлайки, списки понравившихся и непонравившихся, история лайков своей анкеты;
- история просмотренных анкет;
- приглашения на свидание и обмен контактами только при взаимной симпатии;
- чат на WebSocket;
- фотографии удаляются с диска вместе с записью в базе;
- валидаторы для возраста, имени, фотографий, приглашений и сообщений;
- оптимизированные запросы к базе (`select_related`, `prefetch_related`, индексы, пагинация);
- документация Swagger и открытый CORS;
- тесты (47 штук);
- запуск через `docker compose up` с PostgreSQL и Redis.

## Запуск

```bash
docker compose up --build
```

Документация API: http://localhost:8000/api/docs/

При запуске добавляются два демо-пользователя: `anna@demo.ru` и `ivan@demo.ru`, пароль `Demo12345!`. Анна уже лайкнула Ивана.

Тесты:

```bash
docker compose exec web python manage.py test
```

Без Docker проект работает с SQLite:

```bash
pip3 install -U -r requirements.txt
python3 manage.py migrate
python3 manage.py add_demo_users
python3 manage.py runserver
```

## Пример

Получить токен:

```bash
curl -X POST http://localhost:8000/api/auth/token/ -H 'Content-Type: application/json' -d '{"email": "ivan@demo.ru", "password": "Demo12345!"}'
```

Поставить лайк Анне (`<access>` - токен из ответа):

```bash
curl -X POST http://localhost:8000/api/reactions/ -H 'Authorization: Bearer <access>' -H 'Content-Type: application/json' -d '{"to_user": 1, "is_like": true}'
```

В ответе будет `"is_match": true`, потому что симпатия взаимная.
