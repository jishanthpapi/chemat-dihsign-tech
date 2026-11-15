FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY data ./data
RUN pip install --no-cache-dir . && useradd --create-home chemat && mkdir /app/storage && chown chemat /app/storage
USER chemat
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "chemat.api:app", "--host", "0.0.0.0", "--port", "8000"]
