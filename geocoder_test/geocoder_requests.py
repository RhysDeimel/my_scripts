# using requests as a comparison to pygeocode

import requests


def geocode(address):
    parameters = {'address': address}
    base = 'https://maps.googleapis.com/maps/api/geocode/json'
    response = requests.get(base, params=parameters)
    answer = response.json()
    print(answer['results'][0]['geometry']['location'])


if __name__ == '__main__':
    geocode('60 Margaret St, Sydney NSW 2000')
