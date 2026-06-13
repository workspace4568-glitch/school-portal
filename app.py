import os, uuid, json
from datetime import datetime, date
from flask import Flask, request, jsonify, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

try:
    import psycopg2  # noqa
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "pca-fixed-secret-key-2024"

raw_url = os.environ.get("DATABASE_URL", "sqlite:///school.db")
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))

if raw_url.startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True, "pool_recycle": 300,
    }
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin2024")

# ─── MODELS ────────────────────────────────────────────────────────────────

class Setting(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)

class Teacher(db.Model):
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    staff_id      = db.Column(db.String(20), unique=True)
    first_name    = db.Column(db.String(100), nullable=False)
    last_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(200))
    phone         = db.Column(db.String(30))
    qualification = db.Column(db.String(200))
    bio           = db.Column(db.Text)
    photo         = db.Column(db.Text)          # base64
    visible       = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

class Class(db.Model):
    id              = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name            = db.Column(db.String(50), nullable=False)   # e.g. JSS1A
    level           = db.Column(db.String(50))                   # e.g. Junior Secondary
    form_teacher_id = db.Column(db.String(36), db.ForeignKey("teacher.id"), nullable=True)
    form_teacher    = db.relationship("Teacher", backref="form_classes")
    students        = db.relationship("Student", backref="class_", lazy=True)
    subjects        = db.relationship("Subject", backref="class_", lazy=True, cascade="all,delete-orphan")

class Subject(db.Model):
    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = db.Column(db.String(100), nullable=False)
    class_id   = db.Column(db.String(36), db.ForeignKey("class.id"), nullable=False)
    teacher_id = db.Column(db.String(36), db.ForeignKey("teacher.id"), nullable=True)
    teacher    = db.relationship("Teacher", backref="subjects")
    max_ca     = db.Column(db.Integer, default=40)
    max_exam   = db.Column(db.Integer, default=60)

class Student(db.Model):
    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_code = db.Column(db.String(30), unique=True, nullable=False)
    first_name   = db.Column(db.String(100), nullable=False)
    last_name    = db.Column(db.String(100), nullable=False)
    other_name   = db.Column(db.String(100))
    class_id     = db.Column(db.String(36), db.ForeignKey("class.id"), nullable=True)
    gender       = db.Column(db.String(10))
    dob          = db.Column(db.String(20))
    parent_name  = db.Column(db.String(200))
    parent_phone = db.Column(db.String(30))
    parent_email = db.Column(db.String(200))
    address      = db.Column(db.Text)
    photo        = db.Column(db.Text)
    status       = db.Column(db.String(20), default="active")  # active/inactive/graduated
    enrolled_year= db.Column(db.Integer, default=lambda: datetime.utcnow().year)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    results      = db.relationship("Result", backref="student", lazy=True, cascade="all,delete-orphan")
    attendances  = db.relationship("Attendance", backref="student", lazy=True, cascade="all,delete-orphan")
    payments     = db.relationship("FeePayment", backref="student", lazy=True, cascade="all,delete-orphan")

class Attendance(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(36), db.ForeignKey("student.id"), nullable=False)
    date       = db.Column(db.String(20), nullable=False)
    status     = db.Column(db.String(20), default="present")   # present/absent/late

class Result(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.String(36), db.ForeignKey("student.id"), nullable=False)
    subject_id    = db.Column(db.String(36), db.ForeignKey("subject.id"), nullable=False)
    term          = db.Column(db.Integer, nullable=False)        # 1, 2, 3
    academic_year = db.Column(db.String(20), nullable=False)     # e.g. 2024/2025
    ca_score      = db.Column(db.Float, default=0)
    exam_score    = db.Column(db.Float, default=0)
    total         = db.Column(db.Float, default=0)
    grade         = db.Column(db.String(5))
    remark        = db.Column(db.String(50))
    subject       = db.relationship("Subject", backref="results")

class FeeType(db.Model):
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = db.Column(db.String(100), nullable=False)
    amount        = db.Column(db.Float, nullable=False)
    term          = db.Column(db.Integer)
    academic_year = db.Column(db.String(20))
    description   = db.Column(db.String(200))
    payments      = db.relationship("FeePayment", backref="fee_type", lazy=True)

class FeePayment(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.String(36), db.ForeignKey("student.id"), nullable=False)
    fee_type_id    = db.Column(db.String(36), db.ForeignKey("fee_type.id"), nullable=False)
    amount_paid    = db.Column(db.Float, nullable=False)
    date_paid      = db.Column(db.String(20), default=lambda: date.today().isoformat())
    payment_method = db.Column(db.String(50), default="cash")
    receipt_no     = db.Column(db.String(50))
    note           = db.Column(db.String(200))

