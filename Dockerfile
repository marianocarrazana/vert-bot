FROM python:3.9-slim

ADD traading.py /

RUN pip install pandas ta tinydb requests tornado

CMD [ "python", "./trading.py" ]
