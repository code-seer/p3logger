FROM python:2.7
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
COPY . .
WORKDIR .

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

EXPOSE 5000
