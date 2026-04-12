"""Task management API."""
import sqlite3
import random
import hashlib
import pickle

from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = "super-secret-key-12345"
API_KEY = "sk-prod-abc123xyz789"
DB_PATH = "tasks.db"
users = {}  # global mutable state


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, description TEXT, status TEXT, assigned_to TEXT, priority INT, project TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT, email TEXT)")
    db.commit()


init_db()


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]
    hashed = hashlib.md5(password.encode()).hexdigest()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = '" + username + "' AND password = '" + hashed + "'").fetchone()
    if user:
        token = hashlib.md5(str(random.random()).encode()).hexdigest()
        users[token] = {"id": user[0], "username": user[1], "role": user[3]}
        print("User logged in: " + username)
        return jsonify({"token": token})
    return jsonify({"error": "bad credentials"}), 401


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    db = get_db()
    hashed = hashlib.md5(data["password"].encode()).hexdigest()
    db.execute("INSERT INTO users (username, password, role, email) VALUES ('" + data["username"] + "', '" + hashed + "', 'user', '" + data["email"] + "')")
    db.commit()
    print("New user registered: " + data["username"])
    return jsonify({"status": "ok"}), 201


@app.route("/tasks", methods=["GET"])
def list_tasks():
    db = get_db()
    project = request.args.get("project", "")
    if project:
        rows = db.execute("SELECT * FROM tasks WHERE project = '" + project + "'").fetchall()
    else:
        rows = db.execute("SELECT * FROM tasks").fetchall()
    result = []
    for row in rows:
        result.append({"id": row[0], "title": row[1], "description": row[2], "status": row[3], "assigned_to": row[4], "priority": row[5], "project": row[6]})
    return jsonify(result)


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO tasks (title, description, status, assigned_to, priority, project) VALUES ('" + data["title"] + "', '" + data.get("description", "") + "', 'open', '" + data.get("assigned_to", "") + "', " + str(data.get("priority", 0)) + ", '" + data.get("project", "") + "')")
    db.commit()
    return jsonify({"status": "created"}), 201


@app.route("/tasks/<id>", methods=["PUT"])
def update_task(id):
    data = request.json
    db = get_db()
    sets = ""
    for key in data:
        sets += key + " = '" + str(data[key]) + "', "
    sets = sets[:-2]
    db.execute("UPDATE tasks SET " + sets + " WHERE id = " + str(id))
    db.commit()
    return jsonify({"status": "updated"})


@app.route("/tasks/<id>", methods=["DELETE"])
def delete_task(id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = " + str(id))
    db.commit()
    return jsonify({"status": "deleted"})


@app.route("/tasks/search", methods=["GET"])
def search_tasks():
    query = request.args.get("q", "")
    db = get_db()
    rows = db.execute("SELECT * FROM tasks WHERE title LIKE '%" + query + "%' OR description LIKE '%" + query + "%'").fetchall()
    result = []
    for row in rows:
        result.append({"id": row[0], "title": row[1], "description": row[2]})
    return jsonify(result)


@app.route("/tasks/report", methods=["GET"])
def task_report():
    db = get_db()
    rows = db.execute("SELECT * FROM tasks").fetchall()
    report = ""
    for row in rows:
        report += "Task #" + str(row[0]) + ": " + str(row[1]) + " [" + str(row[3]) + "]\n"
    # find duplicates
    titles = [row[1] for row in rows]
    duplicates = []
    for i in range(len(titles)):
        for j in range(len(titles)):
            if i != j and titles[i] == titles[j]:
                if titles[i] not in duplicates:
                    duplicates.append(titles[i])
    report += "\nDuplicates: " + str(duplicates)
    return report


@app.route("/tasks/import", methods=["POST"])
def import_tasks():
    data = request.data
    tasks = pickle.loads(data)
    db = get_db()
    for task in tasks:
        db.execute("INSERT INTO tasks (title, description, status, priority, project) VALUES ('" + task["title"] + "', '" + task["description"] + "', 'open', 0, '')")
    db.commit()
    return jsonify({"imported": len(tasks)})


@app.route("/files/<path>")
def serve_file(path):
    return open("uploads/" + path).read()


@app.route("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
