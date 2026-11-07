from http.server import HTTPServer, BaseHTTPRequestHandler
import json, urllib.parse, requests, os
from datetime import datetime, timezone

SUPABASE_URL = "https://mkqniqayvgukvdtzkaue.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rcW5pcWF5dmd1a3ZkdHprYXVlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI5MTIxNjksImV4cCI6MjEwODQ4ODE2OX0.UEZtgN7syzHvlEraKW75PQ9LonSfafeXRDqBMJlwhj4"
TABLE = "legithax_keys"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def sb_get(key):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{TABLE}", headers=HEADERS, params={"key_value": f"eq.{key.upper()}", "limit": "1"})
    data = r.json()
    return data[0] if data else None

def sb_update_hwid(key, hwid):
    requests.patch(f"{SUPABASE_URL}/rest/v1/{TABLE}", headers=HEADERS, params={"key_value": f"eq.{key.upper()}"}, json={"hwid": hwid, "device_name": "PC"})

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8', errors='replace')
        params = urllib.parse.parse_qs(body)
        req_type = params.get('type', [''])[0]

        if req_type == 'init':
            resp = {"success": True, "message": "Initialized", "nonce": "deadbeef", "sessionid": "FAKESID123456789", "appinfo": {"numUsers": "1", "numOnlineUsers": "1", "numKeys": "9999", "version": "1.0.0", "customerPanelLink": ""}}

        elif req_type in ('login', 'license'):
            key = params.get('key', [''])[0].upper()
            hwid = params.get('hwid', [''])[0]
            now = datetime.now(timezone.utc)
            row = sb_get(key)
            if not row:
                resp = {"success": False, "message": "Invalid license key."}
            elif not row.get("is_active", True):
                resp = {"success": False, "message": "Key banned."}
            else:
                expires_at = row.get("expires_at")
                if expires_at:
                    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp < now:
                        resp = {"success": False, "message": "Key expired."}
                        self._send(resp); return
                bound_hwid = row.get("hwid")
                if bound_hwid and bound_hwid != hwid:
                    resp = {"success": False, "message": "Key is bound to another machine."}
                    self._send(resp); return
                if not bound_hwid:
                    sb_update_hwid(key, hwid)
                timeleft = 99999999
                if expires_at:
                    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    timeleft = max(0, int((exp - now).total_seconds()))
                resp = {"success": True, "message": "Logged in", "sessionid": "FAKESID123456789", "info": {"username": key[:12], "subscriptions": [{"subscription": "default", "expiry": expires_at or "9999999999", "timeleft": timeleft}], "sessionid": "FAKESID123456789", "createdate": "0", "lastlogin": str(int(now.timestamp())), "cooldown": "0"}}

        elif req_type == 'check':
            resp = {"success": True, "message": "Session valid", "sessionid": "FAKESID123456789"}
        elif req_type == 'fetchOnline':
            resp = {"success": True, "message": "1"}
        else:
            resp = {"success": True, "message": "OK", "sessionid": "FAKESID123456789"}

        self._send(resp)

    def _send(self, resp):
        raw = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}")

PORT = int(os.environ.get("PORT", 8080))
print(f"[*] Server running on :{PORT}")
HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
