"""Ponto de entrada para o Render (comando padrão: gunicorn app:app)."""

from dashboard_fitbit import server as app  # noqa: F401
