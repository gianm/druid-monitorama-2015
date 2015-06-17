## About this repo

This repo is a companion to the Druid workshop at [Monitorama 2015](http://monitorama.com/). The slides for that talk are
here: https://speakerdeck.com/gianm/druid-at-monitorama-2015. Depending on when you're reading this, there may even be a video
uploaded at the Monitorama site!

You don't need to read the slides or watch the video to run through this tutorial, although
they may be interesting if you want to learn more about Druid. They go into a little background about Druid's origins, how it
works under the hood, and how people are using it in production.

## Druid as a metrics store

Druid's strength is in powering analytical, slice-and-dice workflows on massive volumes of event data. It's a great
metrics store for large deployments or for any deployment that will need to scale up, since Druid can scale right along
with your app. There are folks running clusters in production that ingest over a million events per second at peak [1].
Even at these high ingest rates, query performance can still be very good (sub-second for simple queries; seconds for
complex queries) and retention is limited only by the amount of storage in the cluster.

For more information about Druid, see http://druid.io/.

[1] For example, the cluster at Metamarkets: https://metamarkets.com/2015/dogfooding-with-druid-samza-and-kafka-metametrics-at-metamarkets/

## Setup

You'll need a few things running for this setup:

- [ZooKeeper](https://zookeeper.apache.org/), used by Kafka and Druid for coordination
- [MySQL](https://www.mysql.com/), used by Druid for metadata storage
- Either [S3](http://aws.amazon.com/s3/) or [HDFS](https://hadoop.apache.org/), used by Druid for data storage
- [Kafka](http://kafka.apache.org/), used for data ingestion
- [Grafana](http://grafana.org/), for visualizations
- [Druid](http://druid.io/), of course!

The following instructions will get you started with a single-machine deployment on a Mac. This should work pretty well
for trying things out, but in production, you'll want to run ZooKeeper, Kafka, and Druid distributed across more than
one machine. Generally ZooKeeper should run on 3 or 5 machines, and Kafka and Druid should run on as many machines as
needed for your data volume.

### MySQL and ZooKeeper

I'm running MySQL and ZooKeeper from Homebrew on my Mac. To get them going, you can run:

```
$ brew install mysql zookeeper
$ mysql.server start
$ zkServer start
$ mysql -uroot -e 'CREATE DATABASE druid; GRANT ALL PRIVILEGES ON druid.* TO druid IDENTIFIED BY "diurd";'
```

This will start up a MySQL server running on port 3306 and a ZooKeeper server running on port 2181.

### Kafka

Find an appropriate Kafka mirror at: https://www.apache.org/dyn/closer.cgi?path=/kafka/0.8.2.1/kafka_2.10-0.8.2.1.tgz

```
$ cd monitorama-druid-2015
$ curl -O $KAFKA_TARBALL_URL
$ tar xzf kafka_2.10-0.8.2.1.tgz
$ cd kafka_2.10-0.8.2.1
$ perl -pi -e's!^zookeeper.connect=.*!zookeeper.connect=localhost:2181/kafka!' config/server.properties
$ bin/kafka-server-start.sh config/server.properties
```

Then, in a separate console:

```
$ bin/kafka-topics.sh --create --zookeeper localhost:2181/kafka --replication-factor 1 --partitions 1 --topic metrics
```

This will start up a single Kafka broker running on port 9092, and create a topic called "metrics".

### Druid

```
$ cd monitorama-druid-2015
$ curl -O http://static.druid.io/artifacts/releases/druid-0.7.3-bin.tar.gz
$ tar xzf druid-0.7.3-bin.tar.gz
$ cd druid-0.7.3/
```

Start up a minimum viable Druid cluster: broker, coordinator, historical node, and realtime node. Do this by opening
four consoles and running one of these in each one:

```
# Broker
$ java -Xmx512m -Duser.timezone=UTC -Dfile.encoding=UTF-8 \
     -classpath "config/_common:config/broker:lib/*" \
     io.druid.cli.Main server broker
```

```
# Coordinator
$ java -Xmx512m -Duser.timezone=UTC -Dfile.encoding=UTF-8 \
     -classpath "config/_common:config/coordinator:lib/*" \
     io.druid.cli.Main server coordinator
```

```
# Historical node
$ java -Xmx512m -Duser.timezone=UTC -Dfile.encoding=UTF-8 \
     -classpath "config/_common:config/historical:lib/*" \
     io.druid.cli.Main server historical
```

```
# Realtime node
$ java -Xmx512m -Duser.timezone=UTC -Dfile.encoding=UTF-8 \
     -Ddruid.realtime.specFile=../configs/druid-metrics-ingest.json \
     -classpath "config/_common:config/realtime:lib/*" \
     io.druid.cli.Main server realtime
```

At this point, you should be able to see some information about your Druid cluster by going to the coordinator's
status page at [http://localhost:8081/#/](http://localhost:8081/#/).

### Grafana

Download version 1.9.1 of Grafana and untar it.

```
$ cd monitorama-druid-2015
$ curl -O http://grafanarel.s3.amazonaws.com/grafana-1.9.1.tar.gz
$ tar xzf grafana-1.9.1.tar.gz
$ cd grafana-1.9.1
```

#### Grafana Druid plugin

Clone the repo at https://github.com/Quantiply/grafana-plugins and install the plugin.

```
$ cd monitorama-druid-2015
$ git clone https://github.com/Quantiply/grafana-plugins.git
$ mkdir -p grafana-1.9.1/plugins/features
$ cp -a grafana-plugins/features/druid grafana-1.9.1/plugins/features
```

#### Grafana configuration

Go back into the grafana-1.9.1 directory, copy in the right configuration files, and start it up.

```
$ cd monitorama-druid-2015
$ cd grafana-1.9.1
$ cp ../configs/grafana-config.js config.js
$ cp ../configs/grafana-metrics-dashboard.json app/dashboards/metrics.json
```

#### Starting Grafana

Grafana needs a web server to start up. I decided to use nginx, since it's easy to install it with Homebrew. The
Homebrew version will launch any server in /usr/local/etc/nginx/servers/, so you can do this to get a server started:

```
$ cd monitorama-druid-2015
$ cp configs/nginx-grafana-server.conf /usr/local/etc/nginx/servers/grafana.conf # after updating the alias path
$ nginx
```

Now you should be able to go to http://localhost:3001/ and see a Grafana-Druid dashboard.

If you want to stop the server:

```
$ nginx -s quit
```

## Producing data

The moment we've been waiting for! Druid will load any JSON written to the "metrics" topic, as long as it has a
"timestamp" (expected to be ISO8601 or milliseconds since the epoch) and a "value" (just some number). To make it easy
to test things out, you can produce some random metrics by running:

```
$ cd monitorama-druid-2015
$ ./emit-random-metrics.py -n 250 # Or however many metrics you want to generate
```

## Screenshots

<img src="https://raw.githubusercontent.com/gianm/druid-monitorama-2015/master/druid-grafana.png" />
