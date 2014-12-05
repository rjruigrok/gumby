#!/usr/bin/env python

from os import path, getpid
from random import choice, randint
from string import letters
from sys import path as pythonpath
from time import time, sleep

from twisted.internet.task import LoopingCall
from twisted.python.log import msg

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

# TODO(emilon): Fix this crap
BASE_DIR = path.abspath(path.join(path.dirname(__file__), '..', '..', '..'))
pythonpath.append(path.abspath(path.join(BASE_DIR, "./tribler")))


class TunnelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.community import TunnelCommunity, TunnelSettings
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = TunnelCommunity

        self.session = self.start_tribler()
        self.session.set_anon_proxy_settings(2, ("127.0.0.1", self.session.get_tunnel_community_socks5_listen_ports()))
        self.set_community_kwarg('session', self.session)

        self.monitor_circuits_lc = None
        self._prev_scenario_statistics = {}

    def start_tribler(self):
        from Tribler.Core.SessionConfig import SessionStartupConfig
        from Tribler.Core.Session import Session
        config = SessionStartupConfig()
        config.set_install_dir(path.abspath(path.join(BASE_DIR, "./tribler")))
        config.set_state_dir(path.abspath(path.join(BASE_DIR, ".Tribler-%d") % getpid()))
        config.set_torrent_checking(False)
        config.set_multicast_local_peer_discovery(False)
        config.set_megacache(False)
        config.set_dispersy(False)
        config.set_mainline_dht(True)
        config.set_torrent_collecting(False)
        config.set_libtorrent(True)
        config.set_dht_torrent_collecting(False)
        config.set_videoplayer(False)
        session = Session(config)
        upgrader = session.prestart(u":memory:")
        while not upgrader.is_done:
            sleep(0.1)
        session.start()
        return session

    def registerCallbacks(self):
        self.scenario_runner.register(self.build_circuits, 'build_circuits')

    def build_circuits(self):
        msg("build_circuits")
        self._community.circuits_needed[3] = 8

    def start_dispersy(self, autoload_discovery=True):
        DispersyExperimentScriptClient.start_dispersy(self, autoload_discovery)
        self.session.lm.dispersy = self._dispersy
        self.session.set_dispersy_port(self._dispersy.endpoint._port)

    def online(self):
        DispersyExperimentScriptClient.online(self)
        if not self.monitor_circuits_lc:
            self.monitor_circuits_lc = lc = LoopingCall(self.monitor_circuits)
            lc.start(5.0, now=True)

    def offline(self):
        DispersyExperimentScriptClient.offline(self)
        if self.monitor_circuits_lc:
            self.monitor_circuits_lc.stop()
            self.monitor_circuits_lc = None

    def monitor_circuits(self):
        nr_circuits = len(self._community.active_data_circuits()) if self._community else 0
        self._prev_scenario_statistics = self.print_on_change("scenario-statistics", self._prev_scenario_statistics,
                                                              {'nr_circuits': nr_circuits})


if __name__ == '__main__':
    TunnelClient.scenario_file = 'tunnel.scenario'
    main(TunnelClient)
