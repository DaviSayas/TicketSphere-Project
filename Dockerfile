## Stage 1 — Build Vite frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

## Stage 2 — Python runtime
FROM python:3.12-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ .

# Copy Vite build output into frontend/ (what main.py expects)
COPY --from=frontend-build /frontend/dist/ /app/frontend/

# Seed database on build
RUN python -m app.db.seed

# Expose port
EXPOSE 10000

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
