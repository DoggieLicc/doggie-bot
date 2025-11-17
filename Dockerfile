FROM python:3.10.19-alpine

WORKDIR /app

RUN apk --no-interactive -U add git && apk cache clean

COPY requirements.txt /app

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "main.py"]
