FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ .

# Copy frontend
COPY frontend/ /app/frontend/

# Seed database on build
RUN python -m app.db.seed

# Expose port
EXPOSE 10000

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
