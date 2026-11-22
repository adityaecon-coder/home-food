"""Run the website + chat API on your laptop:  .venv/Scripts/python dev_server.py"""
import uvicorn
from fastapi.staticfiles import StaticFiles

from api.chat import app

app.mount("/", StaticFiles(directory="public", html=True), name="site")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
