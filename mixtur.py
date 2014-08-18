# -*- coding: utf-8 -*-

'''All the imports'''
import sqlite3, os, datetime
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, send_from_directory, safe_join, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import secure_filename
from contextlib import closing
from urllib import quote_plus, unquote_plus
from PIL import Image

'''Create the application'''
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'mixtur.cfg'))

# print app.config["UPLOAD_FOLDER"]

'''Additional Jinja filters'''
def urlify(s):
  return quote_plus(s.encode('utf8').lower())

def access(dic, key, default=None):
  if key in dic:
    return dic[key]
  else:
    return default

app.jinja_env.filters['urlify'] = urlify
app.jinja_env.filters['access'] = access

'''Database helpers'''
@app.before_request
def before_request():
  g.db = sqlite3.connect(app.config['DATABASE'])

@app.teardown_request
def teardown_request(exception):
  g.db.close()

@app.route("/pw/", methods=["GET", "POST"])
def pw():
    pw = None
    if request.method == 'POST':
        pw = generate_password_hash(request.form["pw"], salt_length=11)
    return render_template('pw.html', pw=pw)

'''General helpers'''
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in app.config["ALLOWED_EXTENSIONS"]

def del_dir(this_dir):
    for the_file in os.listdir(this_dir):
        file_path = os.path.join(this_dir, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception, e:
            print e
    os.rmdir(this_dir)

'''

    The Homepage Views!
    
'''
'''Access to static files'''
@app.route('/uploads/<user>/<mix>/<path:filename>')
def uploaded_file(user, mix, filename):
    mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], user, mix)
    # raise Exception(mix_dir)
    ''' need to use this send_from_directory function so that the proper HTTP
        headers are set and HTML audio API can work properly'''
    return send_from_directory(mix_dir, filename)

'''Home'''
@app.route("/<mix_name>/edit", endpoint="all_mixes_edit")
@app.route("/")
def all_mixes(mix_name=None):    
    mix, action = None, None
    if mix_name:
        action = "edit"
        cur = g.db.execute("select id, name, description, cover, user from mix where lower(name) = ?", [unquote_plus(mix_name.lower())])
        m = cur.fetchone()
        mix = dict(id=m[0], name=m[1], description=m[2], cover=m[3], user=m[4])
    cur = g.db.execute("select id, name, description, cover, user from mix order by date desc")
    entries = [dict(id=row[0], name=row[1], description=row[2], cover=row[3], user=row[4]) for row in cur.fetchall()]
    return render_template("all_mixes.html", action=action, entries=entries, mix=mix)

'''Add/Edit/Delete Mix'''
@app.route("/<mix_name>/<action>/", endpoint="mix_edit", methods=["GET", "POST"])
@app.route("/create/", methods=["POST"])
def mix_action(action="create", mix_name=None):
    if not session.get("logged_in"):
        abort(401)
  
    if action == "delete":
        cursor = g.db.execute("select id from mix where lower(name) = ?", [unquote_plus(mix_name)])
        mix_id = cursor.fetchone()[0]
        mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], session.get('user'), mix_name)
        del_dir(mix_dir)
        cursor = g.db.execute("delete from mix where id = ?", [mix_id])
        g.db.commit()
        cursor = g.db.execute("delete from song where mix = ?", [mix_id])
        flash_msg = "Mix successfully deleted."
    elif action == "edited":
        cursor = g.db.execute("update mix set name=?, description=? where id=?",
                  [request.form["name"], request.form["description"], request.form["id"]])
        flash_msg = "Mix successfully edited."
    else:
        cursor = g.db.execute("insert into mix (name, date, description, user) values (?, ?, ?, ?)",
                          [request.form["name"], str(datetime.datetime.now()),
                          request.form["description"], session.get("user")])
        flash_msg = "New mix successfully added."
        mix_name = urlify(request.form["name"])
    g.db.commit()
  
    # handle file stuff
    if action != "delete":
        id = cursor.lastrowid or request.form["id"]
        file = request.files['file']
        if file:
            try:
                img = Image.open(file)
                mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], session.get('user'), mix_name)
                if not os.path.exists(mix_dir): os.makedirs(mix_dir)
                mix_path = os.path.join(mix_dir, "cover.jpg")
                img.save(mix_path, format='JPEG')
            except IOError:
                pass
    flash(flash_msg)
    return redirect(url_for("all_mixes"))

'''

    The Mixtape Views!
    
'''
@app.route('/<mix_name>/song/<int:song_id>/', endpoint="show_mix_edit")
@app.route('/<mix_name>/')
def show_mix(mix_name, song_id=None, action='create'):
    mix, song, votes = None, None, {}
    if song_id:
        action = "edit"
        cur = g.db.execute("select id, title, artist, position from song where id = ?", [song_id])
        s = cur.fetchone()
        song = dict(id=s[0], title=s[1], artist=s[2], position=s[3])
    if unquote_plus(mix_name) == "top voted":
        mix = dict(id="0", name="Top Voted", description="These are the best of the best here folks the ones voted the MOST.")
        cur = g.db.execute("select s.id, title, artist, position, count(v.id) as votes from song as s, vote as v where s.id = v.song group by song order by votes desc")
        fetched_songs = cur.fetchall()
        songs = [dict(id=row[0], title=row[1], artist=row[2], position=i+1) for i, row in enumerate(fetched_songs)]
        cur = g.db.execute("select s.id, v.user from song as s, vote as v where v.song = s.id")
        for row in cur.fetchall():
            votes.setdefault(row[0], []).append(row[1])
    else:
        cur = g.db.execute("select id, name, description, cover, user from mix where lower(name) = ?", [unquote_plus(mix_name).lower()])
        m = cur.fetchone()
        mix = dict(id=m[0], name=m[1], description=m[2], cover=m[3], user=m[4])
        cur = g.db.execute("select id, title, artist, position from song where mix = ? order by position", [mix["id"]])
        songs = [dict(id=row[0], title=row[1], artist=row[2], position=row[3]) for row in cur.fetchall()]
        cur = g.db.execute("select s.id, v.user from song as s, vote as v where v.song = s.id and mix = ?", [mix["id"]])
        for row in cur.fetchall():
            votes.setdefault(row[0], []).append(row[1])
    return render_template("show_mix.html", mix=mix, songs=songs, song=song, action=action, votes=votes)

