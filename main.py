import os

print("Starting...")
os.system("gunicorn -c gunicorn.conf.py app:asgi_app")
