FROM python:3.6.13

WORKDIR /usr/src/YTAPI
COPY requirements.txt ./
ADD . /usr/src/YTAPI/
RUN pip install -r requirements.txt   