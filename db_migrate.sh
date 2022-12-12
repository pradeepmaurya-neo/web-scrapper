#!/usr/bin/env bash

echo "Waiting for MySQL..."


echo "MySQL started"

flask db init
flask db migrate
flask db upgrade

cd /api
gunicorn --bind 0.0.0.0:5000 --timeout 30000 app:app