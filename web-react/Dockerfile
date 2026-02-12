# Flask backend for Railway (use when service root directory is web-react)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=server.py
EXPOSE 8004

CMD ["python", "server.py"]
