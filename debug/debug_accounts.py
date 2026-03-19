"""
debug_accounts.py — Debug script for Our Legacy 2 account system.

Tests: registration, login, logout, cloud meta/save/load, and edge cases.
Run with: python debug/debug_accounts.py
The app must be running on localhost:5000.
"""

import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:5000"
TEST_USER = f"debugtest_{int(time.time())}"
TEST_PASS = "DebugPass123"

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
WARN = "\033[93m[WARN]\033[0m"

results = []


def log(status, label, detail=""):
    tag = {"PASS": PASS, "FAIL": FAIL, "INFO": INFO, "WARN": WARN}[status]
    line = f"  {tag} {label}"
    if detail:
        line += f"\n         → {detail}"
    print(line)
    if status in ("PASS", "FAIL"):
        results.append((status, label))


def check(label, condition, ok_detail="", fail_detail=""):
    if condition:
        log("PASS", label, ok_detail)
    else:
        log("FAIL", label, fail_detail)


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ─── 1. Server Connectivity ───────────────────────────────────────────────────

section("1. SERVER CONNECTIVITY")

try:
    r = requests.get(BASE_URL, timeout=5)
    check("App is reachable", r.status_code == 200,
          f"HTTP {r.status_code}", f"HTTP {r.status_code} — is the app running?")
except requests.exceptions.ConnectionError:
    log("FAIL", "App is reachable", "Connection refused — start the app first with: python app.py")
    print("\n  Cannot continue without a running server. Exiting.")
    sys.exit(1)


# ─── 2. Registration ──────────────────────────────────────────────────────────

section("2. REGISTRATION")

reg_session = requests.Session()

# Happy path
r = reg_session.post(f"{BASE_URL}/api/online/register",
                     json={"username": TEST_USER, "password": TEST_PASS})
try:
    body = r.json()
    check("Register new user",
          r.status_code == 200 and body.get("ok"),
          body.get("message", ""),
          f"HTTP {r.status_code} — {body.get('message', 'No message')}")
except Exception as e:
    log("FAIL", "Register new user", f"Could not parse response: {e}")

# Duplicate username
r2 = reg_session.post(f"{BASE_URL}/api/online/register",
                      json={"username": TEST_USER, "password": TEST_PASS})
try:
    body2 = r2.json()
    check("Reject duplicate username",
          r2.status_code == 400 and not body2.get("ok"),
          body2.get("message", ""),
          f"Expected 400/ok=false, got HTTP {r2.status_code}")
except Exception as e:
    log("FAIL", "Reject duplicate username", f"Could not parse response: {e}")

# Username too short
r3 = reg_session.post(f"{BASE_URL}/api/online/register",
                      json={"username": "ab", "password": TEST_PASS})
try:
    body3 = r3.json()
    check("Reject username < 3 chars",
          r3.status_code == 400 and not body3.get("ok"),
          body3.get("message", ""),
          f"Expected 400/ok=false, got HTTP {r3.status_code}")
except Exception as e:
    log("FAIL", "Reject username < 3 chars", f"Could not parse response: {e}")

# Password too short
r4 = reg_session.post(f"{BASE_URL}/api/online/register",
                      json={"username": TEST_USER + "_x", "password": "abc"})
try:
    body4 = r4.json()
    check("Reject password < 6 chars",
          r4.status_code == 400 and not body4.get("ok"),
          body4.get("message", ""),
          f"Expected 400/ok=false, got HTTP {r4.status_code}")
except Exception as e:
    log("FAIL", "Reject password < 6 chars", f"Could not parse response: {e}")

# Empty fields
r5 = reg_session.post(f"{BASE_URL}/api/online/register",
                      json={"username": "", "password": ""})
try:
    body5 = r5.json()
    check("Reject empty fields on register",
          r5.status_code == 400 and not body5.get("ok"),
          body5.get("message", ""),
          f"Expected 400/ok=false, got HTTP {r5.status_code}")
except Exception as e:
    log("FAIL", "Reject empty fields on register", f"Could not parse response: {e}")


# ─── 3. Login ─────────────────────────────────────────────────────────────────

section("3. LOGIN")

login_session = requests.Session()

# Wrong password
r = login_session.post(f"{BASE_URL}/api/online/login",
                       json={"username": TEST_USER, "password": "wrongpassword"})
try:
    body = r.json()
    check("Reject wrong password",
          r.status_code == 401 and not body.get("ok"),
          body.get("message", ""),
          f"Expected 401/ok=false, got HTTP {r.status_code}")
except Exception as e:
    log("FAIL", "Reject wrong password", f"Could not parse response: {e}")

# Non-existent user
r2 = login_session.post(f"{BASE_URL}/api/online/login",
                        json={"username": "thisuserdoesnotexist999", "password": TEST_PASS})
