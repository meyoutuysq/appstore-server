import os
import json
import time
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

UPLOAD_DIR = "/storage/emulated/0/AppStore/uploads"
APPS_FILE = "/storage/emulated/0/AppStore/apps.json"
USERS_FILE = "/storage/emulated/0/AppStore/users.json"
CODES_FILE = "/storage/emulated/0/AppStore/codes.json"
COMMENTS_FILE = "/storage/emulated/0/AppStore/comments.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)

SMTP_HOST = "smtp.163.com"
SMTP_PORT = 465
SMTP_USER = "15539697298@163.com"
SMTP_PASS = "HSKNHGnQaPrTqzaE"


def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_title(user):
    email = user.get("email", "")
    role = user.get("role", "user")
    if email == "1771457782@qq.com":
        return "官方"
    if role == "admin":
        return "管理员"
    if role == "founder":
        return "创始人"
    if role == "developer":
        return "开发者"
    if role == "elder":
        return "元老"
    upload_count = user.get("upload_count", 0)
    comment_count = user.get("comment_count", 0)
    like_count = user.get("likes", 0)
    if upload_count >= 10:
        return "投稿大师"
    if like_count >= 50:
        return "点赞哥"
    if comment_count >= 30:
        return "热评达人"
    return "普通用户"


@app.route("/api/send_code", methods=["POST"])
def send_code():
    data = request.get_json()
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"success": False, "msg": "邮箱不能为空"})
    code = str(random.randint(100000, 999999))
    codes = load_json(CODES_FILE, {})
    codes[email] = {"code": code, "time": time.time()}
    save_json(CODES_FILE, codes)
    try:
        msg = MIMEText(f"【AppStore】您的验证码是：{code}，5分钟内有效。", "plain", "utf-8")
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg["Subject"] = "AppStore 登录验证码"
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, email, msg.as_string())
        server.quit()
        return jsonify({"success": True, "msg": "验证码已发送"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"发送失败: {str(e)}"})


@app.route("/api/code_login", methods=["POST"])
def code_login():
    data = request.get_json()
    email = data.get("email", "").strip()
    code = data.get("code", "").strip()
    if not email or not code:
        return jsonify({"success": False, "msg": "邮箱和验证码不能为空"})
    codes = load_json(CODES_FILE, {})
    record = codes.get(email)
    if not record:
        return jsonify({"success": False, "msg": "请先获取验证码"})
    if time.time() - record["time"] > 300:
        return jsonify({"success": False, "msg": "验证码已过期"})
    if record["code"] != code:
        return jsonify({"success": False, "msg": "验证码错误"})
    users = load_json(USERS_FILE, [])
    user = None
    for u in users:
        if u.get("email") == email:
            user = u
            break
    if user is None:
        user = {
            "id": len(users) + 1,
            "email": email,
            "username": email.split("@")[0],
            "password": "",
            "role": "user",
            "signature": "",
            "gender": "保密",
            "age": 0,
            "fans": 0,
            "follows": 0,
            "likes": 0,
            "upload_count": 0,
            "comment_count": 0,
            "register_date": time.strftime("%Y-%m-%d")
        }
        users.append(user)
        save_json(USERS_FILE, users)
    del codes[email]
    save_json(CODES_FILE, codes)
    return jsonify({"success": True, "msg": "登录成功", "user": user})


@app.route("/api/password_login", methods=["POST"])
def password_login():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"success": False, "msg": "邮箱和密码不能为空"})
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("email") == email and u.get("password") == password:
            return jsonify({"success": True, "msg": "登录成功", "user": u})
    return jsonify({"success": False, "msg": "邮箱或密码错误"})


@app.route("/api/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email", "").strip()
    code = data.get("code", "").strip()
    new_password = data.get("new_password", "").strip()
    if not email or not code or not new_password:
        return jsonify({"success": False, "msg": "参数不完整"})
    codes = load_json(CODES_FILE, {})
    record = codes.get(email)
    if not record or record["code"] != code or time.time() - record["time"] > 300:
        return jsonify({"success": False, "msg": "验证码错误或已过期"})
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("email") == email:
            u["password"] = new_password
            save_json(USERS_FILE, users)
            del codes[email]
            save_json(CODES_FILE, codes)
            return jsonify({"success": True, "msg": "密码重置成功"})
    return jsonify({"success": False, "msg": "用户不存在"})


@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    data = request.get_json()
    email = data.get("email", "").strip()
    username = data.get("username", "").strip()
    if not email or not username:
        return jsonify({"success": False, "msg": "参数不完整"})
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("email") == email:
            u["username"] = username
            save_json(USERS_FILE, users)
            return jsonify({"success": True, "msg": "更新成功"})
    return jsonify({"success": False, "msg": "用户不存在"})


@app.route("/api/user_info", methods=["POST"])
def user_info():
    data = request.get_json()
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"success": False, "msg": "邮箱不能为空"})
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("email") == email:
            return jsonify({"success": True, "user": u})
    return jsonify({"success": False, "msg": "用户不存在"})


