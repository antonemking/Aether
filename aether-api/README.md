# Aether API

Backend API for Aether RAG Observability Platform.

## Setup

```bash
# Install dependencies
poetry install

# Copy environment variables
cp .env.example .env
# Edit .env with your actual credentials

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint
poetry run ruff check .

# Type check
poetry run mypy app
```

## Deployment

Deploy to Railway:
1. Connect GitHub repository
2. Add environment variables
3. Railway will auto-detect and deploy
