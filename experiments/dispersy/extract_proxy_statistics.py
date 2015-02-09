#!/usr/bin/env python
from extract_dispersy_statistics import *


class ProxyMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)
        self.packets_sent = defaultdict(lambda: 0)
        self.packets_lost = defaultdict(lambda: 0)
        self.latencies = defaultdict(list)
        self.download_speeds = defaultdict(list)

        self.send_received = defaultdict(lambda : {'received_encrypted':[]})

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key in ["latency-statistics", "speed-statistics"]

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        if key == 'latency-statistics':
            hops = int(json['hops'])
            self.packets_sent[hops] += json['packets_sent']
            self.packets_lost[hops] += json['packets_lost']
            self.latencies[hops].extend(json['latencies'])
        elif key == 'speed-statistics':
            hops = int(json['hops'])
            self.download_speeds[hops].append(json['avg_speed'])


    def all_files_done(self, extract_statistics):
        f = open(os.path.join(extract_statistics.node_directory, "_latency.txt"), 'w')
        f2 = open(os.path.join(extract_statistics.node_directory, "_latencies.txt"), 'w')

        print >> f, "hops", "packets_sent", "packets_lost", "average_latency"
        print >> f2, "hops", "latency"

        for hops in self.packets_sent:
            packets_sent = self.packets_sent[hops]
            packets_lost = self.packets_lost[hops]
            average_latency = 1.0 * sum(self.latencies[hops]) / len(self.latencies[hops])

            print >> f, hops, packets_sent, packets_lost, average_latency

            for latency in self.latencies[hops]:
                print >> f2, hops, latency

        f.close()
        f2.close()

        f = open(os.path.join(extract_statistics.node_directory, "_speeds.txt"), 'w')
        print >> f, "hops", "avg_speed"

        for hops in self.download_speeds:
            for speed in self.download_speeds[hops]:
                print >> f, hops, speed

        f.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <node-directory> <messagestoplot>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        sys.exit(1)

    e = get_parser(sys.argv)
    e.add_handler(ProxyMessages())
    e.parse()
