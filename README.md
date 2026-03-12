# Agent Kakao Notify

Minimal official KakaoTalk notifier for AI agents.

This project lets a user store their Kakao Developers credentials locally and gives an agent a simple command to send a short summary to the user's KakaoTalk `Me` chat after work is completed.

## Scope

- Official Kakao Login + KakaoTalk message API
- Sends only to the authenticated user's `Me` chat
- Intended for local use by coding agents or automation scripts

This project does not support:

- Sending to friends
- Sending to open chat rooms
- Running as an unofficial KakaoTalk bot

## Files

- `kakao_notify.py`: OAuth login, token refresh, and message sending
- `.env.example`: local configuration template
- `AGENTS.md`: instructions an AI agent can follow
- `INTEGRATION.md`: practical integration patterns

## Setup

If you want a Korean step-by-step walkthrough for the initial Kakao Developers setup, follow this guide first:

[Korean setup guide](https://cornwall.tistory.com/44)

1. Create a Kakao Developers app.
2. Enable Kakao Login.
3. Generate a Client Secret.
4. Register this Redirect URI:

```text
http://localhost:3000/oauth/kakao/callback
```

5. Enable the `talk_message` consent item.
6. Create `.env` either by copying `.env.example` manually or by running:

```powershell
python .\kakao_notify.py init
```

7. Fill in:

```env
KAKAO_REST_API_KEY=...
KAKAO_CLIENT_SECRET=...
KAKAO_REDIRECT_URI=http://localhost:3000/oauth/kakao/callback
KAKAO_TOKEN_PATH=token.json
```

## First-time login

If you used `init`, the script prompted for the values locally in your terminal and wrote `.env` for you.

```powershell
python .\kakao_notify.py auth
```

This opens a browser, completes OAuth, and stores tokens in `token.json`.

## Send a message

```powershell
python .\kakao_notify.py send --text "Task complete: build succeeded."
```

Optional link:

```powershell
python .\kakao_notify.py send --text "Task complete." --link "http://localhost/report"
```

## Suggested agent workflow

Tell the agent:

1. Do the requested work.
2. Prepare a 1-3 line summary.
3. Run:

```powershell
python .\kakao_notify.py send --text "<summary>"
```

4. Then answer in chat normally.

See `AGENTS.md` and `INTEGRATION.md` for examples.

## Security

- Never commit `.env` or `token.json`.
- Never paste API keys or tokens into chat.
- Rotate keys if they were exposed.

## Validation

You can validate the script without sending:

```powershell
python -m py_compile .\kakao_notify.py
python .\kakao_notify.py --help
python .\kakao_notify.py init --help
```
