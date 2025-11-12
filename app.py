from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, jsonify, abort
import os, sqlite3, time, uuid
from datetime import datetime
from slugify import slugify
from pathlib import Path

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "app.db"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY,
        filename TEXT,
        caption TEXT,
        tags TEXT,
        created_at TEXT
    );
    """)
    db.commit()
    db.close()
init_db()

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        rows = db.execute(
            "SELECT * FROM images WHERE caption LIKE ? OR tags LIKE ? ORDER BY id DESC",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM images ORDER BY id DESC").fetchall()
    db.close()
    return render_template_string("""
    <h1>Kirk Archive</h1>
    <form method="get">
        <input name="q" placeholder="Search for kirk..." value="{{q}}">
        <button type="submit">Search</button>
    </form>
    <form method="post" action="/upload" enctype="multipart/form-data">
        <input type="file" name="image" required>
        <input name="caption" placeholder="Caption">
        <input name="tags" placeholder="Tags (comma-separated)">
        <button type="submit">Upload</button>
    </form>
    <hr>
    {% for im in images %}
        <div>
            <img src="/uploads/{{im['filename']}}" width="250"><br>
            <b>{{im['caption']}}</b><br>
            Tags: {{im['tags']}}<br><br>
        </div>
    {% endfor %}
    """, images=rows, q=q)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")
    if not file or not allowed_file(file.filename):
        abort(400, "Invalid file.")
    filename = slugify(file.filename.rsplit('.', 1)[0]) + "-" + uuid.uuid4().hex[:8] + "." + file.filename.rsplit('.', 1)[1]
    file.save(UPLOAD_DIR / filename)
    caption = request.form.get("caption", "")
    tags = request.form.get("tags", "")
    db = get_db()
    db.execute("INSERT INTO images(filename, caption, tags, created_at) VALUES(?,?,?,?)",
               (filename, caption, tags, datetime.utcnow().isoformat()))
    db.commit()
    db.close()
    return redirect(url_for("index"))

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": time.time()})

if __name__ == "__main__":
    app.run(debug=True)
