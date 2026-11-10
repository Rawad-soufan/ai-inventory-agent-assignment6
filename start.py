import os
import django
from django.core.management import call_command
from waitress import serve

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
call_command("migrate", interactive=False)
from config.wsgi import application
serve(application, host="0.0.0.0", port=8000)
