"""
Music Bank — Jinja2 template helper
"""
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
)


def respond(template_name: str, context: dict) -> HTMLResponse:
    ctx = {"request": context.get("request")}
    ctx.update({k: v for k, v in context.items() if k != "request"})
    template = _jinja_env.get_template(template_name)
    return HTMLResponse(content=template.render(**ctx))
