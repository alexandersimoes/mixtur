Mixtur
======

Mixtur is a site for hosting playlists. Frontend uses HTML5 <audio> tag and 
flash to fall back on via the SoundManager2 library. Backend is Python via
Flask library and Sqlite3 for datastore.

Install
---
* Initialize database
```
sqlite3 -init mixtur_schema.sql mixtur.db
```
* Add first user to database
	1. navigate to /pw/ and copy the generated password
	2. ```
	echo 'INSERT INTO user (name, email, password) VALUES("user_name", "john@me.com", "pbkdf2:sha1:XXXXXXXX");' | sqlite3 mixtur.db
	```

> Music listening, performance, and composition engage nearly every area 
> of the brain that we have so far identified, and involve nearly every neural subsystem.

Daniel J. Levitin from *This is Your Brain on Music*

License
----

MIT
