FROM python:3.7-alpine

RUN apk update && apk add build-base gcc make python3-dev libc-dev libffi-dev musl-dev postgresql-dev py3-pip bash

WORKDIR /app

COPY conf/ conf/
COPY Makefile .
COPY main.py .

ENTRYPOINT ["make", "run", "source_code=/source/code", "source_requirements=/source/requirements.txt"]
