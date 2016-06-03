# -*- coding: utf-8 -*-

'''All the imports'''
import sqlite3, os, time, re, operator, time
from werkzeug import secure_filename
from flask import Flask, g, render_template, send_from_directory, abort, \
    jsonify, request, json, session, flash, redirect, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from tint import image_tint
from audio import Audio
import cStringIO, base64
''' Some forms stuff '''
from flask_wtf import Form
from wtforms.validators import DataRequired, Email
from wtforms.fields import TextField, PasswordField
''' For file zipping '''
from io import BytesIO
import zipfile
from PIL import Image, ImageOps

'''Create the application'''
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'mixtur.cfg'))

from flask.ext.scss import Scss
Scss(app)

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
    if g:
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = connect_db()
    else:
        db = connect_db()
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

def user_exists(user):
    return query_db("""SELECT EXISTS(SELECT * FROM user WHERE name = ?)""", [user], one=True)[0]

def email_exists(user):
    return query_db("""SELECT EXISTS(SELECT * FROM user WHERE email = ?)""",[user], one=True)[0]


'''Access to static files'''
@app.route('/uploads/<user>/<mix>/<path:filename>')
def uploaded_file(user, mix, filename):
    mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix)
    # raise Exception(mix_dir)
    ''' need to use this send_from_directory function so that the proper HTTP
        headers are set and HTML audio API can work properly'''
    return send_from_directory(mix_dir, filename)

