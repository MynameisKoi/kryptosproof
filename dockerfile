FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip git \
    && rm -rf /var/lib/apt/lists/*

# Nuclei — red team scanner
ARG NUCLEI_VERSION=3.3.5
RUN curl -fsSL -o /tmp/nuclei.zip \
    "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
    && unzip -q /tmp/nuclei.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/nuclei \
    && rm /tmp/nuclei.zip

# FFUF — directory fuzzer
ARG FFUF_VERSION=2.1.0
RUN curl -fsSL -o /tmp/ffuf.tgz \
    "https://github.com/ffuf/ffuf/releases/download/v${FFUF_VERSION}/ffuf_${FFUF_VERSION}_linux_amd64.tar.gz" \
    && tar -xzf /tmp/ffuf.tgz -C /usr/local/bin ffuf \
    && chmod +x /usr/local/bin/ffuf \
    && rm /tmp/ffuf.tgz

# sqlmap — SQL injection scanner
RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /opt/sqlmap \
    && printf '%s\n' '#!/bin/sh' 'exec python3 /opt/sqlmap/sqlmap.py "$@"' > /usr/local/bin/sqlmap \
    && chmod +x /usr/local/bin/sqlmap

# Gitleaks — secret scanning for blue team
ARG GITLEAKS_VERSION=8.21.2
RUN curl -fsSL -o /tmp/gitleaks.tgz \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks \
    && rm /tmp/gitleaks.tgz

# Nuclei templates
RUN nuclei -update-templates -silent || true

# Install Python dependencies as a separate layer (cache-friendly)
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "pydantic-ai>=0.0.14" \
    "pydantic>=2.0" \
    "pydantic-settings>=2.0" \
    "anthropic>=0.40.0" \
    "httpx>=0.27.0" \
    "docker>=7.0.0" \
    "python-dotenv>=1.0.0" \
    "logfire>=4.29.0" \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0"

# Copy application source
COPY . .

# Cloud Run injects PORT at runtime; default to 8080
ENV PORT=8080
EXPOSE 8080

# NOTE: The Docker sandbox requires a Docker daemon reachable at DOCKER_HOST.
# On Cloud Run, set DOCKER_HOST=tcp://<your-docker-vm-ip>:2375 and
# SANDBOX_NETWORK to the network name on that remote daemon.
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT} --workers 1"]
