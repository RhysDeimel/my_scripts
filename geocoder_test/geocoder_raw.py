# Making raw HTTP request to google API to get geocode data

import http.client
import json
from urllib.parse import quote_plus


base = '/maps/api/geocode/json'


def geocode(address):
    path = '{}?address={}'.format(base, quote_plus(address))
    connection = http.client.HTTPConnection('maps.google.com')
    connection.request('GET', path)
    raw_reply = connection.getresponse()
    reply = json.loads(raw_reply.read().decode())
    print(reply['results'][0]['geometry']['location'])


if __name__ == '__main__':
    geocode('60 Margaret St, Sydney NSW 2000')
