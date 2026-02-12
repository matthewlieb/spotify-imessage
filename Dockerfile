# Railway: Flask backend in web-react (bypasses Nixpacks so we control build)
FROM python:3.12-slim

WORKDIR /app

# Install only what we need for web-react backend
COPY web-react/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY web-react/ ./

# Env vars (secrets) are set by Railway; don't bake them into the image
ENV FLASK_APP=server.py
EXPOSE 8004

CMD ["python", "server.py"]
