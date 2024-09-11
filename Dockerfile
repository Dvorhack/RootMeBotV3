FROM python:3.10-alpine


WORKDIR /app

COPY bot /app

RUN pip install -r requirements.txt
EXPOSE 5000

CMD ["python3", "bot.py"]