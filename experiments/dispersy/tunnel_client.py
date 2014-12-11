#!/usr/bin/env python

from os import path, getpid
from random import choice, randint
from string import letters
from sys import path as pythonpath, stdout
from time import time, sleep

from twisted.python.threadable import isInIOThread
from twisted.internet.task import LoopingCall
from twisted.python.log import msg
from threading import Event, Thread

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

# TODO(emilon): Fix this crap
BASE_DIR = path.abspath(path.join(path.dirname(__file__), '..', '..', '..'))
pythonpath.append(path.abspath(path.join(BASE_DIR, "./tribler")))


class TunnelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.community import TunnelCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = TunnelCommunity

        self.monitor_circuits_lc = None
        self._prev_scenario_statistics = {}

    def start_tribler(self):
        from Tribler.Core.SessionConfig import SessionStartupConfig
        from Tribler.Core.Session import Session
        from Tribler.community.tunnel.community import TunnelSettings
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
        print 'Session created', isInIOThread()
        stdout.flush()
        upgrader = session.prestart()
        while not upgrader.is_done:
            sleep(0.1)
        session.start()

        self.set_community_kwarg('tribler_session', session)

        settings = TunnelSettings()
        settings.do_test = False

        self.set_community_kwarg('settings', settings)
        self.session = session

    def registerCallbacks(self):
        self.scenario_runner.register(self.build_circuits, 'build_circuits')

    def build_circuits(self):
        msg("build_circuits")
        self._community.circuits_needed[3] = 8

    def start_dispersy(self, autoload_discovery=True):
        msg("start dispersy")
        DispersyExperimentScriptClient.start_dispersy(self, autoload_discovery)
        self.start_tribler()

    def online(self):
        msg("online")
        self.session.lm.dispersy = self._dispersy
        cb = self.session.sessconfig.callback
        self.session.sessconfig.callback = None
        self.session.sessconfig.set(u'dispersy', u'dispersy_port', self._dispersy.endpoint._port)
        msg("dispersy on port %d" % (self._dispersy.endpoint._port))
        self.session.sessconfig.callback = cb
        self.session.set_anon_proxy_settings(2, ("127.0.0.1", self.session.get_tunnel_community_socks5_listen_ports()))
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
