"""Rebuild the help-docs index:  .venv/Scripts/python build_index.py"""
from support_agent.rag import build_index

print(f"Index built with {build_index()} chunks.")
