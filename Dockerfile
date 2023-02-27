FROM python:3.9.16-alpine3.17

COPY . .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

CMD ["uvicorn", "fast_api_app:app", "--host", "0.0.0.0", "--port", "80"]


# docker build -t name_mash .
# docker run -d --name name_mash -p 127.0.0.1:20000:80 --restart unless-stopped name_mash