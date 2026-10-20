FROM node:20-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM python:3.11-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY --from=frontend-build /build/frontend/dist/ /app/frontend/dist/
ENV DEVSWEEP_HOSTED_DEMO=true \
    DEVSWEEP_DEMO_MODE=true \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    DEVSWEEP_DB_PATH=/data/devsweep.db \
    DEVSWEEP_DEMO_ROOT=/data/demo-workspaces
RUN mkdir -p /data/demo-workspaces
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request; port=os.environ.get('PORT',os.environ.get('BACKEND_PORT','8000')); urllib.request.urlopen('http://127.0.0.1:'+port+'/health', timeout=2)"]
CMD ["sh", "-c", "uvicorn main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-${BACKEND_PORT:-8000}} --proxy-headers"]
