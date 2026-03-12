# Integration

## Initial Setup

If the user has not completed the Kakao Developers setup yet, send them this guide first:

[Korean setup guide](https://cornwall.tistory.com/44)

If `.env` is not set up yet, initialize it locally without pasting secrets into chat:

```powershell
python .\kakao_notify.py init
```

Then authenticate once:

```powershell
python .\kakao_notify.py auth
```

## Manual Use

After any task:

```powershell
python .\kakao_notify.py send --text "작업 완료: 요청 반영. 결과: 성공."
```

## Scripted Use

PowerShell example:

```powershell
$summary = "작업 완료: 빌드 설정 갱신. 결과: 성공."
python .\kakao_notify.py send --text $summary
```

## Agent Prompt Snippet

You can give an AI agent this instruction:

```text
When you finish a task in this repository, send a short KakaoTalk summary by running:
python .\kakao_notify.py send --text "<short summary>"
Use the local .env and token.json already configured in the repo. Do not ask for secret values in chat.
```

## Multi-repository Pattern

You can either:

- copy this repository into each workspace, or
- keep it as a shared utility folder and call it with an absolute path

Example:

```powershell
python C:\Workspace\agent-kakao-notify\kakao_notify.py send --text "작업 완료: 문서 수정. 결과: 성공."
```

## Re-authentication

If the local token is missing or invalid:

```powershell
python .\kakao_notify.py auth
```
