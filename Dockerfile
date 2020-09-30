# Use an official Python runtime as a parent image
FROM python:3.6-slim

ARG DEVICE_CONFIG_BACKUP_HOST_ADDRESS
ENV DEVICE_CONFIG_BACKUP_HOST_ADDRESS=${DEVICE_CONFIG_BACKUP_HOST_ADDRESS}
ARG DEVICE_CONFIG_BACKUP_DB_NAME
ENV DEVICE_CONFIG_BACKUP_DB_NAME=${DEVICE_CONFIG_BACKUP_DB_NAME}
ARG DEVICE_CONFIG_BACKUP_DB_PASSWORD
ENV DEVICE_CONFIG_BACKUP_DB_PASSWORD=${DEVICE_CONFIG_BACKUP_DB_PASSWORD}
ARG RMQ_HOST
ENV RMQ_HOST=${RMQ_HOST}
ARG POSTGRES_COMMANDER_RMQ_EXCHANGE
ENV POSTGRES_COMMANDER_RMQ_EXCHANGE=${POSTGRES_COMMANDER_RMQ_EXCHANGE}
ARG POSTGRES_COMMANDER_RMQ_QUEUE_IN
ENV POSTGRES_COMMANDER_RMQ_QUEUE_IN=${POSTGRES_COMMANDER_RMQ_QUEUE_IN}
ARG EASY_CROSSING_POST_ADDRESS
ENV EASY_CROSSING_POST_ADDRESS=${EASY_CROSSING_POST_ADDRESS}

RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y net-tools
RUN apt-get install -y telnet

RUN mkdir -p /app

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Run app.py when the container launches
CMD ["python", "rmq_postgres_commander.py"]