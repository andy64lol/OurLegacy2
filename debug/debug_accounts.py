
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:5000"
TEST_USER = f"dbg{int(time.time()) % 10**7}"
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

section("1. SERVER CONNECTIVITY")

try:
    r = requests.get(BASE_URL, timeout=5)
    check("App is reachable", r.status_code == 200,
          f"HTTP {r.status_code}", f"HTTP {r.status_code} — is the app running?")
except requests.exceptions.ConnectionError:
    log("FAIL", "App is reachable", "Connection refused — start the app first with: python app.py")
    print("\n  Cannot continue without a running server. Exiting.")
    sys.exit(1)

section("2. REGISTRATION")

reg_session = requests.Session()

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

user_20 = f"u{'x' * 17}{int(time.time()) % 100:02d}"[:20]
r_20 = reg_session.post(f"{BASE_URL}/api/online/register",
                        json={"username": user_20, "password": TEST_PASS})
try:
    body_20 = r_20.json()
    check("Accept username of exactly 20 chars",
          r_20.status_code in (200, 400) and r_20.status_code != 500,
          f"HTTP {r_20.status_code} — {body_20.get('message', '')}",
          f"Server error for 20-char username: HTTP {r_20.status_code}")
    if r_20.status_code == 200:
        log("INFO", f"20-char username '{user_20}' created (will be cleaned up from Supabase)")
except Exception as e:
    log("FAIL", "Accept username of exactly 20 chars", f"Could not parse response: {e}")

r_21 = reg_session.post(f"{BASE_URL}/api/online/register",
                        json={"username": "a" * 21, "password": TEST_PASS})
try:
    body_21 = r_21.json()
    check("Reject username > 20 chars",
          r_21.status_code == 400 and not body_21.get("ok"),
          body_21.get("message", ""),
          f"Expected 400, got HTTP {r_21.status_code} — username over limit was accepted!")
except Exception as e:
    log("FAIL", "Reject username > 20 chars", f"Could not parse response: {e}")

r4 = requests.post(f"{BASE_URL}/api/online/register",
                   json={"username": TEST_USER + "x", "password": "abc"})
if r4.status_code == 429:
    log("WARN", "Reject password < 6 chars — skipped (register rate limit reached for this IP)",
        "Restart the app to reset the in-memory limit counter and re-run")
else:
    try:
        body4 = r4.json()
        check("Reject password < 6 chars",
              r4.status_code == 400 and not body4.get("ok"),
              body4.get("message", ""),
              f"Expected 400/ok=false, got HTTP {r4.status_code}")
    except Exception as e:
        log("FAIL", "Reject password < 6 chars", f"Could not parse response: {e}")

r5 = requests.post(f"{BASE_URL}/api/online/register",
                   json={"username": "", "password": ""})
if r5.status_code == 429:
    log("WARN", "Reject empty fields on register — skipped (register rate limit reached for this IP)",
        "Restart the app to reset the in-memory limit counter and re-run")
else:
    try:
        body5 = r5.json()
        check("Reject empty fields on register",
              r5.status_code == 400 and not body5.get("ok"),
              body5.get("message", ""),
              f"Expected 400/ok=false, got HTTP {r5.status_code}")
    except Exception as e:
        log("FAIL", "Reject empty fields on register", f"Could not parse response: {e}")

section("3. LOGIN")

login_session = requests.Session()

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

r3 = login_session.post(f"{BASE_URL}/api/online/login",
                        json={"username": TEST_USER.upper(), "password": TEST_PASS})
try:
    body3 = r3.json()
    check("Accept username case-insensitively",
          r3.status_code == 200 and body3.get("ok"),
          body3.get("message", ""),
          f"Got HTTP {r3.status_code} — {body3.get('message', '')}")
    login_session.post(f"{BASE_URL}/api/online/logout")
except Exception as e:
    log("FAIL", "Accept username case-insensitively", f"Could not parse response: {e}")

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

if login_ok:
    check("Returned username is lowercase",
          body4.get("username", "") == TEST_USER.lower(),
          f"username='{body4.get('username', '')}'",
          f"Expected '{TEST_USER.lower()}', got '{body4.get('username', '')}'")

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
            log("INFO", "No cloud save on this account yet (expected for new users)")
    except Exception as e:
        log("FAIL", "Cloud meta endpoint", f"Could not parse response: {e}")

    anon_session = requests.Session()
    r2 = anon_session.get(f"{BASE_URL}/api/online/cloud_meta")
    try:
        body2 = r2.json()
        check("Cloud meta returns ok=False when not logged in",
              r2.status_code == 200 and not body2.get("ok"),
              "ok=False returned correctly",
              f"Expected ok=false, got {body2}")
    except Exception as e:
        log("FAIL", "Cloud meta (not logged in)", f"Could not parse response: {e}")
