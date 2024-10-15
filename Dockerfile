# 
FROM python:3.12

# 
WORKDIR /code

# 
COPY ./requirements.txt /code/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY src/*.py /code/src/
COPY locales/*.json /code/locales/

# 
CMD ["python", "/code/src/main.py"]
