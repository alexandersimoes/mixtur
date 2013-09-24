# -*- coding: utf-8 -*-

'''All the imports'''
import sqlite3, os, datetime
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, send_from_directory, jsonify
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


'''

    The Homepage Views!
    
'''
'''Access to static files'''
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # raise Exception(app.config['UPLOAD_FOLDER'])
    ''' need to use this send_from_directory function so that the proper HTTP
        headers are set and HTML audio API can work properly'''
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
    cur = g.db.execute("select m.id, m.name, m.description, m.cover, u.id, u.name from mix as m, user as u where m.user = u.id order by m.date desc")
    entries = [dict(id=row[0], name=row[1], description=row[2], cover=row[3], user_id=row[4], user=row[5]) for row in cur.fetchall()]
    return render_template("all_mixes.html", action=action, entries=entries, mix=mix)

'''Add/Edit/Delete Mix'''
@app.route("/<mix_name>/<action>/", endpoint="mix_edit", methods=["GET", "POST"])
@app.route("/create/", methods=["POST"])
def mix_action(action="create", mix_name=None):
    if not session.get("logged_in"):
        abort(401)
  
    if action == "delete":
        cursor = g.db.execute("select id, cover from mix where lower(name) = ?", [unquote_plus(mix_name)])
        mix_id, mix_cover = cursor.fetchone()
        if mix_cover:
            cover_img = os.path.join(app.config['UPLOAD_FOLDER'], mix_cover)
            try:
                os.remove(cover_img)
            except OSError:
                pass
        cursor = g.db.execute("delete from mix where id = ?", [mix_id])
        flash_msg = "Mix successfully deleted."
    elif action == "edited":
        cursor = g.db.execute("update mix set name=?, description=? where id=?",
                  [request.form["name"], request.form["description"], request.form["id"]])
        flash_msg = "Mix successfully edited."
    else:
        cursor = g.db.execute("insert into mix (name, date, description, user) values (?, ?, ?, ?)",
                          [request.form["name"], str(datetime.datetime.now()),
                          request.form["description"], session.get("user_id")])
        flash_msg = "New mix successfully added."
    g.db.commit()
  
    # handle file stuff
    if action != "delete":
        id = cursor.lastrowid or request.form["id"]
        file = request.files['file']
        name = request.form["name"].replace(" ", "_")
        if file:
            new_file_name = u"cover_{0}_{1}.png".format(name, id)
            try:
                img = Image.open(file)
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], new_file_name.encode('utf-8')))
                cursor = g.db.execute("update mix set cover=? where id=?",
                          [new_file_name, id])
                g.db.commit()
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

@app.route('/<mix_name>/song/<int:song_id>/<action>/', endpoint="song_edit", methods=["GET", "POST"])
@app.route('/<mix_name>/song/create', methods=["POST"])
def song_add(mix_name, action="create", song_id=None):
    if not session.get("logged_in"):
        abort(401)
    if action == "delete":
        cursor = g.db.execute("select title, artist from song where id = ?", [song_id])
        title, artist = cursor.fetchone()
        file_name = u"song_{0}_{1}.mp3".format(artist.replace(" ", "_").lower(), title.replace(" ", "_").lower())
        song_file = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        try:
            os.remove(song_file)
        except OSError:
            pass
        cursor = g.db.execute("delete from song where id=?", [song_id])
        flash_msg = "Song deleted."
    elif action == "edit":
        if request.is_xhr:
            cursor = g.db.execute("update song set position=? where id=?",
                      [request.form["position"], song_id])
            g.db.commit()
            return jsonify({"success": True})
        cursor = g.db.execute("update song set title=?, artist=? where id=?",
                  [request.form["title"], request.form["artist"], request.form["id"]])
        flash_msg = "Song edited."
    else:
        cursor = g.db.execute("select count(*) from song, mix where " \
                                "mix.name=? and mix.id = song.mix;", [mix_name])
        next_track_position = int(cursor.fetchone()[0]) + 1
        cursor = g.db.execute("insert into song (title, artist, position, mix) values (?, ?, ?, ?)",
                  [request.form["title"], request.form["artist"],
                  next_track_position, request.form["mix"]])
        flash_msg = "New song added"
    g.db.commit()
    if action != "delete":
        file = request.files['file']
        title = request.form["title"].replace(" ", "_").lower()
        artist = request.form["artist"].replace(" ", "_").lower()
        if file and allowed_file(file.filename):
            new_file_name = u"song_{0}_{1}.mp3".format(artist, title)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_file_name.encode('utf-8')))
        flash(flash_msg)
    return redirect(url_for('show_mix', mix_name=mix_name))


'''

    The Login/out Views!
    
'''
'''Login'''
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        '''try to find user'''
        cur = g.db.execute("select id, password from user where email = ?", [request.form["username"].lower()])
        user = cur.fetchone()
        if not user:
            error = "Invalid username"
        elif not check_password_hash(user[1], request.form["password"]):
            error = "Invalid password"
        else:
            session["logged_in"] = True
            session["user_id"] = user[0]
            flash("You were logged in")
            return redirect(url_for("all_mixes"))
    return render_template("login.html", error=error)

'''Logout'''
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("user_id", None)
    flash("You were logged out")
    return redirect(url_for("all_mixes"))


'''

    Run the file!
    
'''
if __name__ == '__main__':
  app.run()