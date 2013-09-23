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

    The Views!
    
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
@app.route("/<action>/", methods=["POST"])
def mix_action(action, mix_name=None):
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
    elif action == "create":
        # raise Exception(request.form["name"])
        cursor = g.db.execute("insert into mix (name, date, description, user) values (?, ?, ?, ?)",
                          [request.form["name"], str(datetime.datetime.now()),
                          request.form["description"], session.get("user_id")])
        flash_msg = "New mix successfully added."
    else:
        return redirect(url_for("all_mixes"))
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