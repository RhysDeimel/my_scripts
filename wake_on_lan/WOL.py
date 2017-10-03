# Wake on Lan (WOL) script. Usage example:
#
# python3 WOL.py XX:XX:XX:XX:XX:XX

import socket
from sys import argv


def WOL(mac_addr, port=9, network='<broadcast>'):
    """
    From Wikipedia:
    The magic packet is a broadcast frame containing anywhere within
    its payload 6 bytes of all 255 (FF FF FF FF FF FF in hexadecimal,
    followed by sixteen repetitions of the target computer's 48-bit
    MAC address, for a total of 102 bytes.

    Since the magic packet is only scanned for the string above, and
    not actually parsed by a full protocol stack, it may be sent as
    any network- and transport-layer protocol, although it is
    typically sent as a UDP datagram to port 0, 7 or 9, or directly
    over Ethernet as EtherType 0x0842.
    """

    if len(mac_addr) != 17:
        raise ValueError('Incorrect MAC address format ',
                         '(use XX:XX:XX:XX:XX:XX).')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    mac_addr_packet = mac_addr.replace(':', ' ')
    mac_addr_packet = bytearray.fromhex(mac_addr_packet) * 16

    magic_packet = bytearray.fromhex('FF FF FF FF FF')
    magic_packet += mac_addr_packet

    sock.sendto(magic_packet, (network, port))
    print('Magic packet sent!')


if __name__ == '__main__':
    WOL(argv[1])
