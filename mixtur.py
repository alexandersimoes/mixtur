# -*- coding: utf-8 -*-

'''All the imports'''
import sqlite3, os, time, re
from werkzeug import secure_filename
from flask import Flask, g, render_template, send_from_directory, abort, jsonify, request
from urllib import quote_plus, unquote_plus
from datetime import datetime
from mutagen.mp3 import MP3

'''Create the application'''
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'mixtur.cfg'))

'''Additional Jinja filters'''
def urlify(s):
  return quote_plus(s.encode('utf8').lower())
def dateformat(value, format='%H:%M / %d-%m-%Y'):
    try:
        date_object = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
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

def query_db(query, args=(), one=False, update=False):
    cur = get_db().execute(query, args)
    if update:
        return get_db().commit()
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def insert_db(table, fields=(), args=()):
    # g.db is the database connection
    query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table,
        ', '.join(fields),
        ', '.join(['?'] * len(args))
    )
    cur = get_db().execute(query, args)
    get_db().commit()
    id = cur.lastrowid
    cur.close()
    return id

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
    mixes = query_db('select id, name, description, cover, user, slug from mix order by date desc limit 20')
    anthologies = query_db("""
        select a.name, m.name as mix_name, cover, user, a.slug, m.slug as mix_slug
        from anthology as a, mixanthology as ma, mix as m 
        where ma.anthology_id = a.id and m.id = ma.mix_id group by a.id
        order by date desc limit 20
    """)
    return render_template("home2.html", mixes=mixes, anthologies=anthologies)

@app.route("/<mix_type>/<mix_slug>/")
def mix(mix_type, mix_slug):
    mix_votes = {}
    if mix_type == "m":
        songs = query_db("""select m.name as mix_name, cover, m.slug as mix_slug, s.title, s.artist, s.slug as song_slug, disc, position, runtime, date, user from
                                song as s, mix as m
                                where m.slug = ? and s.mix = m.id
                                order by m.id, s.position;""", (mix_slug,))
    elif mix_type == "a":
        songs = query_db("""select a.name as anthology, m.name as mix_name, cover, m.slug as mix_slug, s.title, s.artist, s.slug as song_slug, disc, position, runtime, date, user from
                                song as s, anthology as a, mixanthology as ma, mix as m
                                where a.slug = ? and ma.anthology_id = a.id and m.id = ma.mix_id and s.mix = m.id
                                order by m.id, s.disc, s.position;""", (mix_slug,))
    else:
        abort(404)
    return render_template("new_show_mix.html", mix_type=mix_type, mix=None, artist="Various Artists", songs=songs, votes={})

@app.route("/uploadr/")
def uploadr():
    return render_template("uploadr.html")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

def parse_files(file_dict):
    files = dict(file_dict).items()
    files = [(int(re.findall(r'\d+', f_tuple[0])[0]), f_tuple[1][0]) for f_tuple in files]
    files.sort()
    return [f[1] for f in files]

@app.route("/uploadr/<file_type>/", methods=["GET", "POST"])
def uploadr_file(file_type):
    # return jsonify(name="filename", size="file_size", file_type=file_type)
    if request.method == 'POST':
        mix_title = request.form.get('mix_title')
        mix_id = request.form.get('mix_id')
        user = "aljaffe"
        files = parse_files(request.files)
        artists = request.form.getlist('song_artist')
        titles = request.form.getlist('song_title')
        track_nums = request.form.getlist('song_num')
        
        if not mix_id:
            mix_id = insert_db("mix", fields=('date', 'user'), args=(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), user))

        if mix_title:
            mix_slug = secure_filename(mix_title)
            query_db("UPDATE mix SET name=?, slug=? WHERE id=?", [mix_title, mix_slug, mix_id], update=True)
        
        # user = session["user"]
        for f, artist, title, track_num in zip(files, artists, titles, track_nums):
            # raise Exception(f, artist, title, track_num)
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix_slug)
                if not os.path.exists(user_mix_dir): os.makedirs(user_mix_dir)
                f.save(os.path.join(user_mix_dir, filename))
                print f.mimetype
                if "image" in f.mimetype:
                    print 'made it!!!!', filename, mix_id
                    # add cover img file_name to db
                    query_db("UPDATE mix SET cover=? WHERE id=?", [filename, mix_id], update=True)
                if "audio" in f.mimetype:
                    # add song file_name to db
                    audio = MP3(os.path.join(user_mix_dir, filename))
                    runtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(audio.info.length))
                    insert_db("song", fields=('title','artist','position','runtime','slug','mix'), args=(title, artist, track_num, runtime, filename, mix_id))
            
            
                # return jsonify(name=filename)
                # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # return redirect(url_for('uploaded_file',
                #                                 filename=filename))
        
        # return jsonify(files=str(files))
        
        return jsonify(mix_id=mix_id)
        
        files = request.files.getlist('song')
        return jsonify(name="filename", size="file_size", file_type=file_type, files=str(files), test=str(request.form))
        for f in files:
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                updir = os.path.join(basedir, 'upload/')
                f.save(os.path.join(updir, filename))
                file_size = os.path.getsize(os.path.join(updir, filename))
            else:
                app.logger.info('ext name error')
                return jsonify(error='ext name error')
        return jsonify(name=filename, size=file_size)
'''

    Run the file!
    
'''
if __name__ == '__main__':
  app.run()