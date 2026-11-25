import os
import sqlite3
import uuid
import io
import secrets

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))

DB = os.path.join(
    "/tmp" if os.environ.get("VERCEL") else BASE,
    "messages.db"
)

app = Flask(__name__, template_folder=BASE, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

TYPES = {
    "birthday": "عيد ميلاد 🎂",
    "thanks": "شكر 💜",
    "success": "نجاح وتخرج 🎓",
    "blame": "عتاب 💌",
    "appreciation": "تقدير ❤️",
    "other": "رسالة أخرى ✨"
}


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def get_columns(db):
    return {
        row["name"]: row
        for row in db.execute("PRAGMA table_info(messages)").fetchall()
    }


def init_db():
    db = connect()

    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            recipient TEXT,
            title TEXT,
            content TEXT,
            message_type TEXT,
            image BLOB,
            image_type TEXT,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    columns = get_columns(db)

    required_columns = {
        "recipient": "TEXT",
        "title": "TEXT",
        "content": "TEXT",
        "message_type": "TEXT",
        "image": "BLOB",
        "image_type": "TEXT",
        "image_data": "BLOB",
        "image_mime": "TEXT",
        "password": "TEXT",
        "password_hash": "TEXT",
        "created_at": "TIMESTAMP"
    }

    for column, data_type in required_columns.items():
        if column not in columns:
            db.execute(
                f"ALTER TABLE messages ADD COLUMN {column} {data_type}"
            )

    db.commit()
    db.close()


def save_message(data):
    db = connect()
    columns = get_columns(db)

    values = {
        "id": data["id"],
        "recipient": data["recipient"],
        "receiver": data["recipient"],
        "title": data["title"],
        "content": data["content"],
        "message": data["content"],
        "message_type": data["message_type"],
        "type": data["message_type"],
        "image": data["image"],
        "image_data": data["image"],
        "image_type": data["image_type"],
        "image_mime": data["image_type"],
        "password": data["password"],
        "password_hash": data["password"],
        "created_at": None
    }

    insert_values = {}

    for column, info in columns.items():
        if column in values:
            value = values[column]

            if value is not None:
                insert_values[column] = value

            elif info["notnull"] and info["dflt_value"] is None:
                insert_values[column] = ""

        elif info["notnull"] and info["dflt_value"] is None:
            if column != "id":
                insert_values[column] = ""

    if "id" not in insert_values:
        insert_values["id"] = data["id"]

    names = list(insert_values.keys())
    placeholders = ", ".join(["?"] * len(names))
    column_names = ", ".join(f'"{name}"' for name in names)

    sql = f"""
        INSERT INTO messages ({column_names})
        VALUES ({placeholders})
    """

    db.execute(sql, [insert_values[name] for name in names])
    db.commit()
    db.close()


def get_image(msg):
    for key in ("image", "image_data"):
        if key in msg.keys() and msg[key]:
            return msg[key]

    return None


def get_image_type(msg):
    for key in ("image_type", "image_mime"):
        if key in msg.keys() and msg[key]:
            return msg[key]

    return "image/jpeg"


def get_message_content(msg):
    for key in ("content", "message"):
        if key in msg.keys() and msg[key]:
            return msg[key]

    return ""


def get_message_password(msg):
    for key in ("password", "password_hash"):
        if key in msg.keys() and msg[key]:
            return msg[key]

    return ""


@app.route("/style.css")
def css():
    return send_from_directory(BASE, "style.css")


@app.route("/script.js")
def js():
    return send_from_directory(BASE, "script.js")


@app.route("/")
def home():
    return render_template("index.html", page="home")


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":

        recipient = request.form.get("recipient", "").strip()
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        kind = request.form.get("kind", "")
        password = request.form.get("password", "")
        image = request.files.get("image")

        if not all([recipient, title, content, password, image, image.filename]):
            flash("من فضلك أكمل البيانات واختار الصورة.")
            return redirect(url_for("create"))

        if kind not in TYPES:
            flash("اختار نوع الرسالة.")
            return redirect(url_for("create"))

        if len(password) < 6:
            flash("كلمة المرور لازم تكون 6 أحرف على الأقل.")
            return redirect(url_for("create"))

        allowed = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }

        ext = image.filename.rsplit(".", 1)[-1].lower()

        if ext not in allowed:
            flash("اختار صورة JPG أو PNG أو WEBP.")
            return redirect(url_for("create"))

        image_data = image.read()

        if not image_data:
            flash("الصورة غير صالحة.")
            return redirect(url_for("create"))

        message_id = uuid.uuid4().hex

        data = {
            "id": message_id,
            "recipient": recipient,
            "title": title,
            "content": content,
            "message_type": kind,
            "image": image_data,
            "image_type": allowed[ext],
            "password": generate_password_hash(password)
        }

        try:
            save_message(data)
        except sqlite3.Error:
            app.logger.exception("Database save error")
            flash("حصل خطأ أثناء حفظ الرسالة. راجع قاعدة البيانات.")
            return redirect(url_for("create"))

        return render_template(
            "index.html",
            page="created",
            message_id=message_id
        )

    return render_template(
        "index.html",
        page="create",
        types=TYPES
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":

        query = request.form.get("query", "").strip()

        if not query:
            flash("اكتب اسم الشخص أو عنوان الرسالة.")
            return redirect(url_for("search"))

        db = connect()
        columns = get_columns(db)

        title_column = "title" if "title" in columns else None

        recipient_column = (
            "recipient" if "recipient" in columns
            else "receiver" if "receiver" in columns
            else None
        )

        conditions = []
        params = []

        if title_column:
            conditions.append(f'"{title_column}" LIKE ?')
            params.append("%" + query + "%")

        if recipient_column:
            conditions.append(f'"{recipient_column}" LIKE ?')
            params.append("%" + query + "%")

        if not conditions:
            db.close()
            flash("تعذر البحث في قاعدة البيانات.")
            return redirect(url_for("search"))

        sql = f"""
            SELECT * FROM messages
            WHERE {" OR ".join(conditions)}
            ORDER BY rowid DESC
        """

        results = db.execute(sql, params).fetchall()
        db.close()

        return render_template(
            "index.html",
            page="results",
            results=results,
            types=TYPES,
            query=query
        )

    return render_template("index.html", page="search")


@app.route("/image/<message_id>")
def image(message_id):
    db = connect()

    msg = db.execute(
        "SELECT * FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()

    db.close()

    if not msg:
        return "الصورة غير موجودة", 404

    image_data = get_image(msg)

    if not image_data:
        return "الصورة غير موجودة", 404

    return send_file(
        io.BytesIO(image_data),
        mimetype=get_image_type(msg)
    )


@app.route("/message/<message_id>", methods=["GET", "POST"])
def message(message_id):
    db = connect()

    msg = db.execute(
        "SELECT * FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()

    db.close()

    if not msg:
        flash("الرسالة غير موجودة.")
        return redirect(url_for("home"))

    saved_password = get_message_password(msg)
    content = get_message_content(msg)

    if request.method == "POST":
        entered_password = request.form.get("password", "")

        if saved_password and check_password_hash(
            saved_password, entered_password
        ):
            session.setdefault("unlocked", [])

            if message_id not in session["unlocked"]:
                session["unlocked"].append(message_id)

            session.modified = True

            return redirect(
                url_for("message", message_id=message_id)
            )

        flash("كلمة المرور غير صحيحة.")

    unlocked = message_id in session.get("unlocked", [])

    message_data = dict(msg)
    message_data["content"] = content

    return render_template(
        "index.html",
        page="message",
        msg=message_data,
        unlocked=unlocked,
        types=TYPES
    )


@app.errorhandler(413)
def too_large(error):
    flash("حجم الصورة أكبر من 5 ميجابايت.")
    return redirect(url_for("create"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)