try:
    body2 = r2.json()
    check("Reject non-existent user",
          r2.status_code == 401 and not body2.get("ok"),
          body2.get("message", ""),
          f"Expected 401/ok=false, got HTTP {r2.status_code}")
except Exception as e:
    log("FAIL", "Reject non-existent user", f"Could not parse response: {e}")

# Case-insensitive username (login with uppercase)
r3 = login_session.post(f"{BASE_URL}/api/online/login",
                        json={"username": TEST_USER.upper(), "password": TEST_PASS})
try:
    body3 = r3.json()
    check("Accept username case-insensitively",
          r3.status_code == 200 and body3.get("ok"),
          body3.get("message", ""),
          f"Got HTTP {r3.status_code} — {body3.get('message', '')}")
    # Logout after this test to clear session
    login_session.post(f"{BASE_URL}/api/online/logout")
except Exception as e:
    log("FAIL", "Accept username case-insensitively", f"Could not parse response: {e}")

# Happy path login (fresh session we'll keep for later tests)
auth_session = requests.Session()
r4 = auth_session.post(f"{BASE_URL}/api/online/login",
                       json={"username": TEST_USER, "password": TEST_PASS})
try:
    body4 = r4.json()
    login_ok = r4.status_code == 200 and body4.get("ok")
    check("Login with correct credentials",
          login_ok,
          f"username={body4.get('username', '')} — {body4.get('message', '')}",
          f"HTTP {r4.status_code} — {body4.get('message', 'No message')}")
except Exception as e:
    log("FAIL", "Login with correct credentials", f"Could not parse response: {e}")
    login_ok = False

# Username stored as lowercase in session
if login_ok:
    check("Returned username is lowercase",
          body4.get("username", "") == TEST_USER.lower(),
          f"username='{body4.get('username', '')}'",
          f"Expected '{TEST_USER.lower()}', got '{body4.get('username', '')}'")


# ─── 4. Cloud Meta (requires login) ──────────────────────────────────────────

section("4. CLOUD META (requires login)")

if login_ok:
    r = auth_session.get(f"{BASE_URL}/api/online/cloud_meta")
    try:
        body = r.json()
        check("Cloud meta returns ok=True when logged in",
              r.status_code == 200 and body.get("ok"),
              f"meta={body.get('meta')}",
              f"HTTP {r.status_code} — {body}")
        if body.get("meta") is None:
            log("INFO", "No cloud save on this account yet (meta is null — expected for new users)")
    except Exception as e:
        log("FAIL", "Cloud meta endpoint", f"Could not parse response: {e}")

    # Cloud meta when NOT logged in
    anon_session = requests.Session()
    r2 = anon_session.get(f"{BASE_URL}/api/online/cloud_meta")
    try:
        body2 = r2.json()
        check("Cloud meta returns ok=False when not logged in",
              r2.status_code == 200 and not body2.get("ok"),
              body2.get("message", "ok=False returned correctly"),
              f"Expected ok=false, got {body2}")
    except Exception as e:
        log("FAIL", "Cloud meta (not logged in)", f"Could not parse response: {e}")
else:
    log("WARN", "Cloud meta tests skipped — login failed")


# ─── 5. Cloud Save (requires login + active game session) ────────────────────

section("5. CLOUD SAVE (requires login + active game session)")

if login_ok:
    r = auth_session.post(f"{BASE_URL}/api/online/cloud_save")
    try:
        body = r.json()
        if r.status_code == 400 and "No active character" in body.get("message", ""):
            log("WARN", "Cloud save skipped",
                "No active game session — this is expected if you haven't started a game")
            log("INFO", "Cloud save endpoint exists and responds correctly (returns 400 with proper message)")
        elif r.status_code == 200 and body.get("ok"):
            log("PASS", "Cloud save succeeded", body.get("message", ""))
        else:
            log("FAIL", "Cloud save unexpected response",
                f"HTTP {r.status_code} — {body.get('message', body)}")
    except Exception as e:
        log("FAIL", "Cloud save endpoint", f"Could not parse response: {e}")

    # Cloud save without login
    anon_session = requests.Session()
    r2 = anon_session.post(f"{BASE_URL}/api/online/cloud_save")
    try:
        body2 = r2.json()
        check("Cloud save rejected when not logged in",
              r2.status_code == 401 and not body2.get("ok"),
              body2.get("message", ""),
              f"Expected 401, got HTTP {r2.status_code}")
    except Exception as e:
        log("FAIL", "Cloud save auth guard", f"Could not parse response: {e}")
else:
    log("WARN", "Cloud save tests skipped — login failed")


# ─── 6. Cloud Load (requires login) ──────────────────────────────────────────

section("6. CLOUD LOAD (requires login)")

