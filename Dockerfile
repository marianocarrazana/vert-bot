FROM python:3.9-slim

ADD traading.py /

RUN pip install pandas ta tinydb requests tornado python-binance finplot

CMD [ "python", "./server.py" ]
