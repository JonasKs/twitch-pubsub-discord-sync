FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip \
  && pip install poetry

RUN mkdir -p /source
WORKDIR /source
COPY . /source
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-dev

ENTRYPOINT ["python", "client.py"]