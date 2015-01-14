# -*- coding: utf-8 -*-

'''All the imports'''
import sqlite3, os, time, re, operator, time
from werkzeug import secure_filename
from flask import Flask, g, render_template, send_from_directory, abort, \
    jsonify, request, json, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from mutagen.mp3 import MP3
from tint import image_tint

'''Create the application'''
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'mixtur.cfg'))

@app.before_request
def before_request():
  g.user = session.get('user')

'''Additional Jinja filters'''
def dateformat(value, format='%H:%M / %d-%m-%Y'):
    try:
        date_object = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except:
        return 
    return date_object.strftime(format)

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
    mixes = query_db('select id, name, desc, cover, user, slug from mix order by date desc limit 20')
    anthologies = query_db("""
        select a.name, m.name as mix_name, cover, user, a.slug, m.slug as mix_slug
        from anthology as a, mixanthology as ma, mix as m 
        where ma.anthology_id = a.id and m.id = ma.mix_id group by a.id
        order by date desc limit 20
    """)
    return render_template("home.html", mixes=mixes, anthologies=anthologies)

@app.route("/<mix_type>/<mix_slug>/")
def mix(mix_type, mix_slug):
    mix_votes = {}
    num_albums = 1
    total_time = 3
    base_date = datetime(1970, 1, 1)
    if mix_type == "m":
        songs = query_db("""select m.name as mix_name, cover, m.slug as mix_slug, s.title, s.artist, s.slug as song_slug, disc, position, runtime, date, palette, user from
                                song as s, mix as m
                                where m.slug = ? and s.mix = m.id
                                order by m.id, s.position;""", (mix_slug,))
    elif mix_type == "a":
        songs = query_db("""select a.name as anthology_name, m.name as mix_name, cover, m.slug as mix_slug, s.title, s.artist, s.slug as song_slug, disc, palette, position, runtime, date, user from
                                song as s, anthology as a, mixanthology as ma, mix as m
                                where a.slug = ? and ma.anthology_id = a.id and m.id = ma.mix_id and s.mix = m.id
                                order by m.id, s.disc, s.position;""", (mix_slug,))
        num_albums = len({s["mix_name"] for s in songs})
    else:
        abort(404)
    
    # format palettes
    def fix_palette(s):
        if "palette" in s and s["palette"]:
            s["palette"] = json.loads(s["palette"])
        else:
            s["palette"] = ["#eee", "#222"]
        return s
    songs = map(dict, songs)
    songs = map(fix_palette, songs)
    # get runtimes
    runtimes = [datetime.strptime(s["runtime"], '%Y-%m-%d %H:%M:%S') for s in songs]
    runtimes = [r - base_date for r in runtimes]
    total_runtime = reduce(operator.add, runtimes)
    hours, remainder = divmod(total_runtime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return render_template("new_show_mix.html", 
                                mix_type=mix_type,
                                num_albums=num_albums,
                                total_runtime={"hours":hours, "minutes":minutes, "seconds":seconds},
                                songs=songs, 
                                votes={})

@app.route("/<mix_type>/<mix_slug>/delete/")
def mix_del(mix_type, mix_slug):
    if not session.get("logged_in"): abort(401)
    
    # step 1 - make sure mix exists
    mix = query_db('select * from mix where slug=?', (mix_slug, ), one=True)
    if not mix:
        flash("Could not delete, mix does not exist.", "error")
        return redirect(url_for("home"))
    
    # step 2 - make sure mix user is the same as logged in user
    if mix["user"] != g.user:
        flash("Could not delete, this mix isn't yours to delete.", "error")
        return redirect(url_for("home"))
    
    # step 3 - delete all files associated with this mix (songs and album art)
    #           including the directory itself
    user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], mix["user"], mix["slug"])
    if os.path.exists(user_mix_dir):
        file_list = os.listdir(user_mix_dir)
        for file_name in file_list:
            os.remove(os.path.join(user_mix_dir, file_name))
        os.rmdir(user_mix_dir)

    # step 4 - delete all songs from DB
    query_db('delete from song where mix=?', (mix["id"], ), update=True)
    
    # step 5 - delete all songs from DB
    query_db('delete from mix where id=?', (mix["id"], ), update=True)
    
    flash("Mix successfully deleted.", "success")
    return redirect(url_for("home"))

@app.route("/uploadr/")
def uploadr():
    if not session.get("logged_in"): abort(401)
    return render_template("uploadr.html")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

