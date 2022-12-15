FROM python:3.10
COPY . /api
WORKDIR /api
ENV FLASK_APP app.py
ENV PYTHONUNBUFFERED 1
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN flask db init
RUN flask db migrate
RUN flask db upgrade
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "30000", "app:app"]