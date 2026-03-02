FROM python:3.12-slim

# Instala Poetry
RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /app

# Copia manifesto e instala dependências de produção
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Copia código
COPY . .

# Usuário não-root
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
