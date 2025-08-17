FROM python:slim

WORKDIR /

COPY app app

RUN mkdir /var/log/app

RUN pip install --no-cache-dir --upgrade -r app/requirements.txt

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee -a /var/log/app/app.log"]
