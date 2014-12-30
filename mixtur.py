# -*- coding: utf-8 -*-

'''All the imports'''
import sqlite3, os
from flask import Flask, g, render_template, send_from_directory, abort
from urllib import quote_plus, unquote_plus
from datetime import datetime

'''Create the application'''
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'mixtur.cfg'))

'''Additional Jinja filters'''
def urlify(s):
  return quote_plus(s.encode('utf8').lower())
def dateformat(value, format='%H:%M / %d-%m-%Y'):
    try:
        date_object = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
    except:
        return 
    return date_object.strftime(format)

app.jinja_env.filters['urlify'] = urlify
app.jinja_env.filters['dateformat'] = dateformat

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def make_dicts(cursor, row):
    return dict((cur.description[idx][0], value)
                for idx, value in enumerate(row))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_db()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def get_artist(list_of_songs):
    artists = {s["artist"] for s in list_of_songs}
    if len(artists) > 1:
        return "Various Artists"
    else:
        return artists[0]

'''Access to static files'''
@app.route('/uploads/<user>/<mix>/<path:filename>')
def uploaded_file(user, mix, filename):
    mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix)
    # raise Exception(mix_dir)
    ''' need to use this send_from_directory function so that the proper HTTP
        headers are set and HTML audio API can work properly'''
    return send_from_directory(mix_dir, filename)

@app.route("/")
def home():
    mixes = query_db('select id, name, description, cover, user from mix order by date desc limit 20')
    anthologies = query_db("""
        select a.name, m.name as mix_name, cover, user 
        from anthology as a, mixanthology as ma, mix as m 
        where ma.anthology_id = a.id and m.id = ma.mix_id group by a.id
        order by date desc limit 20
    """)
    return render_template("home.html", mixes=mixes, anthologies=anthologies)

@app.route("/<mix_type>/<mix_name>/")
def mix(mix_type, mix_name):
    mix_votes = {}
    if mix_type == "m":
        songs = query_db("""select m.name as mix_name, cover, s.title, s.artist, disc, position, runtime, date, user from
                                song as s, mix as m
                                where lower(m.name) = ? and s.mix = m.id
                                order by m.id, s.position;""", (unquote_plus(mix_name).lower(),))
    elif mix_type == "a":
        songs = query_db("""select a.name as anthology, m.name as mix_name, cover, s.title, s.artist, disc, position, runtime, date, user from
                                song as s, anthology as a, mixanthology as ma, mix as m
                                where lower(a.name) = ? and ma.anthology_id = a.id and m.id = ma.mix_id and s.mix = m.id
                                order by m.id, s.disc, s.position;""", (unquote_plus(mix_name).lower(),))
    else:
        abort(404)
    return render_template("new_show_mix.html", mix_type=mix_type, mix=None, artist="Various Artists", songs=songs, votes={})

'''

    Run the file!
    
'''
if __name__ == '__main__':
  app.run()