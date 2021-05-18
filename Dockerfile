FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install pandas ta tinydb requests tornado python-binance logging

CMD [ "python", "./server.py" ]
