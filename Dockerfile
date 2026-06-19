FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

# Copy application
COPY . .

# Create static audio directory
RUN mkdir -p /app/static/audio

EXPOSE 8090

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8090"]
