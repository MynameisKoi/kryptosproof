# ─── Stage 1: Build the Next.js frontend ────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ─── Stage 2: Python backend + security tools + frontend runtime ────────
FROM python:3.12-slim

WORKDIR /app

# Node.js runtime (needed to run the Next.js standalone server)
COPY --from=node:20-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:20-slim /usr/local/include/node /usr/local/include/node
COPY --from=node:20-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip git \
    && rm -rf /var/lib/apt/lists/*

# Nuclei (ProjectDiscovery)
ARG NUCLEI_VERSION=3.3.5
RUN curl -fsSL -o /tmp/nuclei.zip \
    "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
    && unzip -q /tmp/nuclei.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/nuclei \
    && rm /tmp/nuclei.zip

# FFUF
ARG FFUF_VERSION=2.1.0
RUN curl -fsSL -o /tmp/ffuf.tgz \
    "https://github.com/ffuf/ffuf/releases/download/v${FFUF_VERSION}/ffuf_${FFUF_VERSION}_linux_amd64.tar.gz" \
    && tar -xzf /tmp/ffuf.tgz -C /usr/local/bin ffuf \
    && chmod +x /usr/local/bin/ffuf \
    && rm /tmp/ffuf.tgz

# sqlmap
RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /opt/sqlmap \
    && printf '%s\n' '#!/bin/sh' 'exec python3 /opt/sqlmap/sqlmap.py "$@"' > /usr/local/bin/sqlmap \
    && chmod +x /usr/local/bin/sqlmap

# Gitleaks
ARG GITLEAKS_VERSION=8.21.2
RUN curl -fsSL -o /tmp/gitleaks.tgz \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks \
    && rm /tmp/gitleaks.tgz

# Nuclei templates
RUN nuclei -update-templates -silent || true

# Python dependencies
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
    "uvicorn>=0.30.0"

# Copy Python source (explicit to avoid copying node_modules, .git, etc.)
COPY *.py ./
COPY ai/ ai/
COPY schemas/ schemas/
COPY tools/ tools/
COPY third_party/ third_party/
COPY wordlists/ wordlists/

# Copy Next.js standalone build + static assets
COPY --from=frontend /app/frontend/.next/standalone ./frontend/
COPY --from=frontend /app/frontend/.next/static ./frontend/.next/static

# Startup script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
