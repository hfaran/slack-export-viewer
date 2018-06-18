FROM tiangolo/uwsgi-nginx-flask:python2.7

COPY ./ ./

EXPOSE 5000

RUN pip install -r requirements.txt

CMD gunicorn --timeout 600 -c config.py wsgi
