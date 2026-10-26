FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=80 STORAGE=file DATA_FILE=/tmp/entries.json
EXPOSE 80
CMD ["python", "app.py"]
