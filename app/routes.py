from __future__ import annotations
import json
from typing import Dict, Any, Optional
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
from . import config
from .db import db_conn, db_put, get_pool, find_ref
from .constants import FIELDS, EXPLAINS
from .parsing.ocr import extract_text_from_upload
from .parsing.parse import parse_lab_text_to_form
from psycopg2.extras import Json

app = Flask(__name__, template_folder="templates", static_folder=None)
app.secret_key = config.SECRET_KEY

# -------- helpers --------

def render_form(form: Dict[str, Any], exam_id: Optional[int]):
    return render_template(
        "form.html",
        title=config.APP_TITLE,
        APP_TITLE=config.APP_TITLE,
        fields=FIELDS,
        form=form,
        exam_id=exam_id
    )

def save_exam(exam_id: Optional[int]):
    patient_name = request.form.get("patient_name") or None
    sex = (request.form.get("sex") or "").upper() or None
    age_raw = request.form.get("age_years", "").strip()
    if not age_raw.isdigit():
        flash("Idade é obrigatória e deve ser um número inteiro (anos).")
        if exam_id:
            return redirect(url_for('edit_exam', exam_id=exam_id))
        return redirect(url_for('home'))
    age_years = int(age_raw)

    data: Dict[str, Any] = {}
    for _, key, _, _ in FIELDS:
        val = (request.form.get(f"f_{key}") or "").strip().replace(",", ".")
        if val == "":
            continue
        try:
            v = float(val)
        except ValueError:
            v = val
        data[key] = v

    conn = db_conn()
    try:
        with conn, conn.cursor() as cur:
            if exam_id is None:
                cur.execute("""
                    INSERT INTO exams (patient_name, sex, age_years, data, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,NOW(),NOW()) RETURNING id
                """, (patient_name, sex, age_years, Json(data)))
                new_id = cur.fetchone()[0]
                flash("Exame salvo!")
                return redirect(url_for('chart', exam_id=new_id))
            else:
                cur.execute("""
                    UPDATE exams SET patient_name=%s, sex=%s, age_years=%s, data=%s, updated_at=NOW()
                    WHERE id=%s
                """, (patient_name, sex, age_years, Json(data), exam_id))
                flash("Exame atualizado!")
                return redirect(url_for('chart', exam_id=exam_id))
    finally:
        db_put(conn)

# -------- rotas --------

@app.context_processor
def inject_base():
    return {"APP_TITLE": config.APP_TITLE}

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return save_exam(None)
    return render_form(form={}, exam_id=None)

@app.route("/edit/<int:exam_id>", methods=["GET", "POST"])
def edit_exam(exam_id: int):
    conn = db_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT id, patient_name, sex, age_years, data::text FROM exams WHERE id=%s", (exam_id,))
            row = cur.fetchone()
            if not row:
                flash("Exame não encontrado.")
                return redirect(url_for('list_exams'))
            if request.method == "POST":
                return save_exam(exam_id)
            data = json.loads(row[4])
            form = {"patient_name": row[1], "sex": row[2], "age_years": row[3]}
            form.update(data)
            return render_form(form=form, exam_id=exam_id)
    finally:
        db_put(conn)

@app.route("/exams")
def list_exams():
    conn = db_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, patient_name, age_years, created_at, updated_at
                FROM exams ORDER BY id DESC LIMIT 200
            """)
            items = [
                {
                    "id": r[0],
                    "patient_name": r[1],
                    "age_years": r[2],
                    "created_at": r[3].strftime("%Y-%m-%d %H:%M"),
                    "updated_at": r[4].strftime("%Y-%m-%d %H:%M"),
                } for r in cur.fetchall()
            ]
    finally:
        db_put(conn)
    return render_template("list.html", title=config.APP_TITLE, APP_TITLE=config.APP_TITLE, items=items)

@app.route("/chart/<int:exam_id>")
def chart(exam_id: int):
    conn = db_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT id, patient_name, sex, age_years, data::text FROM exams WHERE id=%s", (exam_id,))
            row = cur.fetchone()
            if not row:
                flash("Exame não encontrado.")
                return redirect(url_for('list_exams'))
            exam = {
                "id": row[0],
                "patient_name": row[1],
                "sex": row[2],
                "age_years": row[3],
                "data": json.loads(row[4]),
            }
    finally:
        db_put(conn)

    items = []
    for label, key, unit, _ in FIELDS:
        v = exam["data"].get(key, None)
        if isinstance(v, (int, float)):
            lo, hi, u_db = find_ref(key, exam["age_years"], exam["sex"])
            unit_final = u_db or unit
            items.append({
                "key": key,
                "label": label,
                "unit": unit_final,
                "value": float(v),
                "low": lo if lo is not None else None,
                "high": hi if hi is not None else None,
                "desc": EXPLAINS.get(key, "—"),
            })
    if not items:
        flash("Nenhum valor numérico preenchido para plotar. Edite o exame e informe ao menos um marcador.")
        return redirect(url_for('edit_exam', exam_id=exam_id))

    items.sort(key=lambda x: x["label"].lower())
    return render_template("chart.html", title=config.APP_TITLE, APP_TITLE=config.APP_TITLE, exam=exam, items=items)

@app.route("/import", methods=["GET", "POST"])
def import_exam():
    if request.method == "GET":
        return render_template("import.html", title=config.APP_TITLE, APP_TITLE=config.APP_TITLE)

    file = request.files.get("file")
    if not file or not file.filename:
        flash("Selecione um arquivo PDF/PNG/JPG.")
        return redirect(url_for("import_exam"))

    try:
        file.stream.seek(0)
        text = extract_text_from_upload(file)
        parsed = parse_lab_text_to_form(text)
    except Exception as e:
        flash(f"Falha ao ler arquivo: {e}")
        return redirect(url_for("import_exam"))

    form = {}
    for _, key, _, _ in FIELDS:
        if key in parsed:
            form[key] = parsed[key]

    meta = {
        "patient_name": parsed.get("_patient_name", ""),
        "sex": "",
        "age_years": parsed.get("_age_years", ""),
    }

    flash("Importado via OCR")
    return render_form({**form, **meta}, exam_id=None)

@app.route("/delete/<int:exam_id>", methods=["POST"])
def delete_exam(exam_id: int):
    conn = db_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM exams WHERE id=%s", (exam_id,))
            if cur.rowcount == 0:
                flash(f"Exame #{exam_id} não encontrado.")
            else:
                flash(f"Exame #{exam_id} excluído.")
    finally:
        db_put(conn)
    return redirect(url_for("list_exams"))

@app.route("/_ping")
def ping():
    from datetime import datetime, timezone
    return jsonify(ok=True, at=datetime.now(timezone.utc).isoformat())
