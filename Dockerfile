FROM python:3.10-alpine


WORKDIR /app

COPY bot/requirements.txt ./

RUN pip install -r requirements.txt

COPY bot /app

EXPOSE 5000

CMD ["python3", "-u", "main.py"]
