#!/bin/bash
set -e

pip install -r requirements.txt
playwright install --with-deps chromium
python manage.py collectstatic --noinput