@app.route("/api/user_profile/<email_or_id>")
def user_profile(email_or_id):
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("email") == email_or_id or str(u.get("id")) == email_or_id:
            u["register_date"] = u.get("register_date", "2026-05-01")
            u["signature"] = u.get("signature", "")
            u["gender"] = u.get("gender", "保密")
            u["age"] = u.get("age", 0)
            u["fans"] = u.get("fans", 0)
            u["follows"] = u.get("follows", 0)
            u["likes"] = u.get("likes", 0)
            u["title"] = get_user_title(u)
            return jsonify({"success": True, "profile": u})
    return jsonify({"success": False, "msg": "用户不存在"})


@app.route("/api/update_profile_detail", methods=["POST"])
def update_profile_detail():
    data = request.get_json()
    email = data.get("email", "")
    signature = data.get("signature", "")
    gender = data.get("gender", "保密")
    age = data.get("age", 0)
    users = load_json(USERS_FILE, [])
    for u in users:
        if u.get("email") == email:
            u["signature"] = signature
            u["gender"] = gender
            u["age"] = age
            save_json(USERS_FILE, users)
            return jsonify({"success": True, "msg": "更新成功"})
    return jsonify({"success": False, "msg": "用户不存在"})


@app.route("/api/apps")
def get_apps():
    apps = load_json(APPS_FILE, [])
    category = request.args.get("category", "")
    keyword = request.args.get("keyword", "")
    if category:
        apps = [a for a in apps if a.get("category") == category]
    if keyword:
        apps = [a for a in apps if keyword.lower() in a.get("name", "").lower()]
    apps.sort(key=lambda x: x.get("time", ""), reverse=True)
    return jsonify(apps)


@app.route("/api/categories")
def get_categories():
    apps = load_json(APPS_FILE, [])
    cats = list(set([a.get("category", "其他") for a in apps]))
    if not cats:
        cats = ["视频播放", "音乐播放", "文字阅读", "实用工具", "下载工具", "人工智能", "其他"]
    return jsonify(cats)


@app.route("/api/upload", methods=["POST"])
def upload_app():
    name = request.form.get("name", "")
    category = request.form.get("category", "其他")
    desc = request.form.get("desc", "")
    size = request.form.get("size", "未知")
    uploader = request.form.get("uploader", "匿名")
    version = request.form.get("version", "1.0")

    file = request.files.get("file")
    filename = ""
    if file:
        filename = f"{int(time.time())}_{file.filename}"
        file.save(os.path.join(UPLOAD_DIR, filename))

    icon_file = request.files.get("icon_file")
    icon_filename = ""
    if icon_file:
        icon_filename = f"{int(time.time())}_icon.png"
        icon_file.save(os.path.join(UPLOAD_DIR, icon_filename))

    screenshot_files = request.files.getlist("screenshots")
    screenshot_filenames = []
    for sf in screenshot_files:
        if sf.filename:
            sf_name = f"{int(time.time())}_screenshot.png"
            sf.save(os.path.join(UPLOAD_DIR, sf_name))
            screenshot_filenames.append(sf_name)

    apps = load_json(APPS_FILE, [])
    new_id = max([a.get("id", 0) for a in apps], default=0) + 1

    app_info = {
        "id": new_id,
        "name": name,
        "size": size,
        "category": category,
        "desc": desc,
        "filename": filename,
        "icon_file": icon_filename,
        "uploader": uploader,
        "version": version,
        "screenshots": screenshot_filenames,
        "time": time.strftime("%Y-%m-%d")
    }
    apps.insert(0, app_info)
    save_json(APPS_FILE, apps)
    return jsonify({"success": True, "app": app_info})


@app.route("/api/download/<filename>")
def download_file(filename):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "file not found"}), 404


@app.route("/api/icon/<filename>")
def get_icon(filename):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="image/png")
    return jsonify({"error": "not found"}), 404


@app.route("/api/screenshot/<filename>")
def get_screenshot(filename):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="image/png")
    return jsonify({"error": "not found"}), 404


@app.route("/api/comments/<int:app_id>")
def get_comments(app_id):
    comments = load_json(COMMENTS_FILE, {})
    app_comments = comments.get(str(app_id), [])
    return jsonify(app_comments)


@app.route("/api/add_comment", methods=["POST"])
def add_comment():
    data = request.get_json()
    app_id = data.get("app_id", "")
    user = data.get("user", "匿名")
    content = data.get("content", "")
    rating = data.get("rating", 0)
    if not app_id or not content:
        return jsonify({"success": False, "msg": "参数不完整"})
    comments = load_json(COMMENTS_FILE, {})
    app_comments = comments.get(str(app_id), [])
    comment = {
        "id": len(app_comments) + 1,
        "user": user,
        "content": content,
        "rating": rating,
        "time": time.strftime("%Y-%m-%d %H:%M")
    }
    app_comments.append(comment)
    comments[str(app_id)] = app_comments
    save_json(COMMENTS_FILE, comments)
    return jsonify({"success": True, "comment": comment})


if __name__ == "__main__":
    print("AppStore 后端启动!")
    print("地址: http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)