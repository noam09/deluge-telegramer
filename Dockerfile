FROM python:3.10-alpine3.15 AS base

RUN mkdir -p /usr/src/app
RUN mkdir -p /output
WORKDIR /usr/src/app

COPY telegramer /usr/src/app/telegramer
COPY setup.py /usr/src/app/setup.py
COPY LICENSE /usr/src/app/LICENSE

RUN python setup.py bdist_egg
