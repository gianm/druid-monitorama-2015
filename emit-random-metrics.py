#!/usr/bin/env python2.7

import argparse
import json
import random
import subprocess
import time

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-n', metavar='count', type=int, default=1)
args = parser.parse_args()

# Open the kafka console producer
producer = subprocess.Popen(
  "./kafka_2.10-0.8.2.1/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic metrics",
  shell=True,
  stdin=subprocess.PIPE
)

# Generate random query metrics
for n in xrange(0, args.n):
  metric = {
    'timestamp': long(time.time() * 1000),
    'name': 'query/time',
    'host': '192.168.' + str(random.randrange(1, 254)) + '.' + str(random.randrange(1, 254)),
    'page': str(int(max(1, random.gauss(5, 4)))) + '.html',
    'value': max(0, int(random.gauss(200, 80)))
  }
  producer.stdin.write(json.dumps(metric))
  producer.stdin.write("\n")

# Close kafka console producer, wait for exit
producer.stdin.close()
producer.wait()

if producer.returncode != 0:
  raise Exception("Producer exited with code: " + str(producer.returncode))
