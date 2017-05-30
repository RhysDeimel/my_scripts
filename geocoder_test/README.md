## geocoder_test
> A quick script to get pygeocoder working

Takes the address stored in `address` and outputs the latitude and longitude.

```
$ python3 geocoder_test.py
(-33.8647516, 151.2068173)
```


## geocoder_requests
> Same thing, but using requests to access google API

```
$ python geocoder_requests.py
{'lng': 151.2068173, 'lat': -33.8647516}
```