from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import aiohttp_jinja2
import jinja2
from aiohttp import web


routers = web.RouteTableDef()


@routers.get("/{username}")
@aiohttp_jinja2.template("example.html")
async def greet_user(request: web.Request) -> Dict[str, Any]:
    context = {
        "username": request.match_info.get("usernmae", ""),
        "current_date": datetime.now().date(),
    }
    return context


async def init_app() -> web.Application:
    app = web.Application()
    app.add_routes(routers)
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader(str(Path.cwd() / "templates"))
    )
    return app


web.run_app(init_app())
