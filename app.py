import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, url_for
)

app = Flask(__name__)

# =======================
# Config
# =======================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "kirkverse.db")

# Save uploads into /static/uploads so we can serve with url_for('static', ...)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "webm", "mov"}


# =======================
# Helpers
# =======================
def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def get_media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[1].lower()
    if ext in {"mp4", "webm", "mov"}:
        return "video"
    return "image"


def get_db():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # so we can use row["caption"]
    return conn


def init_db():
    """Create posts table if it doesn't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            caption TEXT,
            tags TEXT,
            media_type TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


# Call this once when app starts
init_db()


# =======================
# Routes
# =======================

@app.route("/", methods=["GET"])
def index():
    """TikTok-style feed + search."""
    q = request.args.get("q", "").strip()
    conn = get_db()
    cur = conn.cursor()

    if q:
        cur.execute(
            """
            SELECT id, filename, caption, tags, media_type, created_at
            FROM posts
            WHERE caption LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC
            """,
            (f"%{q}%", f"%{q}%"),
        )
    else:
        cur.execute(
            """
            SELECT id, filename, caption, tags, media_type, created_at
            FROM posts
            ORDER BY created_at DESC
            """
        )

    posts = cur.fetchall()
    conn.close()

    # posts is a list of rows; in template we can do post["caption"], etc.
    return render_template("index.html", posts=posts, query=q)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle file upload + save to DB."""
    file = request.files.get("file")
    caption = request.form.get("caption", "").strip()
    tags = request.form.get("tags", "").strip()

    if not file or file.filename == "":
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        # For now just redirect; you can show a flash message later
        return redirect(url_for("index"))

    # Make filename safe & unique
    original_name = file.filename
    name, ext = os.path.splitext(original_name)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    safe_filename = f"{name}_{timestamp}{ext}"
    safe_filename = safe_filename.replace(" ", "_")

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
    file.save(save_path)

    media_type = get_media_type(safe_filename)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO posts (filename, caption, tags, media_type, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (safe_filename, caption, tags, media_type, datetime.utcnow()),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


# Simple health check (useful for Render)
@app.route("/health")
def health():
    return "ok", 200


# =======================
# Main
# =======================
if __name__ == "__main__":
    # For local dev
    app.run(debug=True, host="0.0.0.0", port=5000)
