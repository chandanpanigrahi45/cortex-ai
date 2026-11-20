# Cortex AI

## Verified implementation status

| Architecture area | Status | Details |
| --- | --- | --- |
| FastAPI backend | Implemented | Modular user, credit, agent, and payment routers. |
| PostgreSQL | Implemented | Users, credit ledger, and payment orders. Existing user tables get a non-destructive password-hash column migration at startup. |
| Authentication | Implemented | Passwords are Argon2-hashed; protected endpoints require a signed, expiring JWT. User IDs are taken from the token, not request bodies. |
| Credit accounting | Implemented | Agent calls write negative ledger entries; credit top-ups are only granted for captured, verified payments. |
| Razorpay | Implemented, configuration required | Fixed package: INR 50 for 50 credits. Server verifies payment signatures and captured status; webhook processing and duplicate-callback protection are included. |
| React frontend | Implemented | Password login/registration, bearer-token API requests, agent selector, and Razorpay Checkout. |
| Docker Compose and Nginx | Implemented | Compose runs PostgreSQL, Redis, FastAPI, and an Nginx-served React build. |
| Redis memory/queues | Not implemented | Redis connectivity is configured and health-checked, but chat memory and background jobs do not use Redis yet. |
| LangChain orchestration | Not implemented | Agent calls currently use the Google GenAI SDK directly, not LangChain chains. |
| Master router | Partial | Gemini routes requests to the selected agent. The model defaults to `gemini-2.5-flash`; it is not the originally described `gemini-1.5-flash`. |
| Code, chat, and PPT agents | Partial | They return generated text; no code execution or `.pptx` file generation is implemented. |
| PDF agent | Not implemented as a document workflow | It can respond to text instructions but there is no upload, PDF parsing, or extracted-document context. |
| Image and video agents | Prompt-only | They generate prompts/storyboards; they do not create image or video files. |
| Persistent conversation history | Not implemented | Chat threads currently live only in frontend memory and disappear on reload. |

## Authentication and existing accounts

New accounts must use a password of 8 to 128 characters. Set `JWT_SECRET_KEY` to a random value of at least 32 characters in `Backend/.env`; do not commit secrets. A token expires after 60 minutes by default and the user must sign in again.

Accounts created before password authentication have no password hash and cannot use the new login until an administrator sets one. From the `Backend` directory, run `..\.venv\Scripts\python.exe reset_password.py`; the password is entered through a hidden terminal prompt. This requires trusted local/backend shell access.

## Payment setup

Copy the variable names from `Backend/.env.example` into `Backend/.env` without overwriting existing values. Configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` with Razorpay test credentials first. Configure the webhook URL as `/api/payments/webhook` and subscribe to `payment.captured`. Live payments require production keys, HTTPS, and a publicly reachable webhook URL.

Credits are not added when an order is created or a browser claims success. The server grants them after signature, order, amount, and captured-status verification. The current catalog intentionally has one fixed INR 50 / 50-credit package.

## Running

For the complete Docker stack, ensure `Backend/.env` exists and contains the required keys, then run from the repository root:

```powershell
docker-compose up --build -d
```

The frontend is served on port 80 and the API on port 8000. For local development, start the API from `Backend` with `..\.venv\Scripts\python.exe -m uvicorn main:app --reload` and the frontend from `Frontend` with `npm run dev`.

## Original product goals still outstanding

Redis-backed conversational memory/queues, real PDF ingestion, generated PPTX/image/video artifacts, and a LangChain-based orchestration layer remain follow-up work. The current agents are text generation workflows, not full media production pipelines.