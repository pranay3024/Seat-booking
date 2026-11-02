"""
SeatDesk — admin-only seat booking for a single auditorium.
Run locally:  python app.py   (then open http://127.0.0.1:5000)
"""
import csv
import hmac
import io
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask, Response, abort, flash, redirect, render_template, request, session, url_for,
)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import db
from seats import (
    ALL_SEATS, LAYOUT, SECTION_COUNTS, SECTION_OF, TOTAL_SEATS, group_by_row, seat_sort_key,
)

# ---------------------------------------------------------------- config
app = Flask(
    __name__,
    static_folder="public/static",   # on Vercel, files in public/ are served by the CDN
    static_url_path="/static",
    template_folder="templates",
)

app.secret_key = os.environ.get("SECRET_KEY") or "dev-only-change-this-secret"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=db.ON_VERCEL,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "" if db.ON_VERCEL else "admin123")

APP_NAME = os.environ.get("APP_NAME", "SeatDesk")
SINGLE_SHOW_TITLE = "Singing Show"
MIN_SEATS, MAX_SEATS = 1, 50
IST = timezone(timedelta(hours=5, minutes=30))
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

app.teardown_appcontext(db.close_db)


# ---------------------------------------------------------------- helpers
def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def new_code():
    for _ in range(10):
        code = "BK-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not db.query("SELECT 1 FROM bookings WHERE code = ?", (code,), one=True):
            return code
    raise RuntimeError("Could not generate booking code")


def clean_phone(p):
    p = (p or "").strip()
    digits = re.sub(r"\D", "", p)
    return p if 7 <= len(digits) <= 15 else None


def parse_seats(raw):
    seen, out = set(), []
    for s in (raw or "").upper().replace(" ", "").split(","):
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def get_single_show():
    show = db.query(
        "SELECT * FROM shows WHERE title = ? ORDER BY show_date DESC, id DESC LIMIT 1",
        (SINGLE_SHOW_TITLE,),
        one=True,
    )
    if show:
        return show

    row = db.execute(
        """INSERT INTO shows (title, venue, show_date, show_time, notes, created_at)
           VALUES (?, '', ?, '', '', ?) RETURNING id""",
        (SINGLE_SHOW_TITLE, date.today().isoformat(), now_utc()),
    )
    db.commit()
    return db.query("SELECT * FROM shows WHERE id = ?", (row["id"],), one=True)


def get_show_or_404(show_id):
    show = get_single_show()
    if show["id"] != show_id:
        abort(404)
    return show


def get_booking_or_404(code):
    show = get_single_show()
    b = db.query(
        """SELECT b.*, s.title AS show_title, s.venue, s.show_date, s.show_time
           FROM bookings b JOIN shows s ON s.id = b.show_id
           WHERE b.code = ? AND b.show_id = ?""",
        (code.upper(), show["id"]), one=True,
    )
    if not b:
        abort(404)
    return b


def booked_map(show_id):
    rows = db.query(
        """SELECT bs.seat, b.code, b.customer_name
           FROM booked_seats bs JOIN bookings b ON b.id = bs.booking_id
           WHERE bs.show_id = ?""",
        (show_id,),
    )
    return {r["seat"]: r for r in rows}


# ---------------------------------------------------------------- template filters
@app.template_filter("ist")
def ist(ts):
    if not ts:
        return ""
    dt = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d %b %Y, %I:%M %p")


