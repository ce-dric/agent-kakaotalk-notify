# AGENTS.md

## Purpose

This repository provides a minimal KakaoTalk notifier that an AI agent can use to send a completion summary to the user's KakaoTalk `Me` chat.

## Operating Rules

- Never ask the user to paste secret values into chat.
- Read secrets only from the local `.env` file.
- Assume `token.json` is local-only and sensitive.
- Do not modify `.env` unless the user explicitly asks.
- Do not commit `.env` or `token.json`.

## Repository Discovery Rule

When an agent needs to use this repository from another workspace, resolve its path in this order:

1. Use `./agent-kakao-notify` if it exists inside the current workspace.
2. Otherwise use `KAKAO_NOTIFY_HOME` if that environment variable is set.
3. Otherwise use a user-provided shared clone path if one is explicitly configured.
4. Otherwise clone the configured GitHub repository and use the newly created path.
5. If multiple candidate paths exist, do not guess. Report the ambiguity and stop.

After resolving the repository path, run `kakao_notify.py` from that location.

## Expected Flow

For any task that results in analysis, code changes, or verification:

1. Complete the requested work.
2. Prepare a short summary in Korean or the user's language.
3. Send the summary with:

```powershell
python .\kakao_notify.py send --text "<summary>"
```

4. Then send the normal final answer in chat.

## Summary Format

Use one short line when possible.

Recommended format:

```text
작업 완료: <무엇을 했는지>. 결과: <성공/실패>. 다음: <있으면 한 줄>.
```

Examples:

```text
작업 완료: 빌드 스크립트 분리. 결과: 성공. 다음: 클린 빌드 검증 필요.
작업 완료: 카카오 알림 연동 설정. 결과: 성공.
```

## Failure Handling

- If send fails, mention it in the final chat response.
- Do not retry indefinitely.
- If OAuth is not initialized, instruct the user to run:

```powershell
python .\kakao_notify.py auth
```
