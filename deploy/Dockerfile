FROM python:3.12-slim

WORKDIR /app
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .

# persistent data survives container restarts if this is mounted as a volume
VOLUME ["/app/data"]

EXPOSE 8765

CMD ["python", "main.py"]