@app.template_filter("nicedate")
def nicedate(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%a, %d %b %Y")
    except (TypeError, ValueError):
        return d or ""


@app.template_filter("mon")
def mon(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%b").upper()
    except (TypeError, ValueError):
        return ""


@app.template_filter("nicetime")
def nicetime(t):
    try:
        return datetime.strptime(t, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except (TypeError, ValueError):
        return t or ""


@app.template_filter("rowgroups")
def rowgroups(seats_text):
    return group_by_row(parse_seats(seats_text))


# ---------------------------------------------------------------- security
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@app.context_processor
def inject_globals():
    return {
        "csrf_token": csrf_token,
        "APP_NAME": APP_NAME,
        "PERSISTENT": db.PERSISTENT,
        "MAX_SEATS": MAX_SEATS,
        "TOTAL_SEATS": TOTAL_SEATS,
    }


@app.before_request
def check_csrf():
    if request.method == "POST":
        token = request.form.get("_csrf", "")
        if not token or not hmac.compare_digest(token, session.get("_csrf", "")):
            abort(400, "Form expired — please go back, refresh and try again.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------- auth
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        if not ADMIN_PASSWORD:
            error = "ADMIN_PASSWORD is not set on the server. Add it in Vercel → Settings → Environment Variables."
        else:
            u = request.form.get("username", "")
            p = request.form.get("password", "")
            if hmac.compare_digest(u, ADMIN_USERNAME) and hmac.compare_digest(p, ADMIN_PASSWORD):
                token = session.get("_csrf")
                session.clear()
                session["_csrf"] = token
                session.permanent = True
                session["admin"] = u
                nxt = request.args.get("next") or ""
                return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
            error = "Wrong username or password."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- dashboard
@app.route("/")
@login_required
def dashboard():
    return _render_map(get_single_show())


# ---------------------------------------------------------------- seat map + booking
def _render_map(show, form=None, preselect=None, status=200):
    booked = booked_map(show["id"])
    sold_by_section = {"stalls": 0, "balcony": 0}
    for seat in booked:
        sold_by_section[SECTION_OF.get(seat, "stalls")] += 1
    return render_template(
        "seatmap.html",
        show=show,
        layout=LAYOUT,
        booked=booked,
        sold=len(booked),
        sold_by_section=sold_by_section,
        section_counts=SECTION_COUNTS,
        form=form or {},
        preselect=preselect or [],
        min_seats=MIN_SEATS,
    ), status


@app.route("/shows/<int:show_id>")
@login_required
def seat_map(show_id):
    return _render_map(get_show_or_404(show_id))


@app.route("/shows/<int:show_id>/book", methods=["POST"])
@login_required
def book(show_id):
    show = get_show_or_404(show_id)
    f = request.form
    seats = parse_seats(f.get("seats"))
    try:
        requested_count = int(f.get("seat_count", ""))
    except ValueError:
        requested_count = 0
    name = f.get("customer_name", "").strip()
    phone = clean_phone(f.get("phone"))
    email = f.get("email", "").strip()

    errors = []
    bad = [s for s in seats if s not in ALL_SEATS]
    if bad:
        errors.append("Unknown seat(s): " + ", ".join(bad))
    if not (MIN_SEATS <= requested_count <= MAX_SEATS):
        errors.append(f"Choose between {MIN_SEATS} and {MAX_SEATS} seats.")
    elif len(seats) != requested_count:
        errors.append(f"Select exactly {requested_count} seat(s) (you selected {len(seats)}).")
    if not name:
        errors.append("Customer name is required.")
    if not phone:
        errors.append("Enter a valid phone number.")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors.append("Email address looks wrong.")

    if errors:
        for e in errors:
            flash(e, "error")
        return _render_map(show, form=f, preselect=[s for s in seats if s in ALL_SEATS], status=400)

    seats.sort(key=seat_sort_key)

    code = new_code()
    try:
        row = db.execute(
            """INSERT INTO bookings (code, show_id, customer_name, phone, email, city, num_seats, seats,
                                     notes, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?) RETURNING id""",
            (code, show_id, name, phone, email, f.get("city", "").strip(), len(seats), ",".join(seats),
             f.get("notes", "").strip(), now_utc()),
        )
        db.executemany(
            "INSERT INTO booked_seats (show_id, seat, booking_id) VALUES (?, ?, ?)",
            [(show_id, s, row["id"]) for s in seats],
        )
        db.commit()
    except db.IntegrityError:
        db.rollback()
        taken = set(booked_map(show_id))
        clash = [s for s in seats if s in taken]
        flash("Just booked by someone else: " + ", ".join(clash) + ". Pick other seats.", "error")
        return _render_map(show, form=f, preselect=[s for s in seats if s not in taken], status=409)

    flash(f"Booking {code} confirmed — {len(seats)} seat(s).", "ok")
    return redirect(url_for("booking_detail", code=code))


# ---------------------------------------------------------------- bookings
def _filtered_bookings(args):
    show = get_single_show()
    sql = """SELECT b.*, s.title AS show_title, s.show_date, s.show_time
             FROM bookings b JOIN shows s ON s.id = b.show_id WHERE b.show_id = ?"""
    params = [show["id"]]
    q = args.get("q", "").strip()
    if q:
        like = f"%{q.lower()}%"
        sql += """ AND (LOWER(b.customer_name) LIKE ? OR LOWER(b.phone) LIKE ?
                   OR LOWER(b.code) LIKE ? OR LOWER(COALESCE(b.email, '')) LIKE ?)"""
        params += [like] * 4
    if args.get("status") in ("confirmed", "cancelled"):
        sql += " AND b.status = ?"
        params.append(args["status"])
    sql += " ORDER BY b.created_at DESC LIMIT 1000"
    return db.query(sql, params)


@app.route("/bookings")
@login_required
def bookings():
    rows = _filtered_bookings(request.args)
    return render_template("bookings.html", rows=rows, args=request.args)


@app.route("/bookings.csv")
@login_required
def bookings_csv():
    rows = _filtered_bookings(request.args)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Booking code", "Status", "Show", "Show date", "Show time", "Customer", "Phone", "Email",
                "City", "Seats", "No. of seats", "Notes", "Booked at (IST)"])
    for r in rows:
        w.writerow([r["code"], r["status"], r["show_title"], r["show_date"], r["show_time"], r["customer_name"],
                    r["phone"], r["email"], r["city"], r["seats"].replace(",", " "), r["num_seats"],
                    r["notes"], ist(r["created_at"])])
    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=bookings-{date.today().isoformat()}.csv"},
    )


@app.route("/bookings/<code>")
@login_required
def booking_detail(code):
    return render_template("booking_detail.html", b=get_booking_or_404(code))


@app.route("/bookings/<code>/edit", methods=["POST"])
@login_required
def booking_edit(code):
    b = get_booking_or_404(code)
    f = request.form
    name = f.get("customer_name", "").strip()
    phone = clean_phone(f.get("phone"))
    if not name or not phone:
        flash("Name and a valid phone number are required.", "error")
        return redirect(url_for("booking_detail", code=b["code"]))
    db.execute(
        """UPDATE bookings SET customer_name=?, phone=?, email=?, city=?, notes=? WHERE id=?""",
        (name, phone, f.get("email", "").strip(), f.get("city", "").strip(),
         f.get("notes", "").strip(), b["id"]),
    )
    db.commit()
    flash("Customer details updated.", "ok")
    return redirect(url_for("booking_detail", code=b["code"]))


@app.route("/bookings/<code>/cancel", methods=["POST"])
@login_required
def booking_cancel(code):
    b = get_booking_or_404(code)
    if b["status"] != "cancelled":
        db.execute("DELETE FROM booked_seats WHERE booking_id = ?", (b["id"],))
        db.execute("UPDATE bookings SET status='cancelled', cancelled_at=? WHERE id=?", (now_utc(), b["id"]))
        db.commit()
        flash(f"Booking {b['code']} cancelled. {b['num_seats']} seat(s) released.", "ok")
    return redirect(url_for("booking_detail", code=b["code"]))


# ---------------------------------------------------------------- errors
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", title="Not found", message="That page doesn't exist."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", title="Something's off", message=e.description), 400


if __name__ == "__main__":
    app.run(debug=True)