class SubjectTemplate(db.Model):
    """Global subject catalogue — defines subjects school-wide."""
    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name        = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(200))
    default_ca  = db.Column(db.Integer, default=40)
    default_exam= db.Column(db.Integer, default=60)
    sort_order  = db.Column(db.Integer, default=0)

class Announcement(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    category    = db.Column(db.String(50), default="General")
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    published   = db.Column(db.Boolean, default=True)
    pinned      = db.Column(db.Boolean, default=False)

class Download(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    category      = db.Column(db.String(50), default="General")
    file_name     = db.Column(db.String(200))
    file_data     = db.Column(db.Text)    # base64
    file_type     = db.Column(db.String(50))
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    published     = db.Column(db.Boolean, default=True)

# ─── DEFAULT SETTINGS ──────────────────────────────────────────────────────

def _auto_academic_year():
    """Auto-generate academic year e.g. 2026/2027 based on today's date.
    Assumes new academic year starts in September (adjust month if needed)."""
    now = datetime.utcnow()
    start = now.year if now.month >= 9 else now.year - 1
    return f"{start}/{start + 1}"


DEFAULT_SETTINGS = {
    "school_name":     "Proper Child Academy",
    "school_short":    "PCA",
    "school_motto":    "Excellence in Learning",
    "address":         "123 School Road, Lagos",
    "phone":           "+234 800 000 0000",
    "email":           "info@properchildacademy.edu.ng",
    "website":         "",
    "logo":            "",
    "current_term":    "1",
    "current_year":    _auto_academic_year(),
    "theme_primary":   "#1E3A5F",
    "theme_accent":    "#F59E0B",
    "theme_bg":        "#F4F6FA",
    "theme_card":      "#FFFFFF",
    "theme_preset":    "classic",
    "color_scheme":    "royal-blue",
    # Appearance
    "sidebar_dark":    "1",
    "border_radius":   "8",
    "theme_text":      "#0F1520",
    "theme_sub":       "#4B5563",
    "theme_muted":     "#9CA3AF",
}

# ─── HELPERS ───────────────────────────────────────────────────────────────

def get_setting(key):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else DEFAULT_SETTINGS.get(key, "")

def set_setting(key, value):
    s = Setting.query.filter_by(key=key).first()
    if s: s.value = value
    else: db.session.add(Setting(key=key, value=str(value) if value is not None else ""))

def require_admin():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    return None

def calculate_grade(total):
    if total >= 75: return ("A1", "Excellent")
    elif total >= 70: return ("B2", "Very Good")
    elif total >= 65: return ("B3", "Good")
    elif total >= 60: return ("C4", "Credit")
    elif total >= 55: return ("C5", "Credit")
    elif total >= 50: return ("C6", "Credit")
    elif total >= 45: return ("D7", "Pass")
    elif total >= 40: return ("E8", "Pass")
    else: return ("F9", "Fail")

def generate_student_code():
    short = get_setting("school_short") or "PCA"
    year  = str(datetime.utcnow().year)
    prefix = f"{short}{year}"
    count = Student.query.filter(Student.student_code.like(f"{prefix}%")).count()
    return f"{prefix}{str(count + 1).zfill(4)}"

def generate_staff_id():
    count = Teacher.query.count()
    return f"STF{str(count + 1).zfill(4)}"

def generate_receipt_no():
    count = FeePayment.query.count()
    return f"RCP{datetime.utcnow().year}{str(count + 1).zfill(5)}"

def student_dict(s, include_class=True):
    d = {
        "id": s.id, "student_code": s.student_code,
        "first_name": s.first_name, "last_name": s.last_name,
        "other_name": s.other_name or "",
        "full_name": f"{s.first_name} {s.last_name}",
        "gender": s.gender or "", "dob": s.dob or "",
        "parent_name": s.parent_name or "", "parent_phone": s.parent_phone or "",
        "parent_email": s.parent_email or "", "address": s.address or "",
        "photo": s.photo or "", "status": s.status,
        "enrolled_year": s.enrolled_year, "class_id": s.class_id or "",
    }
    if include_class and s.class_id:
        cls = db.session.get(Class, s.class_id)
        d["class_name"] = cls.name if cls else ""
    else:
        d["class_name"] = ""
    return d

def teacher_dict(t):
    return {
        "id": t.id, "staff_id": t.staff_id or "",
        "first_name": t.first_name, "last_name": t.last_name,
        "full_name": f"{t.first_name} {t.last_name}",
        "email": t.email or "", "phone": t.phone or "",
        "qualification": t.qualification or "", "bio": t.bio or "",
        "photo": t.photo or "", "visible": t.visible,
    }

def class_dict(c):
    return {
        "id": c.id, "name": c.name, "level": c.level or "",
        "form_teacher_id": c.form_teacher_id or "",
        "form_teacher": f"{c.form_teacher.first_name} {c.form_teacher.last_name}" if c.form_teacher else "",
        "student_count": len(c.students),
        "subject_count": len(c.subjects),
        "subjects": [{"id": s.id, "name": s.name, "max_ca": s.max_ca, "max_exam": s.max_exam,
                       "teacher_id": s.teacher_id or "",
                       "teacher": f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else ""}
                     for s in c.subjects],
    }

def result_dict(r):
    return {
        "id": r.id, "student_id": r.student_id,
        "subject_id": r.subject_id,
        "subject_name": r.subject.name if r.subject else "",
        "term": r.term, "academic_year": r.academic_year,
        "ca_score": r.ca_score, "exam_score": r.exam_score,
        "total": r.total, "grade": r.grade or "", "remark": r.remark or "",
        "max_ca": r.subject.max_ca if r.subject else 40,
        "max_exam": r.subject.max_exam if r.subject else 60,
    }

def get_class_positions(class_id, term, academic_year):
    students = Student.query.filter_by(class_id=class_id, status="active").all()
    data = []
    for s in students:
        results = Result.query.filter_by(student_id=s.id, term=term, academic_year=academic_year).all()
        if results:
            total_score = sum(r.total or 0 for r in results)
            subj_count = len(results)
            avg = round(total_score / subj_count, 1) if subj_count else 0
            data.append({"student_id": s.id, "total": total_score, "avg": avg, "count": subj_count})
    data.sort(key=lambda x: x["total"], reverse=True)
    return {d["student_id"]: {"position": i + 1, "out_of": len(data), "total": d["total"], "avg": d["avg"]} for i, d in enumerate(data)}

# ─── DB INIT ───────────────────────────────────────────────────────────────

def initialize_db():
    try:
        db.create_all()
    except Exception as e:
        print(f"[init] create_all: {e}")
    try:
        for key, value in DEFAULT_SETTINGS.items():
            if not Setting.query.filter_by(key=key).first():
                db.session.add(Setting(key=key, value=value))
        db.session.commit()
        print("[init] Database ready")
    except Exception as e:
        db.session.rollback()
        print(f"[init] seed error: {e}")

with app.app_context():
    initialize_db()

# ─── FRONTEND ──────────────────────────────────────────────────────────────

def _serve_html():
    """Serve index.html directly — bypasses Jinja2 completely.
    No template syntax errors possible since file is read raw."""
    import os
    path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    return Response(html, status=200, mimetype="text/html")

@app.route("/")
def index(): return _serve_html()

@app.route("/admin")
def admin(): return _serve_html()

@app.route("/results")
def results(): return _serve_html()

@app.route("/health")
def health(): return jsonify({"status": "ok"}), 200

# ─── SETTINGS ──────────────────────────────────────────────────────────────

@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    return jsonify({k: get_setting(k) for k in DEFAULT_SETTINGS})

@app.route("/api/settings", methods=["POST"])
def api_settings_post():
    err = require_admin(); 
    if err: return err
    for key, val in (request.json or {}).items():
        set_setting(key, val)
    db.session.commit()
    return jsonify({"success": True})

# ─── ADMIN AUTH ────────────────────────────────────────────────────────────

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    if (request.json or {}).get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success": True})
    return jsonify({"error": "Invalid password"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("admin", None)
    return jsonify({"success": True})

@app.route("/api/admin/check")
def api_admin_check():
    return jsonify({"admin": bool(session.get("admin"))})

# ─── TEACHERS ──────────────────────────────────────────────────────────────

@app.route("/api/teachers", methods=["GET"])
def api_teachers_get():
    teachers = Teacher.query.order_by(Teacher.last_name).all()
    return jsonify([teacher_dict(t) for t in teachers])

@app.route("/api/teachers/public", methods=["GET"])
def api_teachers_public():
    teachers = Teacher.query.filter_by(visible=True).order_by(Teacher.last_name).all()
    return jsonify([teacher_dict(t) for t in teachers])

@app.route("/api/teachers", methods=["POST"])
def api_teacher_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    t = Teacher(
        staff_id=d.get("staff_id") or generate_staff_id(),
        first_name=d["first_name"], last_name=d["last_name"],
        email=d.get("email",""), phone=d.get("phone",""),
        qualification=d.get("qualification",""), bio=d.get("bio",""),
        photo=d.get("photo",""), visible=d.get("visible", True)
    )
    db.session.add(t); db.session.commit()
    return jsonify(teacher_dict(t)), 201

@app.route("/api/teachers/<tid>", methods=["PUT"])
def api_teacher_update(tid):
    err = require_admin();
    if err: return err
    t = db.session.get(Teacher, tid)
    if not t: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    for f in ["first_name","last_name","email","phone","qualification","bio","visible","staff_id"]:
        if f in d: setattr(t, f, d[f])
    if "photo" in d: t.photo = d["photo"]
    db.session.commit()
    return jsonify(teacher_dict(t))

@app.route("/api/teachers/<tid>", methods=["DELETE"])
def api_teacher_delete(tid):
    err = require_admin();
    if err: return err
    t = db.session.get(Teacher, tid)
    if not t: return jsonify({"error": "Not found"}), 404
    db.session.delete(t); db.session.commit()
    return jsonify({"success": True})

# ─── CLASSES ───────────────────────────────────────────────────────────────

@app.route("/api/classes", methods=["GET"])
def api_classes_get():
    classes = Class.query.order_by(Class.name).all()
    return jsonify([class_dict(c) for c in classes])

@app.route("/api/classes", methods=["POST"])
def api_class_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    c = Class(name=d["name"], level=d.get("level",""),
              form_teacher_id=d.get("form_teacher_id") or None)
    db.session.add(c); db.session.commit()
    return jsonify(class_dict(c)), 201

@app.route("/api/classes/<cid>", methods=["PUT"])
def api_class_update(cid):
    err = require_admin();
    if err: return err
    c = db.session.get(Class, cid)
    if not c: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    if "name" in d: c.name = d["name"]
    if "level" in d: c.level = d["level"]
    if "form_teacher_id" in d: c.form_teacher_id = d["form_teacher_id"] or None
    db.session.commit()
    return jsonify(class_dict(c))

@app.route("/api/classes/<cid>", methods=["DELETE"])
def api_class_delete(cid):
    err = require_admin();
    if err: return err
    c = db.session.get(Class, cid)
    if not c: return jsonify({"error": "Not found"}), 404
    db.session.delete(c); db.session.commit()
    return jsonify({"success": True})

# ─── SUBJECTS ──────────────────────────────────────────────────────────────

@app.route("/api/subjects", methods=["POST"])
def api_subject_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    s = Subject(name=d["name"], class_id=d["class_id"],
                teacher_id=d.get("teacher_id") or None,
                max_ca=int(d.get("max_ca", 40)), max_exam=int(d.get("max_exam", 60)))
    db.session.add(s); db.session.commit()
    return jsonify({"id": s.id, "name": s.name, "class_id": s.class_id,
                    "max_ca": s.max_ca, "max_exam": s.max_exam,
                    "teacher_id": s.teacher_id or "",
                    "teacher": f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else ""}), 201

@app.route("/api/subjects/<sid>", methods=["PUT"])
def api_subject_update(sid):
    err = require_admin();
    if err: return err
    s = db.session.get(Subject, sid)
    if not s: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    if "name" in d: s.name = d["name"]
    if "teacher_id" in d: s.teacher_id = d["teacher_id"] or None
    if "max_ca" in d: s.max_ca = int(d["max_ca"])
    if "max_exam" in d: s.max_exam = int(d["max_exam"])
    db.session.commit()
    return jsonify({"id": s.id, "name": s.name, "teacher_id": s.teacher_id or "",
                    "max_ca": s.max_ca, "max_exam": s.max_exam,
                    "teacher": f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else ""})

@app.route("/api/subjects/<sid>", methods=["DELETE"])
def api_subject_delete(sid):
    err = require_admin();
    if err: return err
    s = db.session.get(Subject, sid)
    if not s: return jsonify({"error": "Not found"}), 404
    Result.query.filter_by(subject_id=sid).delete()
    db.session.delete(s); db.session.commit()
    return jsonify({"success": True})

# ─── SUBJECT TEMPLATES ─────────────────────────────────────────────────────

@app.route("/api/subject-templates", methods=["GET"])
def api_subject_templates_get():
    items = SubjectTemplate.query.order_by(SubjectTemplate.sort_order, SubjectTemplate.name).all()
    return jsonify([{"id": t.id, "name": t.name, "description": t.description or "",
                     "default_ca": t.default_ca, "default_exam": t.default_exam} for t in items])

@app.route("/api/subject-templates", methods=["POST"])
def api_subject_template_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    if not d.get("name"): return jsonify({"error": "Name required"}), 400
    existing = SubjectTemplate.query.filter_by(name=d["name"].strip()).first()
    if existing: return jsonify({"error": "Subject already exists"}), 409
    count = SubjectTemplate.query.count()
    t = SubjectTemplate(name=d["name"].strip(), description=d.get("description", ""),
                        default_ca=int(d.get("default_ca", 40)),
                        default_exam=int(d.get("default_exam", 60)),
                        sort_order=count)
    db.session.add(t); db.session.commit()
    return jsonify({"id": t.id, "name": t.name, "description": t.description,
                    "default_ca": t.default_ca, "default_exam": t.default_exam}), 201

@app.route("/api/subject-templates/<tid>", methods=["PUT"])
def api_subject_template_update(tid):
    err = require_admin();
    if err: return err
    t = db.session.get(SubjectTemplate, tid)
    if not t: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    if "name" in d: t.name = d["name"].strip()
    if "description" in d: t.description = d["description"]
    if "default_ca" in d: t.default_ca = int(d["default_ca"])
    if "default_exam" in d: t.default_exam = int(d["default_exam"])
    db.session.commit()
    return jsonify({"id": t.id, "name": t.name, "description": t.description,
                    "default_ca": t.default_ca, "default_exam": t.default_exam})

@app.route("/api/subject-templates/<tid>", methods=["DELETE"])
def api_subject_template_delete(tid):
    err = require_admin();
    if err: return err
    t = db.session.get(SubjectTemplate, tid)
    if not t: return jsonify({"error": "Not found"}), 404
    db.session.delete(t); db.session.commit()
    return jsonify({"success": True})

@app.route("/api/subject-templates/<tid>/assign", methods=["POST"])
def api_subject_template_assign(tid):
    """Assign this subject template to one or more classes."""
    err = require_admin();
    if err: return err
    t = db.session.get(SubjectTemplate, tid)
    if not t: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    class_ids = d.get("class_ids", [])
    teacher_id = d.get("teacher_id") or None
    created = []
    for cid in class_ids:
        c = db.session.get(Class, cid)
        if not c: continue
        # Check if subject with same name already exists in this class
        exists = Subject.query.filter_by(class_id=cid, name=t.name).first()
        if not exists:
            s = Subject(name=t.name, class_id=cid, teacher_id=teacher_id,
                        max_ca=t.default_ca, max_exam=t.default_exam)
            db.session.add(s)
            created.append(cid)
    db.session.commit()
    return jsonify({"success": True, "assigned": len(created), "skipped": len(class_ids) - len(created)})

# ─── STUDENTS ──────────────────────────────────────────────────────────────

@app.route("/api/students", methods=["GET"])
def api_students_get():
    class_id = request.args.get("class_id")
    status   = request.args.get("status", "active")
    q = Student.query
    if class_id: q = q.filter_by(class_id=class_id)
    if status != "all": q = q.filter_by(status=status)
    students = q.order_by(Student.last_name).all()
    return jsonify([student_dict(s) for s in students])

@app.route("/api/students", methods=["POST"])
def api_student_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    s = Student(
        student_code=generate_student_code(),
        first_name=d["first_name"], last_name=d["last_name"],
        other_name=d.get("other_name",""),
        class_id=d.get("class_id") or None,
        gender=d.get("gender",""), dob=d.get("dob",""),
        parent_name=d.get("parent_name",""), parent_phone=d.get("parent_phone",""),
        parent_email=d.get("parent_email",""), address=d.get("address",""),
        photo=d.get("photo",""), status=d.get("status","active"),
        enrolled_year=d.get("enrolled_year", datetime.utcnow().year),
    )
    db.session.add(s); db.session.commit()
    return jsonify(student_dict(s)), 201

@app.route("/api/students/<sid>", methods=["GET"])
def api_student_get(sid):
    s = Student.query.filter_by(student_code=sid).first() or db.session.get(Student, sid)
    if not s: return jsonify({"error": "Not found"}), 404
    return jsonify(student_dict(s))

@app.route("/api/students/<sid>", methods=["PUT"])
def api_student_update(sid):
    err = require_admin();
    if err: return err
    s = db.session.get(Student, sid)
    if not s: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    for f in ["first_name","last_name","other_name","gender","dob","parent_name",
              "parent_phone","parent_email","address","status","enrolled_year"]:
        if f in d: setattr(s, f, d[f])
    if "class_id" in d: s.class_id = d["class_id"] or None
    if "photo" in d: s.photo = d["photo"]
    db.session.commit()
    return jsonify(student_dict(s))

@app.route("/api/students/<sid>", methods=["DELETE"])
def api_student_delete(sid):
    err = require_admin();
    if err: return err
    s = db.session.get(Student, sid)
    if not s: return jsonify({"error": "Not found"}), 404
    db.session.delete(s); db.session.commit()
    return jsonify({"success": True})

# ─── ATTENDANCE ────────────────────────────────────────────────────────────

@app.route("/api/attendance", methods=["GET"])
def api_attendance_get():
    class_id = request.args.get("class_id")
    date_str = request.args.get("date")
    q = Attendance.query
    if date_str: q = q.filter_by(date=date_str)
    if class_id:
        student_ids = [s.id for s in Student.query.filter_by(class_id=class_id).all()]
        q = q.filter(Attendance.student_id.in_(student_ids))
    records = q.all()
    return jsonify([{"id": r.id, "student_id": r.student_id, "date": r.date, "status": r.status} for r in records])

@app.route("/api/attendance", methods=["POST"])
def api_attendance_post():
    err = require_admin();
    if err: return err
    d = request.json or {}
    # Bulk save: [{student_id, date, status}]
    records = d.get("records", [])
    for rec in records:
        existing = Attendance.query.filter_by(student_id=rec["student_id"], date=rec["date"]).first()
        if existing:
            existing.status = rec["status"]
        else:
            db.session.add(Attendance(student_id=rec["student_id"], date=rec["date"], status=rec["status"]))
    db.session.commit()
    return jsonify({"success": True, "count": len(records)})

@app.route("/api/attendance/summary", methods=["GET"])
def api_attendance_summary():
    student_id = request.args.get("student_id")
    if not student_id: return jsonify({"error": "student_id required"}), 400
    records = Attendance.query.filter_by(student_id=student_id).all()
    present = sum(1 for r in records if r.status == "present")
    absent  = sum(1 for r in records if r.status == "absent")
    late    = sum(1 for r in records if r.status == "late")
    return jsonify({"total": len(records), "present": present, "absent": absent, "late": late,
                    "percent": round(present / len(records) * 100, 1) if records else 0})

# ─── RESULTS ───────────────────────────────────────────────────────────────

@app.route("/api/results", methods=["GET"])
def api_results_get():
    student_id    = request.args.get("student_id")
    class_id      = request.args.get("class_id")
    term          = request.args.get("term")
    academic_year = request.args.get("year")
    q = Result.query
    if student_id:    q = q.filter_by(student_id=student_id)
    if term:          q = q.filter_by(term=int(term))
    if academic_year: q = q.filter_by(academic_year=academic_year)
    if class_id:
        student_ids = [s.id for s in Student.query.filter_by(class_id=class_id).all()]
        q = q.filter(Result.student_id.in_(student_ids))
    results = q.all()
    return jsonify([result_dict(r) for r in results])

@app.route("/api/results", methods=["POST"])
def api_results_post():
    err = require_admin();
    if err: return err
    d = request.json or {}
    records = d.get("records", [])
    saved = []
    for rec in records:
        existing = Result.query.filter_by(
            student_id=rec["student_id"], subject_id=rec["subject_id"],
            term=rec["term"], academic_year=rec["academic_year"]
        ).first()
        ca   = float(rec.get("ca_score", 0))
        exam = float(rec.get("exam_score", 0))
        total = round(ca + exam, 1)
        grade, remark = calculate_grade(total)
        if existing:
            existing.ca_score=ca; existing.exam_score=exam
            existing.total=total; existing.grade=grade; existing.remark=remark
            saved.append(existing)
        else:
            r = Result(student_id=rec["student_id"], subject_id=rec["subject_id"],
                       term=rec["term"], academic_year=rec["academic_year"],
                       ca_score=ca, exam_score=exam, total=total, grade=grade, remark=remark)
            db.session.add(r); saved.append(r)
    db.session.commit()
    return jsonify({"success": True, "count": len(saved)})

@app.route("/api/results/student/<code>", methods=["GET"])
def api_results_by_code(code):
    s = Student.query.filter_by(student_code=code.upper()).first()
    if not s: return jsonify({"error": "Student code not found"}), 404
    term          = request.args.get("term")
    academic_year = request.args.get("year") or get_setting("current_year")
    q = Result.query.filter_by(student_id=s.id, academic_year=academic_year)
    if term: q = q.filter_by(term=int(term))
    results = q.all()
    # Positions
    positions = {}
    if s.class_id:
        for t in set(r.term for r in results):
            positions.update(get_class_positions(s.class_id, t, academic_year))
    pos = positions.get(s.id, {})
    cls = db.session.get(Class, s.class_id) if s.class_id else None
    return jsonify({
        "student": student_dict(s),
        "class_name": cls.name if cls else "",
        "results": [result_dict(r) for r in results],
        "position": pos.get("position"), "out_of": pos.get("out_of"),
        "total_score": pos.get("total"), "average": pos.get("avg"),
        "school_name": get_setting("school_name"),
        "school_address": get_setting("address"),
        "current_year": academic_year,
        "term": term or get_setting("current_term"),
    })

# ─── FEES ──────────────────────────────────────────────────────────────────

@app.route("/api/fee-types", methods=["GET"])
def api_fee_types_get():
    fee_types = FeeType.query.order_by(FeeType.name).all()
    return jsonify([{"id": f.id, "name": f.name, "amount": f.amount,
                     "term": f.term, "academic_year": f.academic_year or "",
                     "description": f.description or ""} for f in fee_types])

@app.route("/api/fee-types", methods=["POST"])
def api_fee_type_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    f = FeeType(name=d["name"], amount=float(d["amount"]),
                term=d.get("term"), academic_year=d.get("academic_year",""),
                description=d.get("description",""))
    db.session.add(f); db.session.commit()
    return jsonify({"id": f.id, "name": f.name, "amount": f.amount}), 201

@app.route("/api/fee-types/<fid>", methods=["DELETE"])
def api_fee_type_delete(fid):
    err = require_admin();
    if err: return err
    f = db.session.get(FeeType, fid)
    if not f: return jsonify({"error": "Not found"}), 404
    db.session.delete(f); db.session.commit()
    return jsonify({"success": True})

@app.route("/api/payments", methods=["GET"])
def api_payments_get():
    student_id = request.args.get("student_id")
    q = FeePayment.query
    if student_id: q = q.filter_by(student_id=student_id)
    payments = q.order_by(FeePayment.date_paid.desc()).all()
    return jsonify([{
        "id": p.id, "student_id": p.student_id,
        "student": f"{p.student.first_name} {p.student.last_name}" if p.student else "",
        "student_code": p.student.student_code if p.student else "",
        "fee_type_id": p.fee_type_id, "fee_name": p.fee_type.name if p.fee_type else "",
        "amount_paid": p.amount_paid, "date_paid": p.date_paid,
        "payment_method": p.payment_method or "cash",
        "receipt_no": p.receipt_no or "", "note": p.note or "",
    } for p in payments])

@app.route("/api/payments", methods=["POST"])
def api_payment_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    p = FeePayment(
        student_id=d["student_id"], fee_type_id=d["fee_type_id"],
        amount_paid=float(d["amount_paid"]),
        date_paid=d.get("date_paid", date.today().isoformat()),
        payment_method=d.get("payment_method","cash"),
        receipt_no=d.get("receipt_no") or generate_receipt_no(),
        note=d.get("note","")
    )
    db.session.add(p); db.session.commit()
    return jsonify({"id": p.id, "receipt_no": p.receipt_no, "amount_paid": p.amount_paid}), 201

@app.route("/api/payments/<int:pid>", methods=["DELETE"])
def api_payment_delete(pid):
    err = require_admin();
    if err: return err
    p = db.session.get(FeePayment, pid)
    if not p: return jsonify({"error": "Not found"}), 404
    db.session.delete(p); db.session.commit()
    return jsonify({"success": True})

# ─── ANNOUNCEMENTS ─────────────────────────────────────────────────────────

@app.route("/api/announcements", methods=["GET"])
def api_announcements_get():
    public_only = request.args.get("public") == "1"
    q = Announcement.query
    if public_only: q = q.filter_by(published=True)
    anns = q.order_by(Announcement.pinned.desc(), Announcement.date_posted.desc()).all()
    return jsonify([{"id": a.id, "title": a.title, "content": a.content,
                     "category": a.category, "published": a.published,
                     "pinned": a.pinned,
                     "date_posted": a.date_posted.strftime("%b %d, %Y")} for a in anns])

@app.route("/api/announcements", methods=["POST"])
def api_announcement_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    a = Announcement(title=d["title"], content=d["content"],
                     category=d.get("category","General"),
                     published=d.get("published", True), pinned=d.get("pinned", False))
    db.session.add(a); db.session.commit()
    return jsonify({"id": a.id, "title": a.title, "category": a.category,
                    "published": a.published, "pinned": a.pinned,
                    "date_posted": a.date_posted.strftime("%b %d, %Y")}), 201

@app.route("/api/announcements/<int:aid>", methods=["PUT"])
def api_announcement_update(aid):
    err = require_admin();
    if err: return err
    a = db.session.get(Announcement, aid)
    if not a: return jsonify({"error": "Not found"}), 404
    d = request.json or {}
    for f in ["title","content","category","published","pinned"]:
        if f in d: setattr(a, f, d[f])
    db.session.commit()
    return jsonify({"success": True, "id": a.id, "title": a.title,
                    "published": a.published, "pinned": a.pinned,
                    "category": a.category, "date_posted": a.date_posted.strftime("%b %d, %Y")})

@app.route("/api/announcements/<int:aid>", methods=["DELETE"])
def api_announcement_delete(aid):
    err = require_admin();
    if err: return err
    a = db.session.get(Announcement, aid)
    if not a: return jsonify({"error": "Not found"}), 404
    db.session.delete(a); db.session.commit()
    return jsonify({"success": True})

# ─── DOWNLOADS ─────────────────────────────────────────────────────────────

@app.route("/api/downloads", methods=["GET"])
def api_downloads_get():
    public_only = request.args.get("public") == "1"
    q = Download.query
    if public_only: q = q.filter_by(published=True)
    items = q.order_by(Download.date_uploaded.desc()).all()
    return jsonify([{"id": i.id, "title": i.title, "category": i.category,
                     "file_name": i.file_name or "", "file_type": i.file_type or "",
                     "file_data": i.file_data or "", "published": i.published,
                     "date_uploaded": i.date_uploaded.strftime("%b %d, %Y")} for i in items])

@app.route("/api/downloads", methods=["POST"])
def api_download_create():
    err = require_admin();
    if err: return err
    d = request.json or {}
    i = Download(title=d["title"], category=d.get("category","General"),
                 file_name=d.get("file_name",""), file_type=d.get("file_type",""),
                 file_data=d.get("file_data",""), published=d.get("published",True))
    db.session.add(i); db.session.commit()
    return jsonify({"id": i.id, "title": i.title, "category": i.category,
                    "file_name": i.file_name, "published": i.published,
                    "date_uploaded": i.date_uploaded.strftime("%b %d, %Y")}), 201

@app.route("/api/downloads/<int:did>", methods=["DELETE"])
def api_download_delete(did):
    err = require_admin();
    if err: return err
    i = db.session.get(Download, did)
    if not i: return jsonify({"error": "Not found"}), 404
    db.session.delete(i); db.session.commit()
    return jsonify({"success": True})

# ─── REPORTS / STATS ───────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    err = require_admin();
    if err: return err
    return jsonify({
        "students":      Student.query.filter_by(status="active").count(),
        "teachers":      Teacher.query.count(),
        "classes":       Class.query.count(),
        "announcements": Announcement.query.filter_by(published=True).count(),
        "total_fees":    db.session.query(db.func.sum(FeePayment.amount_paid)).scalar() or 0,
    })

@app.route("/api/reports/class-list")
def api_report_class_list():
    err = require_admin();
    if err: return err
    class_id = request.args.get("class_id")
    cls = db.session.get(Class, class_id)
    if not cls: return jsonify({"error": "Class not found"}), 404
    students = Student.query.filter_by(class_id=class_id, status="active").order_by(Student.last_name).all()
    return jsonify({
        "class": class_dict(cls),
        "students": [student_dict(s) for s in students],
        "school_name": get_setting("school_name"),
        "generated": date.today().isoformat(),
    })

@app.route("/api/reports/grade-sheet")
def api_report_grade_sheet():
    err = require_admin();
    if err: return err
    class_id      = request.args.get("class_id")
    term          = int(request.args.get("term", get_setting("current_term") or 1))
    academic_year = request.args.get("year", get_setting("current_year"))
    cls = db.session.get(Class, class_id)
    if not cls: return jsonify({"error": "Class not found"}), 404
    students  = Student.query.filter_by(class_id=class_id, status="active").order_by(Student.last_name).all()
    subjects  = Subject.query.filter_by(class_id=class_id).order_by(Subject.name).all()
    positions = get_class_positions(class_id, term, academic_year)
    sheet = []
    for s in students:
        row = {"student": student_dict(s, include_class=False), "scores": {}}
        for subj in subjects:
            r = Result.query.filter_by(student_id=s.id, subject_id=subj.id, term=term, academic_year=academic_year).first()
            row["scores"][subj.id] = {"ca": r.ca_score if r else None, "exam": r.exam_score if r else None,
                                       "total": r.total if r else None, "grade": r.grade if r else None}
        pos = positions.get(s.id, {})
        row["position"] = pos.get("position"); row["avg"] = pos.get("avg"); row["total"] = pos.get("total")
        sheet.append(row)
    return jsonify({
        "class": class_dict(cls), "subjects": [{"id": s.id, "name": s.name} for s in subjects],
        "sheet": sheet, "term": term, "academic_year": academic_year,
        "school_name": get_setting("school_name"),
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG","0")=="1")
