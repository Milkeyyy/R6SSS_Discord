# 
FROM python:3.12-slim-bookworm

# 
WORKDIR /code

# 
RUN apt-get update \
&& apt-get install -y --no-install-recommends git \
&& apt-get purge -y --auto-remove \
&& rm -rf /var/lib/apt/lists/*

# 
COPY ./requirements.txt /code/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY src/*.py /code/src/
COPY src/cogs/commands/*.py /code/src/cogs/commands/
COPY src/cogs/tasks/*.py /code/src/cogs/tasks/
COPY locales/*.json /code/locales/
COPY pyproject.toml /code/

# 
CMD ["python", "/code/src/main.py"]
