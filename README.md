## Example .env
```
TOKEN=2021661289:AAGK0pddVJTF5ZZ5df1pAvVIF2MZmOrxl6U
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_NAME=postgres
DB_PORT=5432
```
## Start docker-compose
```
docker-compose up -d
docker-compose exec web alembic upgrade head
```