# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# Press the green button in the gutter to run the script.
import threading
from http.server import HTTPServer
from pprint import pprint

from plexapi.server import PlexServer

from plexapi.gdm import GDM

from gdm import GDMAdvertiser, GDMAdvertiserRequestHandler


def start_webserver():
    webServer = HTTPServer(('', 32400), GDMAdvertiserRequestHandler)
    webServer.serve_forever()


def start_gdm_answerer():
    gdm_advertiser.createAnswerSocket()


if __name__ == '__main__':
    # baseUrl = ""
    # token = ""
    # plex = PlexServer(baseUrl, token)

    #    gdm = GDM()
    #    gdm.scan(scan_for_clients=True)
    #    pprint(gdm.entries)

    #   gdm.scan(scan_for_clients=False)
    #   pprint(gdm.entries)

    gdm_advertiser = GDMAdvertiser()

    # set up /resources webcontext to confirm the readiness
    webserver_daemon = threading.Thread(name='web_daemon_server',
                                        target=start_webserver)
    webserver_daemon.setDaemon(True)  # Set as a daemon so it will be killed once the main thread is dead.
    webserver_daemon.start()

    # set up UDP server socket to wait for GDM discovery requests
    gdm_answerer_daemon = threading.Thread(name='socket_daemon_server',
                                           target=start_gdm_answerer())
    gdm_answerer_daemon.setDaemon(True)  # Set as a daemon so it will be killed once the main thread is dead.
    gdm_answerer_daemon.start()

