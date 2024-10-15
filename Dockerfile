# 
FROM python:3.12

# 
WORKDIR /

# 
COPY ./requirements.txt /code/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY src/*.py /code/
COPY locales/*.json /locales/

# 
CMD ["python", "./code/main.py"]
