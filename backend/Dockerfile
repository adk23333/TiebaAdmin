FROM python:3.11-bullseye

ENV TZ=Asia/Shanghai

WORKDIR /tieba

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "server.py"]
