FROM ubuntu:24.04

ARG PYTHON_VERSION=3.12

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-dev \
        python${PYTHON_VERSION}-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python${PYTHON_VERSION} -m venv "${VENV_PATH}" \
    && "${VENV_PATH}"/bin/pip install --upgrade pip

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip check

COPY . .

# Make railway-start.sh executable
RUN chmod +x railway-start.sh

# Railway provides PORT env var, default to 8000 for local dev
ENV PORT=8000

CMD ["sh", "railway-start.sh"]
