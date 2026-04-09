# WhatsApp AI Supplement Assistant

A WhatsApp chatbot that acts as a personal supplement assistant. It uses Google Gemini as an intelligent router to converse with users, remember their dietary restrictions, search for products across marketplaces, and schedule proactive reminders when supplies run low.

## Architecture

```
WhatsApp User
     |
     v
Meta Cloud API  -->  ngrok  -->  FastAPI (POST /webhook)
                                      |
                                      v
                              IncomingMessageHandler
                              /         |          \
                    UserRepo      ChatRepo      LLMClient (Gemini)
                        |             |               |
                        v             v               v
                           PostgreSQL            ToolFactory
                                                 /        \
                                          SearchTool   NotifyTool
                                              |             |
                                         Marketplaces   ReminderRepo
                                        (interfaces)        |
                                                        PostgreSQL

Celery Beat (daily 9AM) --> Celery Worker --> check due reminders --> send WhatsApp alerts
```

## Tech Stack

- **Python 3.12** with **FastAPI** for the async webhook server
- **PostgreSQL 16** for users, chat history, and reminders
- **Redis 7** as the Celery message broker
- **Celery** for scheduled background tasks (daily reminder checks)
- **Google Gemini 2.0 Flash** as the LLM (prompt-driven tool calling, no SDK framework)
- **Docker Compose** to run all services

## Project Structure

```
app/
├── main.py                     # FastAPI endpoints (GET/POST /webhook)
├── config.py                   # Environment config via pydantic-settings
├── constants.py                # System prompt for the LLM
├── database.py                 # Async + sync SQLAlchemy engines
├── tables.py                   # SQLAlchemy ORM table definitions
├── worker.py                   # Celery app + daily reminder beat task
├── handlers/
│   └── incoming_message_handler.py   # Message orchestration logic
├── llm/
│   ├── llm_client.py           # Gemini API wrapper
│   └── tools/
│       ├── tool_interface.py   # ITool abstract base class
│       ├── tool_factory.py     # Maps action names to tool instances
│       ├── search.py           # SearchTool (marketplace interfaces)
│       └── notify.py           # NotifyTool (creates reminders)
├── models/
│   ├── incoming_message.py     # Pydantic model for webhook payloads
│   ├── user.py                 # UserCreate / UserResponse
│   ├── chat_message.py         # ChatMessageCreate / ChatMessageResponse
│   └── reminder.py             # ReminderCreate / ReminderResponse
├── repositories/
│   ├── user_repository.py      # User DB operations
│   ├── chat_repository.py      # Chat history DB operations
│   └── reminder_repository.py  # Reminder DB operations
└── util/
    └── whatsapp_util.py        # Parse incoming webhooks, send messages via Meta API
```

## Prerequisites

- Docker and Docker Compose
- A [Meta Developer](https://developers.facebook.com/) account with a WhatsApp Business app
- A [Google AI Studio](https://aistudio.google.com/) API key for Gemini
- [ngrok](https://ngrok.com/) for local webhook tunneling

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd supplement-concierge
```

Create `.env` with your credentials:

```
DATABASE_URL=postgresql+asyncpg://whats_bot:whats_bot@postgres:5432/whats_bot
SYNC_DATABASE_URL=postgresql+psycopg2://whats_bot:whats_bot@postgres:5432/whats_bot
REDIS_URL=redis://redis:6379/0
META_VERIFY_TOKEN=<choose-a-secret-token>
META_API_TOKEN=<your-meta-api-token>
META_PHONE_NUMBER_ID=<your-phone-number-id>
GEMINI_API_KEY=<your-gemini-api-key>
```

### 2. Start all services

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, the FastAPI app, the Celery worker, and the Celery beat scheduler.

### 3. Apply database migrations

```bash
docker compose exec app alembic upgrade head
```

### 4. Expose to WhatsApp via ngrok

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g. `https://xyz.ngrok-free.app`) and configure it in the Meta Developer Portal:

1. Go to your WhatsApp app > Configuration > Webhooks
2. Set the callback URL to `https://xyz.ngrok-free.app/webhook`
3. Set the verify token to the same value as `META_VERIFY_TOKEN` in your `.env`
4. Subscribe to the `messages` webhook field

### 5. Test it

Send a WhatsApp message to your business number. The bot should reply.

## How It Works

1. **User sends a WhatsApp message** -- Meta forwards it as a webhook POST to `/webhook`
2. **`IncomingMessageHandler`** orchestrates the flow:
   - Gets or creates the user in the database
   - Loads the last 10 messages for conversation context
   - Sends the conversation + system prompt to Gemini
3. **Gemini responds** with either plain text or a JSON action block:
   - Plain text: sent directly back to the user
   - Action (e.g. `{"action": "search_tool", "params": {...}}`): dispatched via `ToolFactory`, result fed back to Gemini for a natural-language reply
4. **Daily at 9 AM**, Celery Beat triggers a task that checks for due reminders and sends proactive WhatsApp alerts

## Adding a New Tool

1. Create a class in `app/llm/tools/` implementing `ITool`:

```python
from app.llm.tools.tool_interface import ITool

class MyTool(ITool):
    async def execute(self, params: dict) -> str:
        # do something with params
        return "result string for the LLM"
```

2. Register it in `app/llm/tools/tool_factory.py`:

```python
self._tools = {
    "search_tool": SearchTool(),
    "notify_tool": NotifyTool(db, user_id),
    "my_tool": MyTool(),
}
```

3. Add the tool description to the system prompt in `app/constants.py`

## Local Development (without Docker)

If you prefer running the Python app natively:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start only Postgres + Redis in Docker
docker compose up -d postgres redis

# Update .env to use localhost instead of service names
# DATABASE_URL=postgresql+asyncpg://whats_bot:whats_bot@localhost:5432/whats_bot
# SYNC_DATABASE_URL=postgresql+psycopg2://whats_bot:whats_bot@localhost:5432/whats_bot
# REDIS_URL=redis://localhost:6379/0

alembic upgrade head
uvicorn app.main:app --reload                          # terminal 1
celery -A app.worker worker --loglevel=info            # terminal 2
celery -A app.worker beat --loglevel=info              # terminal 3
```
