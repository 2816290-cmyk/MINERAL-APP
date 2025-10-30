from flask import Flask, render_template, request, redirect, url_for, flash, session
import config
from utils.data_loader import ensure_data_files, load_users
from utils.auth import (
    create_user, authenticate, find_user_by_email,
    generate_reset_token, verify_reset_token, reset_password,
    requires_role, unlock_account
)
from utils.viz import load_minerals_json, generate_mineral_chart, generate_overview_chart
from datetime import timedelta
from utils.viz import load_minerals_json

import os

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = config.PERMANENT_SESSION_LIFETIME

# ----- Setup -----
ensure_data_files()

# Create initial admin
def create_initial_admin():
    users = load_users().get("users", [])
    if not any(u["role"] == "Administrator" for u in users):
        admin = create_user("System", "Admin", "admin@example.com", "SouthAfrica", "MINN", "Administrator", "Admin@1234")
        print("Created default admin user:")
        print("  username:", admin["username"])
        print("  email: admin@example.com")
        print("  password: Admin@1234")
create_initial_admin()

# ----- Routes -----
@app.route("/")
def home():
    if "username" in session:
        role = session.get("role")
        if role == "Administrator":
            return redirect(url_for("dashboard_admin"))
        elif role == "Investor":
            return redirect(url_for("dashboard_investor"))
        elif role == "Researcher":
            return redirect(url_for("dashboard_researcher"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        success, message = authenticate(username, password, remote_ip=request.remote_addr)
        if success:
            flash("Login successful.", "success")
            return redirect(url_for("home"))
        else:
            flash(message, "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        country = request.form.get("country", "").strip()
        org = request.form.get("organization", "").strip()
        role = request.form.get("role", "Researcher")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not (first_name and last_name and email and country and password):
            flash("Please fill in all required fields.", "danger")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        if find_user_by_email(email):
            flash("An account with that email already exists.", "danger")
            return render_template("signup.html")
        if role == "Administrator":
            flash("Administrator accounts must be created by an admin.", "danger")
            return render_template("signup.html")

        new_user = create_user(first_name, last_name, email, country, org, role, password)
        flash(f"Account created. Your username is {new_user['username']}. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

# ----- Dashboards -----
@app.route("/dashboard/admin")
@requires_role("Administrator")
def dashboard_admin():
    users = load_users().get("users", [])
    role_counts = {"Administrator": 0, "Investor": 0, "Researcher": 0}
    for u in users:
        r = u.get("role")
        if r in role_counts:
            role_counts[r] += 1
    return render_template("dashboard_admin.html", users=users, role_counts=role_counts, form=None)

@app.route("/dashboard/investor")
@requires_role("Investor")
def dashboard_investor():
    return render_template("dashboard_investor.html")

@app.route("/dashboard/researcher")
@requires_role("Researcher")
def dashboard_researcher():
    minerals = load_minerals_json()
    return render_template("dashboard_researcher.html", minerals=minerals)

# ----- Password Reset -----
@app.route("/reset-request", methods=["GET", "POST"])
def reset_request():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = find_user_by_email(email)
        if not user:
            flash("If an account exists with that email, a link will be sent.", "info")
            return redirect(url_for("login"))
        token = generate_reset_token(email)
        reset_link = url_for("reset_password_route", token=token, _external=True)
        flash("Password reset link generated (for demo it's displayed on screen).", "info")
        return render_template("reset_request.html", reset_link=reset_link)
    return render_template("reset_request.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password_route(token):
    email = verify_reset_token(token)
    if not email:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for("reset_request"))
    if request.method == "POST":
        pw = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if pw != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)
        reset_password(email, pw)
        flash("Password has been reset. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", token=token)

# ----- Admin Unlock -----
@app.route("/admin/unlock/<user_id>", methods=["POST"])
@requires_role("Administrator")
def admin_unlock(user_id):
    ok = unlock_account(user_id)
    flash("Account unlocked." if ok else "Could not find user.", "success" if ok else "danger")
    return redirect(url_for("dashboard_admin"))

# ---- Minerals Dashboard ----
from utils.viz import load_minerals_json, generate_mineral_chart, generate_overview_chart

@app.route("/minerals")
def minerals_dashboard():
    """Display list of minerals with overview chart."""
    minerals = load_minerals_json()
    chart_html = generate_overview_chart()
    return render_template("minerals_dashboard.html", minerals=minerals, chart_html=chart_html)


@app.route("/minerals/<mineral_name>")
def mineral_detail_chart(mineral_name):
    """Display individual mineral chart."""
    chart_html = generate_mineral_chart(mineral_name)
    return render_template("minerals_dashboard.html", chart_html=chart_html, single=True, mineral_name=mineral_name)


if __name__ == "__main__":
    app.run(debug=True)