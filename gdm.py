"""
Support for discovery using GDM (Good Day Mate), multicast protocol by Plex.

# Licensed Apache 2.0
# From https://github.com/home-assistant/netdisco/netdisco/gdm.py

Inspired by:
  hippojay's plexGDM: https://github.com/hippojay/script.plexbmc.helper/resources/lib/plexgdm.py
  iBaa's PlexConnect: https://github.com/iBaa/PlexConnect/PlexAPI.py
"""
import socket
import struct
from http.server import BaseHTTPRequestHandler
from lxml import etree as ET

WIN_NL = chr(13) + chr(10)

application_name = "Python Test"
machine_identifier = "test123"
plex_product = "Plex for Kodi"
version = "0.0.1"
platform = "raspberry"
platform_version = "19.11111"
plex_protocol = "plex"
plex_protocol_version = "3"
plex_protocol_capabilities = "timeline,playback,navigation,mirror,playqueues"
device_class = "stb"


class GDM:
    """Base class to discover GDM services.

       Atrributes:
           entries (List<dict>): List of server and/or client data discovered.
    """

    def __init__(self):
        self.entries = []

    def scan(self, scan_for_clients=False):
        """Scan the network."""
        self.update(scan_for_clients)

    def all(self, scan_for_clients=False):
        """Return all found entries.

        Will scan for entries if not scanned recently.
        """
        self.scan(scan_for_clients)
        return list(self.entries)

    def find_by_content_type(self, value):
        """Return a list of entries that match the content_type."""
        self.scan()
        return [entry for entry in self.entries
                if value in entry['data']['Content-Type']]

    def find_by_data(self, values):
        """Return a list of entries that match the search parameters."""
        self.scan()
        return [entry for entry in self.entries
                if all(item in entry['data'].items()
                       for item in values.items())]

    def update(self, scan_for_clients):
        """Scan for new GDM services.

        Examples of the dict list assigned to self.entries by this function:

            Server:

                [{'data': {
                     'Content-Type': 'plex/media-server',
                     'Host': '53f4b5b6023d41182fe88a99b0e714ba.plex.direct',
                     'Name': 'myfirstplexserver',
                     'Port': '32400',
                     'Resource-Identifier': '646ab0aa8a01c543e94ba975f6fd6efadc36b7',
                     'Updated-At': '1585769946',
                     'Version': '1.18.8.2527-740d4c206',
                },
                 'from': ('10.10.10.100', 32414)}]

            Clients:

                [{'data': {'Content-Type': 'plex/media-player',
                     'Device-Class': 'stb',
                     'Name': 'plexamp',
                     'Port': '36000',
                     'Product': 'Plexamp',
                     'Protocol': 'plex',
                     'Protocol-Capabilities': 'timeline,playback,playqueues,playqueues-creation',
                     'Protocol-Version': '1',
                     'Resource-Identifier': 'b6e57a3f-e0f8-494f-8884-f4b58501467e',
                     'Version': '1.1.0',
                },
                 'from': ('10.10.10.101', 32412)}]
        """

        gdm_msg = 'M-SEARCH * HTTP/1.0'.encode('ascii')
        gdm_timeout = 1

        self.entries = []
        known_responses = []

        # setup socket for discovery -> multicast message
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(gdm_timeout)

        # Set the time-to-live for messages for local network
        sock.setsockopt(socket.IPPROTO_IP,
                        socket.IP_MULTICAST_TTL,
                        struct.pack("B", gdm_timeout))

        if scan_for_clients:
            # setup socket for broadcast to Plex clients
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            gdm_ip = '255.255.255.255'
            gdm_port = 32412
        else:
            # setup socket for multicast to Plex server(s)
            gdm_ip = '239.0.0.250'
            gdm_port = 32414

        try:
            # Send data to the multicast group
            sock.sendto(gdm_msg, (gdm_ip, gdm_port))

            # Look for responses from all recipients
            while True:
                try:
                    bdata, host = sock.recvfrom(1024)
                    data = bdata.decode('utf-8')
                    if '200 OK' in data.splitlines()[0]:
                        ddata = {k: v.strip() for (k, v) in (
                            line.split(':') for line in
                            data.splitlines() if ':' in line)}
                        identifier = ddata.get('Resource-Identifier')
                        if identifier and identifier in known_responses:
                            continue
                        known_responses.append(identifier)
                        self.entries.append({'data': ddata,
                                             'from': host})
                except socket.timeout:
                    break
        finally:
            sock.close()


class GDMAdvertiser:
    def createAnswerSocket(self):
        gdm_range = "0.0.0.0"
        gdm_port = 32412
        gdm_timeout = 10

        # setup socket for discovery -> multicast message
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(gdm_timeout)
        sock.bind((gdm_range, gdm_port))
        while True:
            data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
            print("received message from %s" % addr[0])
            response = self.getResponseString()
            sock.sendto(response.encode("utf-8"), addr)
            print("sent message to %s" % addr[0])

    def getResponseString(self) -> str:
        response_string: str = "HTTP/1.0 200 OK" + WIN_NL
        response_string = appendNameValue(response_string, "Name", application_name)
        response_string = appendNameValue(response_string, "Port", "32400")
        response_string = appendNameValue(response_string, "Product", plex_product)
        response_string = appendNameValue(response_string, "Content-Type", "plex/media-player")
        response_string = appendNameValue(response_string, "Protocol", plex_protocol)
        response_string = appendNameValue(response_string, "Protocol-Version", plex_protocol_version)
        response_string = appendNameValue(response_string, "Protocol-Capabilities", plex_protocol_capabilities)
        response_string = appendNameValue(response_string, "Version", version)
        response_string = appendNameValue(response_string, "Resource-Identifier", machine_identifier)
        response_string = appendNameValue(response_string, "Device-Class", device_class)
        return response_string


class GDMAdvertiserRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/xml")  # application/xml
        self.end_headers()

        response = self.getWebserverResponse()

        self.wfile.write(response)
        print("WebServer requested")

    def getWebserverResponse(self) -> bytes:
        data = ET.Element('MediaContainer', {"size": "1"})
        attributes: dict[str, str] = {
            "title": application_name,
            "machineIdentifier": machine_identifier,
            "product": plex_product,
            "version": version,
            "platform": platform,
            "platformVersion": platform_version,
            "protocolVersion": plex_protocol_version,
            "protocolCapabilities": plex_protocol_capabilities,
            "deviceClass": device_class
        }
        player = ET.SubElement(data, 'Player', attributes)
        return ET.tostring(data, xml_declaration=True)


def appendNameValue(buf, name, value) -> str:
    line = name + ": " + value + WIN_NL
    return buf + line


def main():
    """Test GDM discovery."""
    from pprint import pprint

    gdm = GDM()

    pprint("Scanning GDM for servers...")
    gdm.scan()
    pprint(gdm.entries)

    pprint("Scanning GDM for clients...")
    gdm.scan(scan_for_clients=True)
    pprint(gdm.entries)


if __name__ == "__main__":
    main()