if login_ok:
    r = auth_session.post(f"{BASE_URL}/api/online/cloud_load")
    try:
        body = r.json()
        if r.status_code == 404 and not body.get("ok"):
            log("WARN", "Cloud load skipped",
                "No cloud save exists for this user yet — expected for a brand-new test account")
        elif r.status_code == 200 and body.get("ok"):
            log("PASS", "Cloud load succeeded", body.get("message", ""))
        else:
            log("FAIL", "Cloud load unexpected response",
                f"HTTP {r.status_code} — {body.get('message', body)}")
    except Exception as e:
        log("FAIL", "Cloud load endpoint", f"Could not parse response: {e}")

    # Cloud load without login
    anon_session = requests.Session()
    r2 = anon_session.post(f"{BASE_URL}/api/online/cloud_load")
    try:
        body2 = r2.json()
        check("Cloud load rejected when not logged in",
              r2.status_code == 401 and not body2.get("ok"),
              body2.get("message", ""),
              f"Expected 401, got HTTP {r2.status_code}")
    except Exception as e:
        log("FAIL", "Cloud load auth guard", f"Could not parse response: {e}")
else:
    log("WARN", "Cloud load tests skipped — login failed")


# ─── 7. Logout ────────────────────────────────────────────────────────────────

section("7. LOGOUT")

if login_ok:
    r = auth_session.post(f"{BASE_URL}/api/online/logout")
    try:
        body = r.json()
        check("Logout returns ok=True",
              r.status_code == 200 and body.get("ok"),
              body.get("message", ""),
              f"HTTP {r.status_code} — {body}")
    except Exception as e:
        log("FAIL", "Logout endpoint", f"Could not parse response: {e}")

    # Verify session is actually cleared after logout
    r2 = auth_session.get(f"{BASE_URL}/api/online/cloud_meta")
    try:
        body2 = r2.json()
        check("Session cleared after logout (cloud_meta returns ok=False)",
              not body2.get("ok"),
              "Session correctly invalidated",
              f"Session still active after logout — {body2}")
    except Exception as e:
        log("FAIL", "Session cleared after logout", f"Could not parse response: {e}")

    # Double logout (should still return ok)
    r3 = auth_session.post(f"{BASE_URL}/api/online/logout")
    try:
        body3 = r3.json()
        check("Double logout is safe (idempotent)",
              r3.status_code == 200 and body3.get("ok"),
              body3.get("message", ""),
              f"HTTP {r3.status_code} — {body3}")
    except Exception as e:
        log("FAIL", "Double logout", f"Could not parse response: {e}")
else:
    log("WARN", "Logout tests skipped — login failed")


# ─── 8. Security / Edge Cases ─────────────────────────────────────────────────

section("8. SECURITY & EDGE CASES")

# SQL injection-like username attempt
inj_session = requests.Session()
r = inj_session.post(f"{BASE_URL}/api/online/login",
                     json={"username": "' OR '1'='1", "password": "anything"})
try:
    body = r.json()
    check("Login rejects SQL-injection-like username",
          not body.get("ok"),
          body.get("message", ""),
          f"Unexpected ok=True for injection payload")
except Exception as e:
    log("FAIL", "SQL injection protection", f"Could not parse response: {e}")

# Missing JSON body
r2 = inj_session.post(f"{BASE_URL}/api/online/login",
                      data="not json",
                      headers={"Content-Type": "text/plain"})
check("Login handles non-JSON body gracefully",
      r2.status_code in (400, 401),
      f"HTTP {r2.status_code}",
      f"Got HTTP {r2.status_code} — may cause 500 error")

# Very long username (stress test)
r3 = inj_session.post(f"{BASE_URL}/api/online/register",
                      json={"username": "a" * 500, "password": TEST_PASS})
try:
    body3 = r3.json()
    check("Register rejects extremely long username gracefully",
          r3.status_code != 500,
          f"HTTP {r3.status_code} — {body3.get('message', '')}",
          f"Server returned 500 — unhandled error for long username")
except Exception as e:
    log("FAIL", "Long username handling", f"Could not parse response: {e}")


# ─── 9. Summary ───────────────────────────────────────────────────────────────

section("9. SUMMARY")

passed = [l for s, l in results if s == "PASS"]
failed = [l for s, l in results if s == "FAIL"]

print(f"\n  Total checks : {len(results)}")
print(f"  \033[92mPassed\033[0m       : {len(passed)}")
print(f"  \033[91mFailed\033[0m       : {len(failed)}")

if failed:
    print(f"\n  Failed checks:")
    for label in failed:
        print(f"    \033[91m✗\033[0m {label}")

print(f"\n  Test account used: {TEST_USER}")
print(f"  (You can delete it from Supabase: ol2_users WHERE username='{TEST_USER}')\n")
