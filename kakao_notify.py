#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
DEFAULT_SCOPE = "talk_message"
DEFAULT_REDIRECT_URI = "http://localhost:3000/oauth/kakao/callback"
DEFAULT_TOKEN_PATH = "token.json"


class ConfigError(RuntimeError):
    pass


def load_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        raise ConfigError(f"Missing env file: {env_path}")

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"Invalid env line: {raw_line}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def require_env(values: dict[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required setting: {key}")
    return value


def resolve_token_path(env_path: Path, values: dict[str, str]) -> Path:
    token_name = values.get("KAKAO_TOKEN_PATH", DEFAULT_TOKEN_PATH).strip() or DEFAULT_TOKEN_PATH
    token_path = Path(token_name)
    if not token_path.is_absolute():
        token_path = env_path.parent / token_path
    return token_path


def prompt_value(label: str, default: str | None = None, secret: bool = False) -> str:
    prompt = f"{label}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "

    while True:
        value = getpass.getpass(prompt) if secret else input(prompt)
        value = value.strip()
        if value:
            return value
        if default is not None:
            return default
        print(f"{label} is required.")


def format_env(values: dict[str, str]) -> str:
    ordered_keys = [
        "KAKAO_REST_API_KEY",
        "KAKAO_CLIENT_SECRET",
        "KAKAO_REDIRECT_URI",
        "KAKAO_TOKEN_PATH",
    ]
    lines = [f"{key}={values[key]}" for key in ordered_keys]
    return "\n".join(lines) + "\n"


def do_init(env_path: Path, force: bool) -> None:
    if env_path.exists() and not force:
        raise ConfigError(f"Env file already exists: {env_path}. Use init --force to overwrite it.")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    values = {
        "KAKAO_REST_API_KEY": prompt_value("Kakao REST API Key", secret=True),
        "KAKAO_CLIENT_SECRET": prompt_value("Kakao Client Secret", secret=True),
        "KAKAO_REDIRECT_URI": prompt_value("Kakao Redirect URI", default=DEFAULT_REDIRECT_URI),
        "KAKAO_TOKEN_PATH": prompt_value("Token file path", default=DEFAULT_TOKEN_PATH),
    }
    env_path.write_text(format_env(values), encoding="utf-8")
    print(f"Saved env file to {env_path}")


def post_form(url: str, form_data: dict[str, str], headers: dict[str, str] | None = None) -> dict[str, Any]:
    body = urllib.parse.urlencode(form_data).encode("utf-8")
    request_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {error_body}") from exc

    return json.loads(payload)


def load_token(token_path: Path) -> dict[str, Any]:
    if not token_path.exists():
        raise ConfigError(f"Missing token file: {token_path}")
    return json.loads(token_path.read_text(encoding="utf-8"))


def save_token(token_path: Path, token_data: dict[str, Any]) -> None:
    token_data["saved_at"] = int(time.time())
    token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def exchange_code_for_token(config: dict[str, str], code: str) -> dict[str, Any]:
    return post_form(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": require_env(config, "KAKAO_REST_API_KEY"),
            "redirect_uri": require_env(config, "KAKAO_REDIRECT_URI"),
            "code": code,
            "client_secret": require_env(config, "KAKAO_CLIENT_SECRET"),
        },
    )


def refresh_access_token(config: dict[str, str], refresh_token: str) -> dict[str, Any]:
    return post_form(
        TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "client_id": require_env(config, "KAKAO_REST_API_KEY"),
            "refresh_token": refresh_token,
            "client_secret": require_env(config, "KAKAO_CLIENT_SECRET"),
        },
    )


def token_is_fresh(token_data: dict[str, Any]) -> bool:
    expires_in = int(token_data.get("expires_in", 0))
    saved_at = int(token_data.get("saved_at", 0))
    if expires_in <= 0 or saved_at <= 0:
        return False
    return time.time() < (saved_at + expires_in - 60)


def ensure_access_token(config: dict[str, str], token_path: Path) -> str:
    token_data = load_token(token_path)
    if token_is_fresh(token_data):
        return str(token_data["access_token"])

    refresh_token = str(token_data.get("refresh_token", "")).strip()
    if not refresh_token:
        raise ConfigError("Stored token is missing refresh_token.")

    refreshed = refresh_access_token(config, refresh_token)
    token_data["access_token"] = refreshed["access_token"]
    token_data["expires_in"] = refreshed.get("expires_in", token_data.get("expires_in", 0))
    if refreshed.get("refresh_token"):
        token_data["refresh_token"] = refreshed["refresh_token"]
    save_token(token_path, token_data)
    return str(token_data["access_token"])


