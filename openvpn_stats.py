#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, pickle

# STATUS = "/var/log/openvpn-status.log" #location of open vpn status file
STATUS = "openvpn-status.log"
db_folder = "db"  # folder for storing data


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


def read_stats():
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
            host = {}
            for i in range(len(headers)):
                print(i, " ", headers[i].rstrip(), " " , cols[i].rstrip())
            host['cn']    = cols[1]
            host['real']  = cols[2].split(':')[0]
            host['virtual']  = cols[3]
            host['recv']  = int(cols[5])
            host['sent']  = int(cols[6])
            host['since'] = int(cols[8].strip())
            hosts.append(host)

    # if  line.startswith('CLIENT_LIST'):
    # 	host  = {}
    # 	host['cn']    = cols[0]
    # 	host['real']  = cols[1].split(':')[0]
    # 	host['recv']  = int(cols[2])
    # 	host['sent']  = int(cols[3])
    # 	host['since'] = cols[4].strip()
    # 	hosts.append(host)
    #
    # if len(cols) == 4 and not line.startswith('Virtual Address'):
    # 	for h in hosts:
    # 		if h['cn'] == cols[1]:
    # 			h['virt'] = cols[0]

    fmt = "%(cn)-25s %(virt)-18s %(real)-15s %(sent)13s %(recv)13s %(since)25s"
    print(hosts)
    return hosts


def getScriptPath():  # gets script directory
    return os.path.dirname(os.path.realpath(sys.argv[0]))


def update_log(cn, vhost):
    dhosts = []
    fn = os.path.join(getScriptPath(), db_folder, cn) + ".log"
    if os.path.exists(fn):
        old_host = pickle.load(open(fn, "rb"))  # read data from file
        print("old_host: ", old_host)
        if old_host[1]['since'] == vhost['since']:
            dhosts.append(old_host[0])
            dhosts.append(vhost)
        else:
            old_host[0]['recv'] += old_host[1]['recv']
            old_host[0]['sent'] += old_host[1]['sent']
            old_host[0]['since'] = old_host[1]['since']
            old_host[0]['real'] = old_host[1]['real']
            dhosts.append(old_host[0])
            dhosts.append(vhost)

        pickle.dump(dhosts, open(fn, "wb"))  # save data to file
    else:
        dhosts.append(vhost)
        dhosts.append(vhost)
        pickle.dump(dhosts, open(fn, "wb"))

    return


if __name__ == '__main__':
    hosts = read_stats()
    for h in hosts:
        update_log(h['cn'],h)
