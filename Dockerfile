# Use latest Alpine Linux image as base
FROM alpine:latest

# Install supervise and python
RUN apk update && apk add --no-cache python3 py-pip

# Upgrade pip and install flask
RUN pip3 install --upgrade pip
RUN pip3 install flask flask_apscheduler

# Copy the ovpnstats directory into the container
COPY ovpnstats /ovpnstats

# Set the working directory to ovpnstats
WORKDIR /ovpnstats


RUN ls -l /
RUN ls -l /ovpnstats
# Start the container with supervise
CMD ls -l && ./ovpnstats.py