def format_runtime(runtime):
    hours, remainder = divmod(runtime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        runtime_str = "{} hour".format(hours)
        if hours > 1:
            runtime_str = "{} hours".format(hours)
        if minutes:
            if minutes > 1:
                return "{}, {} minutes".format(runtime_str, minutes)
            else:
                return "{}, {} minute".format(runtime_str, minutes)
        return runtime_str
    elif minutes:
        if minutes > 1:
            return "{} minutes".format(minutes)
        else:
            return "{} minute".format(minutes)
    elif seconds:
        return "{} seconds".format(seconds)
    return ""

@app.route("/new/")
def home_new():
    return render_template('home_new.html')

@app.route("/new/recent/", defaults={'page': 1})
@app.route("/new/recent/<int:page>/")
def get_recent(page):
    PER_PAGE = 20
    count = query_db('select count(*) as num_mixes from mix where cover is not null;', one=True)
    count = count['num_mixes']
    mixes = []
    offset = PER_PAGE * (page-1)
    mix_rows = query_db('select * from mix where cover is not null order by date desc limit ? offset ?;', [PER_PAGE, offset])
    if not mix_rows and page != 1:
        abort(404)
    for m in mix_rows:
        mix = {'name':m['name'], 'date':m['date'], 'user':m['user'], 'cover':m['cover'], 'slug':m['slug']}
        if mix['cover']:
            cover_no_ext, cover_extension = os.path.splitext(m["cover"])
            thumb = cover_no_ext+"_thumb"+cover_extension
            mix['cover'] = url_for('uploaded_file', user=mix['user'], mix=mix['slug'], filename=thumb)
        mixes.append(mix)
    return jsonify(mixes=mixes, count=count, page=page)

@app.route("/")
def home():
    base_date = datetime(1970, 1, 1)
    # ----------------------------------------------------
    # Mixes
    songs = query_db("""select m.name as mix_name, cover, m.slug as mix_slug, runtime, user from
                            song as s, mix as m
                            where s.mix = m.id
                            order by m.id;""")
    mixes = []

    if songs:
        current_mix = {"slug": None}
        for s in songs:
            runtime = datetime.strptime(s["runtime"], '%Y-%m-%d %H:%M:%S')
            if s["mix_slug"] != current_mix["slug"]:
                if current_mix["slug"]:
                    current_mix["runtime"] = format_runtime(current_mix["runtime"])
                    mixes.append(current_mix)
                current_mix = {
                    "slug": s["mix_slug"],
                    "title": unicode(s["mix_name"]),
                    "author": s["user"],
                    "cover": s["cover"],
                    "songs": 0,
                    "runtime": base_date - base_date
                }
            current_mix["songs"] += 1
            current_mix["runtime"] += runtime - base_date
            if current_mix["cover"]:
                cover_no_ext, cover_extension = os.path.splitext(current_mix["cover"])
                current_mix["thumb"] = cover_no_ext+"_thumb"+cover_extension
        current_mix["runtime"] = format_runtime(current_mix["runtime"])
        mixes.append(current_mix)

    # ----------------------------------------------------
    # Anthologies
    songs = query_db("""
        select a.name as anthology_name, a.slug as anthology_slug, m.name as mix_name, cover, m.slug as mix_slug, runtime, user from
        song as s, anthology as a, mixanthology as ma, mix as m
        where ma.anthology_id = a.id and m.id = ma.mix_id and s.mix = m.id
        order by a.id, m.id;
    """)
    anthologies = []
    if songs:
        current_anthology = {"slug": None, "cover": [], "albums": [], "runtime": base_date - base_date}
        for i, s in enumerate(songs):
            runtime = datetime.strptime(s["runtime"], '%Y-%m-%d %H:%M:%S')
            if s["anthology_slug"] != current_anthology["slug"]:
                if current_anthology["slug"]:
                    current_anthology["cover"] = list(current_anthology["cover"])
                    current_anthology["albums"] = len(current_anthology["albums"])
                    current_anthology["runtime"] = format_runtime(current_anthology["runtime"])
                    anthologies.append(current_anthology)
                current_anthology = {
                    "slug": s["anthology_slug"],
                    "title": unicode(s["anthology_name"]),
                    "author": s["user"],
                    "cover": set([]),
                    "albums": set([]),
                    "songs": 0,
                    "runtime": base_date - base_date
                }
            current_anthology["cover"].add(url_for('uploaded_file', user=s["user"], mix=s["mix_slug"], filename=s["cover"]))
            current_anthology["albums"].add(s["mix_slug"])
            current_anthology["songs"] += 1
            current_anthology["runtime"] += runtime - base_date
        current_anthology["cover"] = list(current_anthology["cover"])
        current_anthology["albums"] = len(current_anthology["albums"])
        current_anthology["runtime"] = format_runtime(current_anthology["runtime"])
        anthologies.append(current_anthology)

    return render_template("home.html", mixes=mixes, anthologies=anthologies)

@app.route("/<user>/")
def profile(user):
    '''A list of a users specific uploads'''
    if not user_exists(user):
        abort(404)

    base_date = datetime(1970, 1, 1)
    # ----------------------------------------------------
    # Mixes
    songs = query_db("""select m.name as mix_name, cover, m.slug as mix_slug, runtime, user from
                            song as s, mix as m
                            where s.mix = m.id
                             and  m.user =  ?
                            order by m.id;""", [user])
    mixes = []

    if songs:
        current_mix = {"slug": None}
        for s in songs:
            runtime = datetime.strptime(s["runtime"], '%Y-%m-%d %H:%M:%S')
            if s["mix_slug"] != current_mix["slug"]:
                if current_mix["slug"]:
                    current_mix["runtime"] = format_runtime(current_mix["runtime"])
                    mixes.append(current_mix)
                current_mix = {
                    "slug": s["mix_slug"],
                    "title": unicode(s["mix_name"]),
                    "author": s["user"],
                    "cover": s["cover"],
                    "songs": 0,
                    "runtime": base_date - base_date
                }
            current_mix["songs"] += 1
            current_mix["runtime"] += runtime - base_date
        current_mix["runtime"] = format_runtime(current_mix["runtime"])
        mixes.append(current_mix)

    # Anthologies
    songs = query_db("""
        select a.name as anthology_name, a.slug as anthology_slug, m.name as mix_name, cover, m.slug as mix_slug, runtime, user from
        song as s, anthology as a, mixanthology as ma, mix as m
        where ma.anthology_id = a.id and m.id = ma.mix_id and s.mix = m.id and user= ?
        order by a.id, m.id;
    """, [user])
    anthologies = []
    if songs:
        current_anthology = {"slug": None, "cover": [], "albums": [], "runtime": base_date - base_date}
        for i, s in enumerate(songs):
            runtime = datetime.strptime(s["runtime"], '%Y-%m-%d %H:%M:%S')
            if s["anthology_slug"] != current_anthology["slug"]:
                if current_anthology["slug"]:
                    current_anthology["cover"] = list(current_anthology["cover"])
                    current_anthology["albums"] = len(current_anthology["albums"])
                    current_anthology["runtime"] = format_runtime(current_anthology["runtime"])
                    anthologies.append(current_anthology)
                current_anthology = {
                    "slug": s["anthology_slug"],
                    "title": s["anthology_name"],
                    "author": s["user"],
                    "cover": set([]),
                    "albums": set([]),
                    "songs": 0,
                    "runtime": base_date - base_date
                }
            current_anthology["cover"].add(url_for('uploaded_file', user=s["user"], mix=s["mix_slug"], filename=s["cover"]))
            current_anthology["albums"].add(s["mix_slug"])
            current_anthology["songs"] += 1
            current_anthology["runtime"] += runtime - base_date
        current_anthology["cover"] = list(current_anthology["cover"])
        current_anthology["albums"] = len(current_anthology["albums"])
        current_anthology["runtime"] = format_runtime(current_anthology["runtime"])
        anthologies.append(current_anthology)

    return render_template("home.html", mixes=mixes, anthologies=anthologies)


@app.route("/<mix_type>/<mix_slug>/")
def mix(mix_type, mix_slug):
    mix_votes = {}
    listens = None
    num_albums = 1
    total_time = 3
    base_date = datetime(1970, 1, 1)
    if mix_type == "m":
        mix = query_db("SELECT * FROM mix WHERE slug=?;", (mix_slug,), one=True)
        if not mix: abort(404)
        songs = query_db("""select m.name as mix_name, cover, m.slug as mix_slug, s.title, s.artist, s.slug as song_slug, disc, position, runtime, date, palette, user, desc, s.id as song_id
                                from song as s, mix as m
                                where m.slug = ? and s.mix = m.id
                                order by m.id, s.position;""", (mix_slug,))
        listens = query_db("""select song, count(*) as listens from listen where mix = ? group by song;""", (mix['id'],))
        if request.args.get('download') is not None:
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                for s in songs:
                    song_file = os.path.join(app.config['UPLOAD_FOLDER'], s["user"], s["mix_slug"], s["song_slug"])
                    data = zipfile.ZipInfo(s["song_slug"])
                    data.date_time = time.localtime(time.time())[:6]
                    data.compress_type = zipfile.ZIP_DEFLATED
                    zf.writestr(data, open(song_file).read())
            memory_file.seek(0)
            return send_file(memory_file, attachment_filename='{}.zip'.format(s["mix_slug"]), as_attachment=True)
    elif mix_type == "a":
        songs = query_db("""select a.name as anthology_name, m.name as mix_name, cover, m.slug as mix_slug, s.title, s.artist, s.slug as song_slug, disc, palette, position, runtime, m.date, user, desc
                                from song as s, anthology as a, mixanthology as ma, mix as m
                                where a.slug = ? and ma.anthology_id = a.id and m.id = ma.mix_id and s.mix = m.id
                                order by m.id, s.disc, s.position;""", (mix_slug,))
        num_albums = len({s["mix_slug"] for s in songs})
    else:
        abort(404)

    if not songs:
        flash("Could not find {} mix.".format(mix_slug), "error")
        return redirect(url_for("home"))

    # format palettes
    def fix_palette(s):
        if "palette" in s and s["palette"]:
            s["palette"] = json.loads(s["palette"])
        else:
            s["palette"] = ["#eee", "#222"]
        return s
    songs = map(dict, songs)
    songs = map(fix_palette, songs)
    if listens:
        for l in listens:
            s = filter(lambda x: x['song_id'] == l['song'], songs)[0]
            s['listens'] = l['listens']
    # get runtimes
    runtimes = [datetime.strptime(s["runtime"], '%Y-%m-%d %H:%M:%S') for s in songs]
    runtimes = [r - base_date for r in runtimes]
    total_runtime = reduce(operator.add, runtimes)
    hours, remainder = divmod(total_runtime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return render_template("mix.html",
                                mix_type=mix_type,
                                num_albums=num_albums,
                                total_runtime={"hours":hours, "minutes":minutes, "seconds":seconds},
                                songs=songs,
                                votes={})

@app.route("/<mix_type>/<mix_slug>/delete/")
def mix_del(mix_type, mix_slug):
    if not session.get("logged_in"): abort(401)
    tbl = "mix" if mix_type == "m" else "anthology"

    # step 1 - make sure mix exists
    mix = query_db('select * from {} where slug=?'.format(tbl), (mix_slug, ), one=True)
    if not mix:
        flash("Could not delete, {} does not exist.".format(tbl), "error")
        return redirect(url_for("home"))

    # step 2 - make sure mix user is the same as logged in user
    if mix_type == "m":
        usr = mix["user"]
    else:
        usr = query_db('select user from mix, mixanthology where mix.id=mixanthology.mix_id and mixanthology.anthology_id = ?', (mix["id"], ), one=True)
        usr = usr["user"]
    if usr != g.user:
        flash("Could not delete, this mix isn't yours to delete.", "error")
        return redirect(url_for("home"))

    # step 3 - delete all files associated with this mix (songs and album art)
    #           including the directory itself
    if mix_type == "m":
        mix_slug = unicode(mix["slug"])
        user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], mix["user"], mix_slug)
        if os.path.exists(user_mix_dir):
            file_list = os.listdir(user_mix_dir)
            for file_name in file_list:
                os.remove(os.path.join(user_mix_dir, file_name))
            os.rmdir(user_mix_dir)

        # step 4 - delete all songs from DB
        query_db('delete from song where mix=?', (mix["id"], ), update=True)

    # step 5 - delete actual mix from DB
    query_db('delete from {} where id=?'.format(tbl), (mix["id"], ), update=True)

    if mix_type == "a":
        query_db('delete from mixanthology where anthology_id=?', (mix["id"], ), update=True)

    flash("{} successfully deleted.".format(tbl.capitalize()), "success")
    return redirect(url_for("home"))

