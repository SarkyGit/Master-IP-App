FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (for bcrypt, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gcc gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install Node dependencies
RUN npm install

# Build static assets
RUN npm run build:css

RUN chmod +x start.sh init_db.sh

CMD ["./start.sh"]
