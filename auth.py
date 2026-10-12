import os
import sys
import json
import secrets
import base64
import hashlib
import webbrowser
import urllib.parse
import http.server
import requests
import urllib3

HOME = os.path.join(os.path.expandvars("%APPDATA%"), "SASAgent")


def get_base_dir():
    """Return the base directory of the script or frozen executable."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path():
    """Locate config.json in app directory, cwd, or APPDATA."""
    candidates = [
        os.path.join(get_base_dir(), "config.json"),
        os.path.join(os.getcwd(), "config.json"),
        os.path.join(HOME, "config.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Default to app directory
    return os.path.join(get_base_dir(), "config.json")


def get_ssl_verify(cfg):
    """Determine SSL verification setting for requests and httpx2."""
    ca_bundle = cfg.get("ssl_ca_bundle")
    if ca_bundle and os.path.exists(ca_bundle):
        return ca_bundle
    
    verify_ssl = cfg.get("verify_ssl", True)
    if isinstance(verify_ssl, str):
        verify_ssl = verify_ssl.strip().lower() in ("true", "1", "yes")
    
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    return bool(verify_ssl)


def load_config():
    """Load configuration with default fallbacks."""
    cfg_path = get_config_path()
    cfg = {
        "name": "SAS Agent",
        "mcp_server_url": "https://localhost:8080/mcp/v1",
        "authorize_url": "https://localhost:8080/oauth/authorize",
        "token_url": "https://localhost:8080/oauth/token",
        "client_id": "",
        "client_secret": "",
        "scope": "",
        "redirect_uri": "http://localhost:8787/callback",
        "callback_port": 8787,
        "verify_ssl": True,
        "ssl_ca_bundle": "",
        "transport": "auto",
        "token": "",
    }
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                cfg.update(user_cfg)
        except Exception as e:
            print(f"Warning: Could not read {cfg_path}: {e}", file=sys.stderr)
    return cfg


def save_token(tok):
    """Save user token to APPDATA and locally."""
    try:
        os.makedirs(HOME, exist_ok=True)
        with open(os.path.join(HOME, "token.json"), "w", encoding="utf-8") as f:
            json.dump({"token": tok}, f)
    except Exception as e:
        print(f"Notice: Could not write token to APPDATA: {e}", file=sys.stderr)


def clear_token():
    """Remove saved token to force re-login."""
    p = os.path.join(HOME, "token.json")
    if os.path.exists(p):
        try:
            os.remove(p)
        except Exception:
            pass


def load_token(cfg=None):
    """Retrieve token from config, env var, or local storage."""
    # 1. Config direct token (PAT / static token)
    if cfg and cfg.get("token"):
        return cfg["token"].strip()
    
    # 2. Environment variable
    env_token = os.environ.get("SAS_MCP_TOKEN")
    if env_token:
        return env_token.strip()

    # 3. Stored token in APPDATA
    try:
        tok_file = os.path.join(HOME, "token.json")
        if os.path.exists(tok_file):
            with open(tok_file, "r", encoding="utf-8") as f:
                return json.load(f).get("token")
    except Exception:
        pass
    return None


def _b64url(d):
    return base64.urlsafe_b64encode(d).rstrip(b"=").decode()


class ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True


def login(cfg):
    """Authenticate to SAS Viya via OAuth 2.0 PKCE or Client Credentials."""
    verify_ssl = get_ssl_verify(cfg)

    # 1. Check if direct token already provided
    if cfg.get("token"):
        return cfg["token"]

    # 2. Check if client_credentials grant is configured
    grant_type = cfg.get("grant_type", "").lower()
    if grant_type == "client_credentials" or (cfg.get("client_secret") and not cfg.get("authorize_url")):
        body = {
            "grant_type": "client_credentials",
            "client_id": cfg["client_id"],
            "client_secret": cfg.get("client_secret", ""),
        }
        if cfg.get("scope"):
            body["scope"] = cfg["scope"]
        
        r = requests.post(cfg["token_url"], data=body, timeout=30, verify=verify_ssl)
        r.raise_for_status()
        tok = r.json()["access_token"]
        save_token(tok)
        return tok

    # 3. OAuth 2.0 authorization-code with PKCE (standard native client flow)
    state, verifier = secrets.token_urlsafe(16), secrets.token_urlsafe(64)
    auth_params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg.get("redirect_uri", "http://localhost:8787/callback"),
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
    }
    if cfg.get("scope"):
        auth_params["scope"] = cfg["scope"]

    url = cfg["authorize_url"] + ("&" if "?" in cfg["authorize_url"] else "?") + urllib.parse.urlencode(auth_params)
    webbrowser.open(url)

    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got["code"] = q.get("code", [""])[0]
            got["state"] = q.get("state", [""])[0]
            got["error"] = q.get("error", [""])[0]
            got["error_description"] = q.get("error_description", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if got.get("error"):
                html = f"<html><body style='font-family:sans-serif;text-align:center;padding:50px;'><h2>Authentication Failed</h2><p>{got.get('error_description') or got.get('error')}</p></body></html>"
            else:
                html = "<html><body style='font-family:sans-serif;text-align:center;padding:50px;'><h2>Authentication Successful</h2><p>You can close this tab and return to the SAS Agent application.</p></body></html>"
            self.wfile.write(html.encode("utf-8"))
            self.server.shutdown()

        def log_message(self, *a):
            pass

    port = int(cfg.get("callback_port", 8787))
    server = ReusableHTTPServer(("127.0.0.1", port), H)
    server.serve_forever()

    if got.get("error"):
        raise RuntimeError(f"OAuth error: {got['error']} - {got.get('error_description', '')}")

    if got.get("state") != state or not got.get("code"):
        raise RuntimeError("Login failed: OAuth state mismatch or authorization code missing.")

    body = {
        "grant_type": "authorization_code",
        "code": got["code"],
        "client_id": cfg["client_id"],
        "redirect_uri": cfg.get("redirect_uri", f"http://localhost:{port}/callback"),
        "code_verifier": verifier,
    }
    if cfg.get("client_secret"):
        body["client_secret"] = cfg["client_secret"]

    r = requests.post(cfg["token_url"], data=body, timeout=30, verify=verify_ssl)
    r.raise_for_status()
    res_data = r.json()
    tok = res_data.get("access_token")
    if not tok:
        raise RuntimeError(f"No access_token found in token response: {res_data}")

    save_token(tok)
    return tok
