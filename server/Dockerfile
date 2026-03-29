FROM python:3.14 as build-env

ENV PYTHONUNBUFFERED=1

RUN mkdir /app
WORKDIR /app

# Add Pipfiles to image and install them
COPY . /app

# RUN apt-get update

RUN apt-get update && \
    apt-get install -y curl unzip && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

RUN apt-get install -y gdal-bin libgdal-dev

# Install Pipenv and run
RUN pip install pipenv --no-cache-dir
RUN pipenv install --system --skip-lock

# Add Django entrypoint script to docker
COPY ./scripts/entrypoint.sh /entrypoint.sh
RUN chmod u+x /entrypoint.sh

COPY ./scripts/wait-for-it.sh /wait-for-it.sh
RUN chmod u+x /wait-for-it.sh

ENTRYPOINT ["/entrypoint.sh"]
