#!/bin/sh
docker build . -t ovpnstats
docker-compose up