@app.route('/<mix_name>/song/<int:song_id>/', methods=["POST"])
def song_edit(mix_name, song_id=None):
    # if not session.get("logged_in"): abort(401)
    cursor = g.db.execute("select title, artist from song where id = ?", [song_id])
    old_title, old_artist = cursor.fetchone()
    
    old_file_name = u"song_{0}_{1}.mp3".format(old_artist.replace(" ", "_").lower(), old_title.replace(" ", "_").lower())
    old_song_file = os.path.join(app.config['UPLOAD_FOLDER'], session.get('user', "aljaffe"), mix_name, old_file_name)
    
    title = request.form["title"]
    artist = request.form["artist"]
    user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], session.get("user", "aljaffe"), mix_name)
    if not os.path.exists(user_mix_dir): os.makedirs(user_mix_dir)
    new_file_name = u"song_{0}_{1}.mp3".format(artist.replace(" ", "_").lower(), title.replace(" ", "_").lower())
    new_song_file = os.path.join(user_mix_dir, new_file_name)
    if len(request.files) and request.files.get('file', None):
        # upload new file
        file = request.files["file"]
        if allowed_file(file.filename):
            file.save(new_song_file)
            # try to delete old file
            try:
                os.remove(old_song_file)
            except OSError:
                pass
    else:
        print old_song_file
        print new_song_file
        os.rename(old_song_file, new_song_file)
    cursor = g.db.execute("update song set title=?, artist=? where id=?", [title, artist, song_id])
    g.db.commit()
    # return jsonify({"id": song_id, "artist":artist, "title":title})
    return redirect(url_for('show_mix', mix_name=mix_name))
'''
curl -i \
    -F "title=Je Suis Orphelin"\
    -F "artist=The Balfa Brothers" \
    -F "file=@/Users/alexandersimoes/Sites/mixtur/uploads/song_balfa_brothers_je_suis_orphelin_(the_orphan_waltz).mp3" \
    -X POST http://localhost:5000/my+new+test+mixxx/song/129/
'''

@app.route('/<mix_name>/song/<int:song_id>/', methods=["DELETE"])
def song_delete(mix_name, song_id=None):
    # if not session.get("logged_in"): abort(401)
    if not song_id: abort(401)
    cursor = g.db.execute("select title, artist from song where id = ?", [song_id])
    title, artist = cursor.fetchone()
    file_name = u"song_{0}_{1}.mp3".format(artist.replace(" ", "_").lower(), title.replace(" ", "_").lower())
    song_file = os.path.join(app.config['UPLOAD_FOLDER'], session.get('user'), mix_name, file_name)
    try:
        os.remove(song_file)
    except OSError:
        pass
    cursor = g.db.execute("delete from song where id=?", [song_id])
    g.db.commit()
    return jsonify({"id": song_id, "artist":artist, "title":title})
'''
curl -i \ -X DELETE http://localhost:5000/my+new+test+mixxx/song/107
'''

@app.route('/<mix_name>/song/create', methods=["POST", "GET"])
def song_add(mix_name):
    # if not session.get("logged_in"): abort(401)
    cursor = g.db.execute("select count(*) from song, mix where " \
                            "lower(mix.name)=? and mix.id = song.mix;", [unquote_plus(mix_name)])
    next_track_position = int(cursor.fetchone()[0]) + 1
    cursor = g.db.execute("insert into song (title, artist, position, mix) values (?, ?, ?, ?)",
              [request.form["title"], request.form["artist"],
              next_track_position, request.form["mix"]])
    g.db.commit()
    file = request.files['file']
    title = request.form["title"].replace(" ", "_").lower()
    artist = request.form["artist"].replace(" ", "_").lower()
    if file and allowed_file(file.filename):
        user_mix_dir = os.path.join(app.config['UPLOAD_FOLDER'], session.get("user"), mix_name)
        if not os.path.exists(user_mix_dir): os.makedirs(user_mix_dir)
        new_file_name = u"song_{0}_{1}.mp3".format(artist, title)
        # file.save(os.path.join(user_mix_dir, new_file_name.encode('utf-8')))
        file.save(os.path.join(user_mix_dir, new_file_name))
    return jsonify({"id": cursor.lastrowid, "artist":request.form["artist"], "title":request.form["title"], "filename":new_file_name, "position":next_track_position})
    # return redirect(url_for('show_mix', mix_name=mix_name))

'''

    The Login/out Views!
    
'''
'''Login'''
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        '''try to find user'''
        cur = g.db.execute("select name, password from user where email = ?", [request.form["username"].lower()])
        user = cur.fetchone()
        if not user:
            error = "Invalid username"
        elif not check_password_hash(user[1], request.form["password"]):
            error = "Invalid password"
        else:
            session["logged_in"] = True
            session["user"] = user[0]
            flash("You were logged in")
            return redirect(url_for("all_mixes"))
    return render_template("login.html", error=error)

'''Logout'''
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("user", None)
    flash("You were logged out")
    return redirect(url_for("all_mixes"))


'''

    Run the file!
    
'''
if __name__ == '__main__':
  app.run()