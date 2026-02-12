# Multi-stage Dockerfile for Railway: Builds React frontend + Flask backend
# Build context: Repo root (Railway uses repo root, so we copy from web-react/ subdirectory)

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app

# Copy package files from web-react
COPY web-react/package*.json ./
# Install ALL dependencies (including devDependencies needed for build)
RUN npm ci

# Copy source from web-react and build React app
COPY web-react/ ./
RUN npm run build

# Verify build output
RUN test -d build && test -f build/index.html || (echo "React build failed!" && exit 1)

# Stage 2: Python backend with React build
FROM python:3.12-slim
WORKDIR /app

# Copy Python requirements from web-react and install
COPY web-react/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy React build from previous stage
COPY --from=frontend-builder /app/build ./build

# Verify build was copied
RUN ls -la build/ && test -f build/index.html || (echo "ERROR: React build not copied correctly!" && exit 1)

# Copy Python application files from web-react
COPY web-react/server.py ./server.py
# Copy all Python helper modules from web-react
COPY web-react/api_resilience.py ./api_resilience.py
COPY web-react/error_handler.py ./error_handler.py
COPY web-react/security_config.py ./security_config.py

# Environment variables (Railway sets PORT dynamically)
ENV FLASK_APP=server.py

# Expose port (Railway will set PORT env var at runtime)
EXPOSE 8004

# Start Flask server (which serves React build)
CMD ["python", "server.py"]