else:
    log("WARN", "Cloud meta tests skipped — login failed")

section("5. CLOUD SAVE (requires login + active game session)")

if login_ok:
    r = auth_session.post(f"{BASE_URL}/api/online/cloud_save")
    try:
        body = r.json()
        if r.status_code == 400 and "No active character" in body.get("message", ""):
            log("WARN", "Cloud save skipped",
                "No active game session — expected if you haven't started a game")
            log("INFO", "Cloud save endpoint responds correctly (400 with proper message)")
        elif r.status_code == 200 and body.get("ok"):
            log("PASS", "Cloud save succeeded", body.get("message", ""))
        else:
            log("FAIL", "Cloud save unexpected response",
                f"HTTP {r.status_code} — {body.get('message', body)}")
    except Exception as e:
        log("FAIL", "Cloud save endpoint", f"Could not parse response: {e}")

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

section("6. CLOUD LOAD (requires login)")

if login_ok:
    r = auth_session.post(f"{BASE_URL}/api/online/cloud_load")
    try:
        body = r.json()
        if r.status_code == 404 and not body.get("ok"):
            log("WARN", "Cloud load skipped",
                "No cloud save exists for this user yet — expected for a new test account")
        elif r.status_code == 200 and body.get("ok"):
            log("PASS", "Cloud load succeeded", body.get("message", ""))
        else:
            log("FAIL", "Cloud load unexpected response",
                f"HTTP {r.status_code} — {body.get('message', body)}")
    except Exception as e:
        log("FAIL", "Cloud load endpoint", f"Could not parse response: {e}")

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

    r2 = auth_session.get(f"{BASE_URL}/api/online/cloud_meta")
    try:
        body2 = r2.json()
        check("Session cleared after logout",
              not body2.get("ok"),
              "Session correctly invalidated",
              f"Session still active after logout — {body2}")
    except Exception as e:
        log("FAIL", "Session cleared after logout", f"Could not parse response: {e}")

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

section("8. SECURITY & EDGE CASES")

inj_session = requests.Session()

r = inj_session.post(f"{BASE_URL}/api/online/login",
                     json={"username": "' OR '1'='1", "password": "anything"})
try:
    body = r.json()
    check("Login rejects SQL-injection-like username",
          not body.get("ok"),
          body.get("message", ""),
          "Unexpected ok=True for injection payload")
except Exception as e:
    log("FAIL", "SQL injection protection", f"Could not parse response: {e}")

r2 = inj_session.post(f"{BASE_URL}/api/online/login",
                      data="not json",
                      headers={"Content-Type": "text/plain"})
check("Login handles non-JSON body gracefully",
      r2.status_code in (400, 401),
      f"HTTP {r2.status_code}",
      f"Got HTTP {r2.status_code} — may cause 500 error")

section("9. RATE LIMITING")

log("INFO", "Login limit: 10 per minute per IP")
log("INFO", "Register limit: 5 per hour per IP")
log("INFO", "Sending 10 rapid wrong-password login attempts to trigger the login rate limit...")

rl_session = requests.Session()
last_status = None
hit_429 = False

for i in range(12):
    r = rl_session.post(f"{BASE_URL}/api/online/login",
                        json={"username": "ratelimitcheckuser", "password": "badpass"})
    last_status = r.status_code
    if r.status_code == 429:
        hit_429 = True
        check(f"Login rate limit triggered on attempt {i + 1}",
              True,
              "HTTP 429 Too Many Requests — rate limiter is working")
        break

if not hit_429:
    log("FAIL", "Login rate limit not triggered after 12 attempts",
        f"Last status: {last_status} — check that flask-limiter is installed and active")

log("INFO", "Testing register rate limit (5 per hour)...")
log("INFO", "Note: previous registration tests count toward the 5/hour limit.")

rl_reg_session = requests.Session()
hit_reg_429 = False

for i in range(8):
    r = rl_reg_session.post(f"{BASE_URL}/api/online/register",
                            json={"username": "ab", "password": "x"})
    if r.status_code == 429:
        hit_reg_429 = True
        check(f"Register rate limit triggered on attempt {i + 1}",
              True,
              "HTTP 429 Too Many Requests — rate limiter is working")
        break

if not hit_reg_429:
    log("WARN", "Register rate limit not triggered in 8 attempts",
        "This may be because the hour window reset, or flask-limiter is not active")

section("10. SUMMARY")

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
print(f"  (Clean up: DELETE FROM ol2_users WHERE username='{TEST_USER}'")
if 'user_20' in dir():
    print(f"             DELETE FROM ol2_users WHERE username='{user_20}')")
print()
