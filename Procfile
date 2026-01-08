web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 300 --worker-class gthread --workers 1 --threads 4
release: python manage.py migrate --noinput