def build_authorize_url(config: dict[str, str], state: str) -> str:
    params = {
        "client_id": require_env(config, "KAKAO_REST_API_KEY"),
        "redirect_uri": require_env(config, "KAKAO_REDIRECT_URI"),
        "response_type": "code",
        "scope": DEFAULT_SCOPE,
        "state": state,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server_version = "AgentKakaoNotify/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = params.get("code", [None])[0]  # type: ignore[attr-defined]
        self.server.auth_state = params.get("state", [None])[0]  # type: ignore[attr-defined]
        self.server.auth_error = params.get("error", [None])[0]  # type: ignore[attr-defined]

        if self.server.auth_code:  # type: ignore[attr-defined]
            self.send_response(200)
            body = "Kakao authorization completed. You can close this window."
        else:
            self.send_response(400)
            body = "Kakao authorization failed. Check the terminal output."

        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        return


def run_local_callback_server(redirect_uri: str, expected_state: str) -> str:
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
        raise ConfigError("Redirect URI must be an http://localhost:<port>/... address for local auth.")

    server = HTTPServer((parsed.hostname, parsed.port), OAuthCallbackHandler)
    server.timeout = 180
    server.auth_code = None  # type: ignore[attr-defined]
    server.auth_state = None  # type: ignore[attr-defined]
    server.auth_error = None  # type: ignore[attr-defined]

    deadline = time.time() + 180
    while time.time() < deadline and server.auth_code is None and server.auth_error is None:  # type: ignore[attr-defined]
        server.handle_request()

    if server.auth_error:  # type: ignore[attr-defined]
        raise RuntimeError(f"Kakao authorization failed: {server.auth_error}")  # type: ignore[attr-defined]
    if server.auth_state != expected_state:  # type: ignore[attr-defined]
        raise RuntimeError("State mismatch in OAuth callback.")
    if not server.auth_code:  # type: ignore[attr-defined]
        raise RuntimeError("Timed out waiting for OAuth callback.")
    return str(server.auth_code)  # type: ignore[attr-defined]


def make_state() -> str:
    return f"agent-kakao-notify-{int(time.time())}"


def do_auth(env_path: Path) -> None:
    config = load_env(env_path)
    token_path = resolve_token_path(env_path, config)
    state = make_state()
    authorize_url = build_authorize_url(config, state)

    print(f"Opening browser for Kakao login: {authorize_url}")
    webbrowser.open(authorize_url)
    code = run_local_callback_server(require_env(config, "KAKAO_REDIRECT_URI"), state)
    token_data = exchange_code_for_token(config, code)
    save_token(token_path, token_data)
    print(f"Authorization succeeded. Token saved to {token_path}")


def make_template(text: str, link: str | None) -> dict[str, Any]:
    safe_link = link or "https://developers.kakao.com"
    return {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": safe_link,
            "mobile_web_url": safe_link,
        },
        "button_title": "Open",
    }


def do_send(env_path: Path, text: str, link: str | None) -> None:
    config = load_env(env_path)
    token_path = resolve_token_path(env_path, config)
    access_token = ensure_access_token(config, token_path)
    template = make_template(text, link)

    response = post_form(
        SEND_MEMO_URL,
        {"template_object": json.dumps(template, ensure_ascii=False)},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if response.get("result_code") != 0:
        raise RuntimeError(f"Kakao send failed: {json.dumps(response, ensure_ascii=False)}")
    print("Message sent to KakaoTalk 'Me' chat.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Official KakaoTalk 'Me' notifier for AI agents")
    parser.add_argument(
        "--env",
        default=str(Path(__file__).with_name(".env")),
        help="Path to .env file. Defaults to ./.env",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="Create a local .env file by prompting in the terminal")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing .env file")
    subparsers.add_parser("auth", help="Run first-time OAuth login flow")

    send_parser = subparsers.add_parser("send", help="Send a text message to 'Me'")
    send_parser.add_argument("--text", required=True, help="Message text to send")
    send_parser.add_argument("--link", help="Optional URL to attach to the message")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        env_path = Path(args.env).resolve()
        if args.command == "init":
            do_init(env_path, args.force)
        elif args.command == "auth":
            do_auth(env_path)
        elif args.command == "send":
            do_send(env_path, args.text, args.link)
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
