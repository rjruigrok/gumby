#!/usr/bin/env python

from threading import RLock
from twisted.internet import reactor

USE_CRYPTO = True

import time

from gumby.experiments.dispersyclient import main, DispersyExperimentScriptClient
from twisted.python.log import msg



class ProxyClient(DispersyExperimentScriptClient):
    @property
    def proxy(self):
        """ :rtype : Tribler.community.anontunnel.community.ProxyCommunity """
        return self._community

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.tunnel_community import TunnelCommunity
        msg("Init TunnelCommunity")

        self.community_class = TunnelCommunity

        self.stats_lock = RLock()
        self.circuit_length = None
        self.broken_circuits = 0
        self.num_stats = 0

        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        from Tribler.community.tunnel.crypto.tunnelcrypto import NoTunnelCrypto, TunnelCrypto
        self.proxy_settings = TunnelSettings()
        self.proxy_settings.crypto = TunnelCrypto() if USE_CRYPTO else NoTunnelCrypto()

        self.socks5_server = None
        self.stats_dict = {}
        self.download = None
        self.stats_crawler = None
        ''' :type : Tribler.community.anontunnel.stats.StatsCrawler '''
        self.exit_strategy = None

    def __stats_counter(self):
        def __stats_getter():
            self.num_stats = self.stats_crawler.get_num_stats()
            self.session.lm.rawserver.add_task(__stats_getter, 5.0)

        # self.session.lm.rawserver.add_task(__stats_getter, 5.0)

    def init_experiment(self, circuit_length):
        msg("Initializing experiment with {0} hops".format(circuit_length))

        circuit_length = int(circuit_length)

        # Only create circuits of length 'circuit_length'
        self.proxy_settings.circuit_length = circuit_length
        self.circuit_length = circuit_length
        self.proxy_settings.max_circuits = 0
        self.community_args = (False, self.proxy_settings, self.session.lm.rawserver)

        stats = dict(self.stats_dict)
        stats['speed'] = 0.0
        stats['broken_circuits_'] = self.broken_circuits
        self.stats_dict = self.print_on_change("scenario-statistics", self.stats_dict, stats)

    def online(self, dont_empty=False):
        super(ProxyClient, self).online(dont_empty)
        msg("ProxyClient has added observer to the ProxyCommunity")
        self.proxy.observers.append(self)

        # self.stats_crawler = StatsCrawler(self.session.lm.dispersy, self.session.lm.rawserver)
        # self.proxy.observers.append(self.stats_crawler)
        self.__stats_counter()


    def on_break_circuit(self, circuit):
        """:type circuit : Circuit"""

        if len(circuit.hops) == circuit.goal_hops:
            self.broken_circuits += 1

        stats = dict(self.stats_dict)
        stats['broken_circuits_'] = self.broken_circuits
        stats['num_stats_'] = self.num_stats

        self.print_on_change("scenario-statistics", self.stats_dict, stats)
        self.stats_dict = stats

    def start_download(self):
        msg("Got start-download trigger from scenario")

        from Tribler.Core.TorrentDef import TorrentDef
        from Tribler.Main.globals import DefaultDownloadStartupConfig
        from Tribler.community.tunnel.stats import StatsCollector
        from Tribler.Core.simpledefs import DLSTATUS_DOWNLOADING, DOWNLOAD, \
            DLSTATUS_SEEDING

        self.annotate("start-download-{0}hop".format(self.circuit_length))

        stats_collector = StatsCollector(self.proxy, "gumby")

        def _callback(ds):
            """
            @type ds : Tribler.Core.DownloadState.DownloadState
            @return:
            """

            msg("Download callback says: {}, {}, {} %".format(ds.get_status(), ds.get_error(), ds.get_progress() * 100.0))
            msg("Got %d circuits" % len(self.proxy.active_circuits))
            bytes_downloaded = ds.get_progress() * ds.get_length()

            # self.broken_circuits = self.broken_circuits + 1

            if ds.get_status() == DLSTATUS_DOWNLOADING:
                if not _callback.download_started_at:
                    _callback.download_started_at = time.time()
                    stats_collector.start()

                speed_download = ds.get_current_speed(DOWNLOAD)
                stats = dict(self.stats_dict)
                stats['speed'] = speed_download
                stats['broken_circuits_'] = self.broken_circuits
                stats['num_stats_'] = self.num_stats
                self.print_on_change("scenario-statistics", self.stats_dict, stats)
                self.stats_dict = stats

                stats_collector.download_stats = {
                    'size': bytes_downloaded,
                    'download_time': time.time() - _callback.download_started_at
                }

            elif not _callback.download_completed and ds.get_status() == DLSTATUS_SEEDING:
                _callback.download_finished_at = time.time()
                _callback.download_completed = True
                download_time = _callback.download_finished_at - _callback.download_started_at
                stats_collector.download_stats = {
                    'size': bytes_downloaded,
                    'download_time': download_time
                }

                stats = dict(self.stats_dict)
                stats['speed'] = 0
                stats['broken_circuits_'] = self.broken_circuits

                self.print_on_change("scenario-statistics", self.stats_dict, stats)
                self.stats_dict = stats

                stats_collector.share_stats()
                stats_collector.stop()
                self.annotate("end-download-{0}hop".format(self.circuit_length))

                self.print_on_change("speed-statistics", {}, {
                    'hops': self.circuit_length,
                    'avg_speed': float(bytes_downloaded) / download_time
                })
                return 0.0, False
            else:
                _callback.peer_added = False

            return 1.0, False

        _callback.download_started_at = None
        _callback.peer_added = True
        _callback.download_completed = None

        folder = os.path.dirname(os.path.realpath(__file__))
        tdef = TorrentDef.load(folder + "/250mb.bin.torrent")
        ''' :type : TorrentDef '''

        defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
        dscfg = defaultDLConfig.copy()
        ''' :type : DefaultDownloadStartupConfig '''

        dscfg.set_dest_dir(os.getcwd() + '/50M')
        msg("Start download to " + dscfg.get_dest_dir())

        dscfg.set_anon_mode(True)

        def add_download():
            download = self.session.start_download(tdef, dscfg)
            msg("Downloading infohash {")

            ''' :type : LibtorrentDownloadImpl '''

            download.set_state_callback(_callback, delay=1)

            hosts = [(os.environ['SYNC_HOST'], int(os.environ['SEEDER_PORT']))]

            for peer in hosts:
                download.add_peer(peer)

            self.download = download

        reactor.callInThread(add_download)

    def build_circuits(self, num):
        num = int(num)
        self.annotate("Building circuits")
        msg("Building %d circuits" % num)

        from Tribler.community.tunnel.Socks5.server import Socks5Server

        socks5_port = self.session.get_proxy_community_socks5_listen_port()
        self.socks5_server = Socks5Server(
            self.proxy,
            self.session.lm.rawserver,
            socks5_port=socks5_port,
            num_circuits=num,
            min_circuits=num,
            min_session_circuits=num
        )

        self.socks5_server.start()

        self.session.set_anon_proxy_settings(2, ("127.0.0.1", socks5_port))
        msg("Socks5 server started at %d, configured libtorrent" % socks5_port)


    def registerCallbacks(self):
        self.scenario_runner.register(self.start_download, 'start_download')
        self.scenario_runner.register(self.build_circuits, 'build_circuits')
        self.scenario_runner.register(self.init_experiment, 'init_experiment')

if __name__ == '__main__':
    import os
    scenario = os.environ['PROXY_SCENARIO'] if 'PROXY_SCENARIO' in os.environ else 'proxy.scenario'
    ProxyClient.scenario_file = scenario
    main(ProxyClient)