def parse_files(file_dict):
    if not file_dict: return None
    files = dict(file_dict).items()
    files = [(int(re.findall(r'\d+', f_tuple[0])[0]), f_tuple[1][0]) for f_tuple in files]
    files.sort()
    return [f[1] for f in files]

def make_slug(title):
    slug = secure_filename(title)
    if query_db("SELECT * FROM mix WHERE slug=?", (slug,), one=True) is None:
        return slug
    version = 2
    while True:
        new_slug = slug + str(version)
        if query_db("SELECT * FROM mix WHERE slug=?", (new_slug,), one=True) is None:
            break
        version += 1
    return new_slug

@app.route("/uploadr/<file_type>/", methods=["GET", "POST"])
def uploadr_file(file_type):
    if not session.get("logged_in"): abort(401)
    # return jsonify(name="filename", size="file_size", file_type=file_type)
    if request.method == 'POST':
        mix_title = request.form.get('mix_title')
        mix_id = request.form.get('mix_id')
        mix_desc = request.form.get('mix_desc')
        mix_palette = request.form.get('mix_palette')
        no_img = request.form.get('no_img')
        user = session.get("user")
        files = parse_files(request.files)
        artists = request.form.getlist('song_artist')
        titles = request.form.getlist('song_title')
        track_nums = request.form.getlist('song_num')
        
        if not mix_id:
            new_mix_title = mix_title or 'Untitled Mix'
            mix_slug = make_slug(new_mix_title)
            mix_id = insert_db("mix", fields=('date', 'user', 'name', 'slug'), args=(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), user, new_mix_title, mix_slug))

        if mix_title:
            mix_slug = make_slug(mix_title)
            query_db("UPDATE mix SET name=?, slug=? WHERE id=?", (mix_title, mix_slug, mix_id), update=True)
        else:
            mix_slug = query_db("SELECT slug FROM mix WHERE id=?", (mix_id,), one=True)["slug"]
        
        user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix_slug)
        if not os.path.exists(user_mix_dir): os.makedirs(user_mix_dir)
        
        if mix_desc:
            query_db("UPDATE mix SET desc=? WHERE id=?", [mix_desc, mix_id], update=True)
        
        if no_img:
            input_image_path = os.path.join(app.root_path, 'static/img/no_cover.jpg')
            new_img = image_tint(input_image_path)
            new_img.save(os.path.join(user_mix_dir, "default_cover.jpg"))
            query_db("UPDATE mix SET cover=? WHERE id=?", ["default_cover.jpg", mix_id], update=True)
        
        if mix_palette:
            query_db("UPDATE mix SET palette=? WHERE id=?", [mix_palette, mix_id], update=True)
        
        if files:
            for f, artist, title, track_num in zip(files, artists, titles, track_nums):
                # raise Exception(f, artist, title, track_num)
                if f and allowed_file(f.filename):
                    filename = secure_filename(f.filename)
                    f.save(os.path.join(user_mix_dir, filename))
                    if "image" in f.mimetype:
                        # add cover img file_name to db
                        query_db("UPDATE mix SET cover=?, palette=? WHERE id=?", [filename, mix_palette, mix_id], update=True)
                    if "audio" in f.mimetype:
                        # add song file_name to db
                        audio = MP3(os.path.join(user_mix_dir, filename))
                        runtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(audio.info.length))
                        insert_db("song", fields=('title','artist','position','runtime','slug','mix'), args=(title, artist, track_num, runtime, filename, mix_id))
        
        return jsonify(mix_id=mix_id, mix_slug=mix_slug)

'''

    The Login/out Views!
    
'''
'''Login'''
@app.route("/login/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        '''try to find user'''
        user = query_db("SELECT name, password FROM user WHERE email=?", [request.form["username"].lower()], one=True)
        if not user:
            error = "Invalid username"
        elif not check_password_hash(user["password"], request.form["password"]):
            error = "Invalid password"
        else:
            session["logged_in"] = True
            session["user"] = user[0]
            flash("You were logged in", "success")
            return redirect(url_for("home"))
    return render_template("login.html", error=error)

'''Logout'''
@app.route("/logout/")
def logout():
    session.pop("logged_in", None)
    session.pop("user", None)
    flash("Logged out", "success")
    return redirect(url_for("home"))
'''

    Run the file!
    
'''
if __name__ == '__main__':
  app.run()