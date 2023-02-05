#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import signal
import sys

import flask
import flask_apscheduler

app = flask.Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)8.8s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

schedule = flask_apscheduler.APScheduler()


STATUS = "/var/log/openvpn-status.log" #location of open vpn status file
# STATUS = "openvpn-status.log"
daily_dir = "config/daily"
config_dir = "config"
dirs = [config_dir, daily_dir]


def byte2str(size):
    sizes = [
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'KB'),
        (1, 'B')
    ]
    for f, suf in sizes:
        if size >= f:
            break

    return "%.2f %s" % (size / float(f), suf)


def getScriptPath():  # gets script directory
    return os.path.dirname(os.path.realpath(sys.argv[0]))


def get_n_files(n):
    search_dir = os.path.join(getScriptPath(), daily_dir)
    files = [f for f in os.listdir(search_dir) if os.path.isfile(os.path.join(search_dir, f))]
    files = [os.path.join(search_dir, f) for f in files]  # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    files = files[0:n]
    logger.info("last %s files:%s", n, files)
    return files


def get_today_filename():
    today = datetime.date.today().strftime('%Y-%m-%d')
    today_filename = os.path.join(getScriptPath(), daily_dir, today + ".json")
    return today_filename


def read_stats_file(filename):
    # todo file not found - create
    day_data = None
    with open(filename, 'r') as f:
        try:
            day_data = json.load(f)
        except Exception:
            logger.warning("%s is not valid json, skipped", filename)
    logger.debug("Loaded from file:%s, content:%s", filename, day_data)
    return day_data


def write_stats_file(content):
    filename = get_today_filename()
    with open(filename, "w") as write_file:
        json.dump(content, write_file, indent=2)


def read_ovpn():
    status_file = open(STATUS, 'r')
    stats = status_file.readlines()
    status_file.close()

    print(stats)
    hosts = []
    headers = []

    headers = {
        'cn': 'Common Name',
        'virt': 'Virtual Address',
        'real': 'Real Address',
        'sent': 'Sent',
        'recv': 'Received',
        'since': 'Connected Since'
    }

    for line in stats:
        cols = line.split(',')

        if line.startswith('HEADER,CLIENT_LIST'):
            headers = cols[1:]
            print(headers)

        if line.startswith('CLIENT_LIST'):
            client = {}
            for i in range(len(headers)):
                print(i, " ", headers[i].rstrip(), " ", cols[i].rstrip())
            client['cn'] = cols[1]
            client['real'] = cols[2].split(':')[0]
            client['virtual'] = cols[3]
            client['recv'] = int(cols[5])
            client['sent'] = int(cols[6])
            client['since'] = int(cols[8].strip())
            client['sessions'] = 1
            hosts.append(client)

    return hosts


def merge_client_data(current_data, old_data):
    if current_data is None:
        return None
    if old_data is None:
        return current_data

    if current_data['since'] == old_data['since']:
        old_data['recv'] = current_data['recv']
        old_data['sent'] = current_data['sent']
    else:
        old_data['recv'] += current_data['recv']
        old_data['sent'] += current_data['sent']
        old_data['since'] = current_data['since']
        old_data['sessions'] += 1

    old_data['real'] = current_data['real']
    old_data['virtual'] = current_data['virtual']
    logger.debug("Merged client data:%s", old_data)
    return old_data


def read_old_data():
    today_filename = get_today_filename()
    if not os.path.isfile(today_filename):
        logger.warning("File is not found:%s", today_filename)
        return dict()
    else:
        old_data = read_stats_file(today_filename)
        if old_data is not None:
            old_dict = {x['cn']: x for x in old_data}
            logger.debug("Old data was read:%s", old_dict)
            return old_dict
        else:
            return dict()


def merge_data(current_data, old_dict):
    if len(current_data) < 1:
        logger.debug("Current data is empty, nothing to update")
        return
    for client in current_data:
        old_client = old_dict.get(client['cn'])
        merged_client = merge_client_data(client, old_client)
        if merged_client is not None:
            old_dict[client['cn']] = merged_client
    updated_data = list(old_dict.values())
    logger.info("Updated data: %s", updated_data)
    return updated_data


def check_dirs_exist():
    for dir in dirs:
        cur_dir = os.path.join(getScriptPath(), dir)
        if not os.path.isdir(cur_dir):
            os.mkdir(cur_dir)


@schedule.task("cron", minute="*")
def upd_stats():
    current_data = read_ovpn()
    old_data = read_old_data()
    merged = merge_data(current_data, old_data)
    write_stats_file(merged)


def get_stats():
    filenames = get_n_files(7)
    data_days = []
    for filename in filenames:
        clients_stats = read_stats_file(filename)
        if clients_stats is not None:
            data = {}
            data['date'] = os.path.basename(filename).replace('.json', '')
            data['stats'] = clients_stats
            data_days.append(data)
    logger.info(data_days)
    return data_days


def mod_data(data_days):
    for day in data_days:
        for stat in day['stats']:
            stat['since'] = datetime.datetime.fromtimestamp(stat['since'])
            stat['recv'] = byte2str(stat['recv'])
            stat['sent'] = byte2str(stat['sent'])
    return data_days


@app.route("/")
def home():
    data = get_stats()
    data = mod_data(data)
    return flask.render_template("stats.html", data=data)


@app.route("/e")
def er():
    os.kill(os.getpid(), signal.SIGINT)


if __name__ == '__main__':
    logger.info("Application starting, %s", __name__)
    check_dirs_exist()
    schedule.start()
    app.run(host="0.0.0.0", port=8075)
