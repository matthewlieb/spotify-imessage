# Multi-stage Dockerfile for Railway: Builds React frontend + Flask backend
# This allows Railway to serve everything from one service

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app

# Copy package files
COPY package*.json ./
# Install ALL dependencies (including devDependencies needed for build)
RUN npm ci

# Copy source and build React app
COPY . .
RUN npm run build

# Verify build output
RUN test -d build && test -f build/index.html || (echo "React build failed!" && exit 1)

# Stage 2: Python backend with React build
FROM python:3.12-slim
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy React build from previous stage
COPY --from=frontend-builder /app/build ./build

# Copy Python application files
COPY server.py ./
# Copy all Python helper modules
COPY api_resilience.py error_handler.py security_config.py ./

# Environment variables (Railway sets PORT dynamically)
ENV FLASK_APP=server.py

# Expose port (Railway will set PORT env var at runtime)
EXPOSE 8004

# Start Flask server (which serves React build)
CMD ["python", "server.py"]
