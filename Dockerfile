# "Building" the venv
FROM dhi.io/python:3.10-alpine3.22-dev AS build-stage

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

RUN apk --no-interactive -U add git whois && apk cache clean

COPY requirements.txt /app

RUN python -m venv /app/venv

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM dhi.io/python:3.10-alpine3.22 AS runtime-stage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

COPY --from=build-stage /usr/lib/libunistring* /usr/lib/
COPY --from=build-stage /usr/lib/libidn2* /usr/lib/
COPY --from=build-stage /usr/bin/whois /usr/bin/
COPY --from=build-stage /etc/whois.conf /etc/whois.conf

COPY --from=build-stage /app/venv ./venv

COPY . /app

CMD ["python", "main.py"]