@app.route("/create/mix/")
@app.route("/create/mix/<mix_slug>/")
def create_mix(mix_slug=None):
    if not session.get("logged_in"):
        summer = request.args.get('summer', False)
        flash("You need to be logged in to make a mix!", "error")
        return redirect(url_for("login"))
    if mix_slug:
        mix = query_db("""select * from mix where slug = ?;""", (mix_slug,), one=True)
        songs = query_db("""select s.* from song as s, mix as m where m.slug = ? and s.mix = m.id order by s.position;""", (mix_slug,))
        return render_template("create_mix.html", mix=mix, songs=songs, summer=mix["summer"])
    else:
        summer = request.args.get('summer', False)
        return render_template("create_mix.html", summer=summer)

def make_slug(title, tbl="mix"):
    slug = secure_filename(title)
    if query_db("SELECT * FROM {} WHERE slug=?".format(tbl), (slug,), one=True) is None:
        return slug
    version = 2
    while True:
        new_slug = slug + str(version)
        if query_db("SELECT * FROM {} WHERE slug=?".format(tbl), (new_slug,), one=True) is None:
            break
        version += 1
    return new_slug

@app.route("/create/anthology/", methods=["GET", "POST"])
def create_anthology():
    if not session.get("logged_in"): abort(401)
    if request.method == 'POST':
        anth = request.get_json()
        anth_title = anth.get('title', None)
        anth_desc = anth.get('desc', None)
        anth_mixes = anth.get('mixes', [])

        # create anthology
        anth_slug = make_slug(anth_title, tbl="anthology")
        anth_id = insert_db("anthology", fields=('name', 'slug', 'date'), args=(anth_title, anth_slug, str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))

        # add mixes
        for m_id in anth_mixes:
            insert_db("mixanthology", fields=('mix_id', 'anthology_id'), args=(m_id, anth_id))

        return jsonify(id=anth_id, slug=anth_slug)
    mixes = query_db("select * from mix where user = ? order by id;", (g.user,))
    return render_template("create_anthology.html", mixes=mixes)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route("/uploadr/<file_type>/", methods=["GET", "POST"])
