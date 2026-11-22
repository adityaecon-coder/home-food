"""
The chat API that the website's chat widget calls.

POST /api/chat  with  {"message": "...", "history": [{"role": "user"|"tanny", "text": "..."}]}
returns {"reply": "..."}.

The web server keeps no memory between requests, so the widget sends the recent history
every time and we pass it to Tanny along with the new message.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Make the project root importable (so 'support_agent' is found on Vercel too).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from support_agent.agent import root_agent
from support_agent.escalation import find_sensitive_word
from support_agent.tools import create_ticket

app = FastAPI()
APP_NAME = "tiffingo"


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


async def ask_tanny(message: str, history: list[dict]) -> str:
    # A fresh session per request; the earlier conversation is included as text.
    # Only the last 10 turns are used, and every line is cut short.
    lines = []
    for turn in history[-10:]:
        who = "Customer" if turn.get("role") == "user" else "Tanny"
        lines.append(f"{who}: {str(turn.get('text', ''))[:800]}")
    prompt = message[:1500]
    if lines:
        prompt = ("Conversation so far:\n" + "\n".join(lines)
                  + f"\n\nCustomer's new message: {prompt}")

    service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=service)
    user_id, session_id = "web", str(uuid.uuid4())
    await service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

    reply = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            reply = "".join(p.text or "" for p in event.content.parts)
    return reply.strip()


@app.post("/api/chat")
@app.post("/")
async def chat(req: ChatRequest):
    # Sensitive words (legal, fraud, health...) go straight to a human executive. No AI call.
    hit = find_sensitive_word(req.message)
    if hit:
        word, priority = hit
        ticket = create_ticket(req.message[:300], f"sensitive word: {word}", priority)
        return {
            "escalated": True,
            "reply": (f"This needs one of our support executives. I've raised ticket {ticket['ticket_id']} "
                      "and an executive will contact you within 24 hours. "
                      "Please don't share card numbers or OTPs in this chat."),
        }
    # Gemini sometimes says "busy" (503) or "quota" (429). Try up to 3 times before giving up.
    for attempt in range(3):
        try:
            reply = await ask_tanny(req.message, req.history)
            return {"reply": reply or "Sorry, I couldn't answer that. Please try again."}
        except Exception as e:
            print(f"chat error (attempt {attempt + 1}):", repr(e)[:300])
            await asyncio.sleep(3 * (attempt + 1))
    return {"reply": "Sorry, I'm a bit busy right now. Please try again in a minute."}
