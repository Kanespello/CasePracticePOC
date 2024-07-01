nohup gunicorn -w 4 api:app --bind 0.0.0.0:9031 > ../error_logs/python_service.log 2>&1 &

