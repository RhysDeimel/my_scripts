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


## geocoder_raw
> Using raw HTTP to achieve the same results

```
$ python geocoder_raw.py
{'lat': -33.8647516, 'lng': 151.2068173}
```


## geocoder_network
> Raw network conversation with google API

```
$ python geocoder_network.py
HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Date: Tue, 30 May 2017 06:31:29 GMT
Expires: Wed, 31 May 2017 06:31:29 GMT
Cache-Control: public, max-age=86400
Access-Control-Allow-Origin: *
Server: mafe
X-XSS-Protection: 1; mode=block
X-Frame-Options: SAMEORIGIN
Accept-Ranges: none
Vary: Accept-Language,Accept-Encoding
Connection: close

{
   "results" : [
      {
         "address_components" : [

         ...
         
         ],      
         "formatted_address" : "60 Margaret St, Sydney NSW 2000, Australia",
         "geometry" : {
            "location" : {
               "lat" : -33.8647516,
               "lng" : 151.2068173
            },
            "location_type" : "ROOFTOP",
            "viewport" : {
               "northeast" : {
                  "lat" : -33.8634026197085,
                  "lng" : 151.2081662802915
               },
               "southwest" : {
                  "lat" : -33.8661005802915,
                  "lng" : 151.2054683197085
               }
            }
         },
         "place_id" : "ChIJ9xWYD0GuEmsRXfgjVqN8NFw",
         "types" : [ "street_address" ]
      }
   ],
   "status" : "OK"
}
```
