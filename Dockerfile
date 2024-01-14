FROM python:3.12

COPY . /code
WORKDIR /code

RUN python -m venv venv
RUN source venv/bin/activate
RUN pip install -e .

ENV PYTHONPATH=/code/src
WORKDIR /code/src/DHCPStaticMapper

CMD python ./src/main.py
