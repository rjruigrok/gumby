#!/usr/bin/env python

from os import path
from sys import path as pythonpath, stdout
from time import sleep

from twisted.internet.task import LoopingCall

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main
from twisted.python.threadable import isInIOThread
from posix import getpid


# TODO(emilon): Fix this crap
BASE_DIR = path.abspath(path.join(path.dirname(__file__), '..', '..', '..'))
#pythonpath.append(path.abspath(path.join(BASE_DIR, "./tribler")))

#BASE_DIR = path.abspath(path.join(path.dirname(path.realpath(__file__))))
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))


class TunnelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = HiddenTunnelCommunity

        tunnel_settings = TunnelSettings()
        #tunnel_settings.max_circuits = 0
        import random
        tunnel_settings.socks_listen_ports = [random.randint(1000, 65535) for _ in range(5)]

        self.set_community_kwarg('settings', tunnel_settings)
        self.set_community_kwarg('tribler_session', None)

        self.monitor_circuits_lc = None
        self._prev_scenario_statistics = {}
        
        
    def start_tribler(self):
        from Tribler.Core.SessionConfig import SessionStartupConfig
        from Tribler.Core.Session import Session
        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        self.config = SessionStartupConfig()
        self.config.set_install_dir(path.abspath(path.join(BASE_DIR, "tribler")))
        self.config.set_state_dir(path.abspath(path.join(BASE_DIR, "output", ".Tribler-%d") % getpid()))
        self.config.set_torrent_checking(False)
        self.config.set_multicast_local_peer_discovery(False)
        self.config.set_megacache(False)
        self.config.set_dispersy(False)
        self.config.set_mainline_dht(True)
        self.config.set_torrent_collecting(False)
        self.config.set_libtorrent(True)
        self.config.set_dht_torrent_collecting(False)
        self.config.set_videoplayer(False)
        session = Session(self.config)
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

    def start_dispersy(self, autoload_discovery=True):
        DispersyExperimentScriptClient.start_dispersy(self, autoload_discovery = autoload_discovery, use_new_crypto = True)
        self.start_tribler()
    
    def registerCallbacks(self):
        self.scenario_runner.register(self.setup_seeder, 'setup_seeder')
        self.scenario_runner.register(self.build_circuits, 'build_circuits')
        self.scenario_runner.register(self.create_torrent, 'create_torrent')
        self.scenario_runner.register(self.start_download, 'start_download')
        

    def build_circuits(self, num):
        self.annotate("build-circuits")
        self._community.circuits_needed[3] = int(num)

    def online(self):
        self.session.lm.dispersy = self._dispersy
        cb = self.session.sessconfig.callback
        self.session.sessconfig.callback = None
        self.session.sessconfig.set(u'dispersy', u'dispersy_port', self._dispersy.endpoint._port)
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

    def create_torrent(self):
        from Tribler.Core.TorrentDef import TorrentDef
        
        self.testtorrent = TorrentDef()
        self.testtorrent.add_content(path.join(BASE_DIR, "tribler", "Tribler", "Test", "data", "video.avi"))
        self.testtorrent.set_tracker("http://fake.net/announce")
        self.testtorrent.set_private()  # disable dht
        self.testtorrent.finalize()
        self.testtorrentfilename = path.join(self.session.get_state_dir(), "testtorrent.torrent")
        self.testtorrent.save(self.testtorrentfilename)
        
    def setup_seeder(self):
        self.annotate("setup-seeder")
        from Tribler.Core.DownloadConfig import DownloadStartupConfig
        dscfg = DownloadStartupConfig()
        dscfg.set_dest_dir(path.join(BASE_DIR, "tribler", "Tribler", "Test", "data", "video.avi"))  # basedir of the file we are seeding
        self.session.start_download(self.testtorrent, dscfg)

    def start_download(self):
        self.annotate("start-download")
        from Tribler.Main.globals import DefaultDownloadStartupConfig
        
        defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
        dscfg = defaultDLConfig.copy()
        dscfg.set_hops(2)
        dscfg.set_dest_dir(path.join(BASE_DIR, "output", str(getpid()), str(self.session.get_dispersy_port()), "video.avi"))  

        def start_download():
            def cb(ds):
                print 'Download', self.testtorrent.get_infohash().encode('hex')[:10], '@', ds.get_current_speed('down'), ds.get_progress(), ds.get_status(), sum(ds.get_num_seeds_peers())
                return 1.0, False
            download = self.session.start_download(self.testtorrent, dscfg)
            download.set_state_callback(cb, delay=1)

        self.session.uch.perform_usercallback(start_download)

    def monitor_circuits(self):
        nr_circuits = len(self._community.active_data_circuits()) if self._community else 0
        self._prev_scenario_statistics = self.print_on_change("scenario-statistics", 
                                                              self._prev_scenario_statistics,
                                                              {'nr_circuits': nr_circuits})


if __name__ == '__main__':
    TunnelClient.scenario_file = 'tunnel.scenario'
    main(TunnelClient)
