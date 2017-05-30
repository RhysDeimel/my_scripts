from pygeocoder import Geocoder


address = '60 Margaret St, Sydney NSW 2000'

if __name__ == '__main__':
    print(Geocoder.geocode(address)[0].coordinates)
