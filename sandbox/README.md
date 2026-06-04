uvicorn app.main:app --host 0.0.0.0 --port 9999 --reload

docker-compose -f .devops/docker-compose.yml up -d --build

docker-compose -f .devops/docker-compose.yml build --no-cache && docker-compose -f .devops/docker-compose.yml up -d

/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