def uploadr_file(file_type):
    if not session.get("logged_in"): abort(401)
    # return jsonify(name="filename", size="file_size", file_type=file_type)
    if request.method == 'POST':
        mix_title = request.form.get('mix_title')
        mix_summer = int(request.form.get('mix_summer', 0))
        mix_id = request.form.get('mix_id')
        mix_desc = request.form.get('mix_desc')
        mix_palette = request.form.get('mix_palette')
        no_img = request.form.get('no_img')
        user = session.get("user")
        file = request.files.get('file')
        artist = request.form.get('song_artist')
        title = request.form.get('song_title') or "Untitled"
        track_num = request.form.get('song_num')
        song_id = request.form.get('song_id')
        song_remove = request.form.get('song_remove')

        if not mix_id:
            new_mix_title = mix_title or 'Untitled Mix'
            mix_slug = make_slug(new_mix_title)
            mix_id = insert_db("mix", fields=('date', 'user', 'name', 'slug', 'desc', 'summer'), args=(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), user, new_mix_title, mix_slug, mix_desc, mix_summer))
            user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix_slug)
            if not os.path.exists(user_mix_dir): os.makedirs(user_mix_dir)
        else:
            mix = query_db("SELECT * FROM mix WHERE id=?", (mix_id,), one=True)
            mix_slug = unicode(mix["slug"])
            user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix_slug)

            if mix_title:
                if mix_title != mix["name"]:
                    new_mix_slug = make_slug(mix_title)
                    query_db("UPDATE mix SET name=?, slug=? WHERE id=?", (mix_title, new_mix_slug, mix_id), update=True)
                    # also need to rename upload directory
                    user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix_slug)
                    new_user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, new_mix_slug)
                    os.rename(user_mix_dir, new_user_mix_dir)
                    user_mix_dir = new_user_mix_dir
                    mix_slug = new_mix_slug
                if mix_summer != mix["summer"]:
                    query_db("UPDATE mix SET summer=? WHERE id=?", (mix_summer, mix_id), update=True)
            if mix_desc is not None:
                query_db("UPDATE mix SET `desc`=? WHERE id=?", [mix_desc, mix_id], update=True)

        b64_img = None
        if no_img:
            input_image_path = os.path.join(app.root_path, 'static/img/no_cover.jpg')
            (new_img, tinted_col) = image_tint(input_image_path)
            new_img.save(os.path.join(user_mix_dir, "default_cover.jpg"))
            jpeg_image_buffer = cStringIO.StringIO()
            new_img.save(jpeg_image_buffer, format="JPEG")
            b64_img = base64.b64encode(jpeg_image_buffer.getvalue())
            query_db("UPDATE mix SET cover=? WHERE id=?", ["default_cover.jpg", mix_id], update=True)

        if mix_palette:
            query_db("UPDATE mix SET palette=? WHERE id=?", [mix_palette, mix_id], update=True)

        if file and allowed_file(file.filename):
            if "image" in file.mimetype:
                filename = secure_filename(file.filename)

                lg_file_path = os.path.join(user_mix_dir, filename)
                filename_no_ext, file_extension = os.path.splitext(filename)
                thumb_file_path = os.path.join(user_mix_dir, filename_no_ext+"_thumb"+file_extension)

                MAX_SIZE = 1600
                QUALITY = 80
                image = Image.open(file)
                original_size = max(image.size[0], image.size[1])

                if original_size >= MAX_SIZE:
                    if (image.size[0] > image.size[1]):
                        resized_width = MAX_SIZE
                        resized_height = int(round((MAX_SIZE/float(image.size[0]))*image.size[1]))
                    else:
                        resized_height = MAX_SIZE
                        resized_width = int(round((MAX_SIZE/float(image.size[1]))*image.size[0]))

                    full_image = image.resize((resized_width, resized_height), Image.ANTIALIAS)
                else:
                    full_image = image
                full_image.save(lg_file_path, image.format, quality=QUALITY)

                thumb_image = ImageOps.fit(image, (500,500), Image.ANTIALIAS)
                thumb_image.save(thumb_file_path, image.format, quality=90)

                # was there already a file? if so delete it
                cover = query_db("SELECT cover FROM mix WHERE id=?", (mix_id,), one=True)["cover"]
                if cover:
                    os.remove(os.path.join(user_mix_dir, cover))
                    # also remove thumb
                    cover_no_ext, cover_extension = os.path.splitext(cover)
                    os.remove(os.path.join(user_mix_dir, cover_no_ext+"_thumb"+cover_extension))
                # add cover img file_name to db
                query_db("UPDATE mix SET cover=?, palette=? WHERE id=?", [filename, mix_palette, mix_id], update=True)
                # add cover to all songs too
                songs = query_db("SELECT * FROM song WHERE mix=?", (mix_id,))
                for s in songs:
                    audio = Audio(os.path.join(user_mix_dir, s["slug"]))
                    audio.albumart(os.path.join(user_mix_dir, filename))
            if "audio" in file.mimetype:
                filename = secure_filename(u"{:02d} {} - {}.mp3".format(int(track_num), artist, title))
                file.save(os.path.join(user_mix_dir, filename))
                mix_title, cover = query_db("SELECT name, cover FROM mix WHERE id=?", (mix_id,), one=True)
                mix_title = unicode(mix_title)
                # add song file_name to db -
                audio = Audio(os.path.join(user_mix_dir, filename))
                audio.flush()
                audio.title(title)
                audio.artist(artist)
                audio.tracknumber(track_num)
                audio.album(mix_title)
                audio.compilation()
                if cover:
                    audio.albumart(os.path.join(user_mix_dir, cover))
                runtime = audio.runtime()
                insert_db("song", fields=('title','artist','position','runtime','slug','mix'), args=(title, artist, track_num, runtime, filename, mix_id))

        if song_id:
            if song_remove:
                song_file = query_db("SELECT slug FROM song WHERE id=?", (song_id,), one=True)["slug"]
                os.remove(os.path.join(user_mix_dir, song_file))
                query_db("DELETE FROM song WHERE id=?", [song_id], update=True)
            else:
                song = query_db("SELECT * FROM song WHERE id=?", (song_id,), one=True)
                mix_title, cover = query_db("SELECT name, cover FROM mix WHERE id=?", (mix_id,), one=True)
                filename = secure_filename(u"{:02d} {} - {}.mp3".format(int(track_num), artist, title))
                os.rename(os.path.join(user_mix_dir, song["slug"]), os.path.join(user_mix_dir, filename))
                # add song file_name to db -
                audio = Audio(os.path.join(user_mix_dir, filename))
                audio.flush()
                audio.title(title)
                audio.artist(artist)
                audio.tracknumber(track_num)
                audio.album(mix_title)
                audio.compilation()
                if cover:
                    audio.albumart(os.path.join(user_mix_dir, cover))
                query_db("UPDATE song SET title=?, artist=?, position=?, slug=? WHERE id=?", [title, artist, track_num, filename, song_id], update=True)


        return jsonify(mix_id=mix_id, mix_slug=mix_slug, b64_img=b64_img)

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

