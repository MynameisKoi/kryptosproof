FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip git \
    && rm -rf /var/lib/apt/lists/*

# Nuclei (ProjectDiscovery) — pinned release binary
ARG NUCLEI_VERSION=3.3.5
RUN curl -fsSL -o /tmp/nuclei.zip \
    "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
    && unzip -q /tmp/nuclei.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/nuclei \
    && rm /tmp/nuclei.zip

# FFUF — pinned release binary
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

# Gitleaks (secret scanning — blue team / CI)
ARG GITLEAKS_VERSION=8.21.2
RUN curl -fsSL -o /tmp/gitleaks.tgz \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks \
    && rm /tmp/gitleaks.tgz

# Nuclei templates (large download; required for meaningful results)
RUN nuclei -update-templates -silent || true

COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "pydantic-ai>=0.0.14" \
    "pydantic>=2.0" \
    "pydantic-settings>=2.0" \
    "anthropic>=0.40.0" \
    "httpx>=0.27.0" \
    "docker>=7.0.0" \
    "python-dotenv>=1.0.0"

COPY . .

CMD ["python", "main.py"]
