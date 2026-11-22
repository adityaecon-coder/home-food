# Tanny (TiffinGo support agent)

A TiffinGo demo website with a chat widget powered by Tanny (Google ADK + Gemini).

Run locally: `.venv/Scripts/python dev_server.py` then open http://127.0.0.1:8000

Deploy: Vercel (static site in `public/`, chat API in `api/chat.py`). Set GOOGLE_API_KEY and GEMINI_MODEL in Vercel env vars.