'''Generate PW'''
@app.route("/pw/", methods=["GET", "POST"])
def pw():
    pw = None
    if request.method == 'POST':
        pw = generate_password_hash(request.form["pw"], salt_length=11)
    return render_template('pw.html', pw=pw)

'''Sign Up'''
class signUp(Form):
    email = TextField("email", [DataRequired("Email is required"), Email()])
    pwd = PasswordField("pwd", [DataRequired("Password is required")])

@app.route("/signup/", methods=["GET", "POST"])
def signup():

    form = signUp(csrf_enabled=False)
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "error")
        return render_template('signup.html')

    email = form.email.data
    name =  email.split("@")[0]
    # Unless someone else got it
    if email_exists(email):
        flash("A user is already assoicated with this email.", "error")
        return render_template('signup.html')
    pw = generate_password_hash(form.pwd.data , salt_length=11)

    try:
        insert_db("user", fields=('name', 'email', 'password'), args=(name, email, pw))
        flash("Successfully signed up. Please sign in.","success")
        return redirect(url_for("login"))

    except Exception as e:
        flash("Failed to create user. Try again later.", "error")
        return render_template('signup.html')

@app.route("/<mix_type>/<mix_slug>/listen/<int:song_id>/", methods=["POST"])
def song_listen(mix_type, mix_slug, song_id):
    if request.method == 'POST':
        mix = query_db("SELECT * FROM mix WHERE slug=?;", (mix_slug,), one=True)
        song = query_db("SELECT * FROM song WHERE id=?;", (song_id,), one=True)
        if not song or not mix: return jsonify(success=False, error="No such song on this mix.")
        insert_db("listen", fields=('user', 'mix', 'song'), args=(g.user, mix['id'], song_id))
        return jsonify(success=True)
    else:
        abort(404)

'''open call for summer mixXxes!'''
@app.route("/summer16/")
@app.route("/summer/")
def summer16():
    return render_template('summer16.html')

'''Just catch all the 404s plz'''
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(401)
def not_found_error(error):
    return render_template('401.html'), 401
'''

    Run the file!

'''
if __name__ == '__main__':
  app.run()
