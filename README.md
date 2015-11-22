Mixtur
======

Mixtur is a site for hosting playlists. Frontend uses HTML5 <audio> tag and 
flash to fall back on via the SoundManager2 library. Backend is Python via
Flask library and Sqlite3 for datastore. (sqlite3 is part of the standard library in Python 2.5 onward)

Install
---
* Required server software (for pillow image manipulation library) [source](https://pillow.readthedocs.org/en/3.0.0/installation.html#linux-installation)
```
$ sudo apt-get install libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk
```
* Initialize database
```
sqlite3 -init mixtur_schema.sql mixtur.db
```
* Add first user to database
	1. navigate to /pw/ and copy the generated password
	2. ```
	echo 'INSERT INTO user (name, email, password) VALUES("user_name", "john@me.com", "pbkdf2:sha1:XXXXXXXX");' | sqlite3 mixtur.db
	```

(Don't Forget!) Include following Environmental Variables
---
> export MIXTUR_SECRET_KEY=""
> export MIXTUR_UN=""
> export MIXTUR_PW=""


> Music listening, performance, and composition engage nearly every area 
> of the brain that we have so far identified, and involve nearly every neural subsystem.

~ Daniel J. Levitin from *This is Your Brain on Music*

License
----

MIT
