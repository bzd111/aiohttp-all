import sqlite3
from pathlib import Path
from typing import Any, AsyncIterator, Dict

import aiohttp_jinja2
import aiosqlite
import jinja2
from aiohttp import web


router = web.RouteTableDef()


async def fetch_post(db: aiosqlite.Connection, post_id: int) -> Dict[str, Any]:
    async with db.execute(
        "select owner, editor, title, text from posts where id = ?", [post_id]
    ) as cursor:
        row = await cursor.fetchone()
        print(row)
        if row is None:
            raise RuntimeError(f"Post {post_id} does not exist")
        return {
            "id": post_id,
            "owner": row["owner"],
            "editor": row["editor"],
            "title": row["title"],
            "text": row["text"],
        }


@router.get("/")
@aiohttp_jinja2.template("index.html")
async def index(request: web.Request) -> Dict[str, Any]:
    ret = []
    db = request.config_dict["DB"]
    async with db.execute("select id, owner, editor, title from posts") as cursor:
        async for row in cursor:
            ret.append(
                {
                    "id": row["id"],
                    "owner": row["owner"],
                    "editor": row["editor"],
                    "title": row["title"],
                }
            )
    return {"posts": ret}


@router.get("/new")
@aiohttp_jinja2.template("new.html")
async def new_post(request: web.Request) -> Dict[str, Any]:
    return {}


@router.post("/new")
@aiohttp_jinja2.template("edit.html")
async def new_post_apply(request: web.Request) -> Dict[str, Any]:
    db = request.config_dict["DB"]
    post = await request.post()
    owner = "Anonymous"
    await db.execute(
        "insert into posts (owner, editor, title, text) values (?,?,?,?)",
        [owner, owner, post["title"], post["text"]],
    )
    await db.commit()
    raise web.HTTPSeeOther(location=f"/")


@router.get("/{post}")
@aiohttp_jinja2.template("view.html")
async def view_post(request: web.Request) -> Dict[str, Any]:
    post_id = request.match_info["post"]
    if post_id.endswith(".ico"):
        raise web.HTTPSeeOther(location=f"/")
    db = request.config_dict["DB"]
    return {"post": await fetch_post(db, post_id)}


@router.get("/{post}/edit")
@aiohttp_jinja2.template("edit.html")
async def edit_post(request: web.Request) -> Dict[str, Any]:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    return {"post": await fetch_post(db, post_id)}


@router.post("/{post}/edit")
async def edit_post_apply(request: web.Request) -> web.Response:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    post = await request.post()
    await db.execute(
        "update posts set title=?, text=? where id =?",
        [post["title"], post["text"], post_id],
    )
    await db.commit()
    raise web.HTTPSeeOther(location=f"/{post_id}")


@router.get("/{post}/delete")
async def delete_post(request: web.Request) -> web.Response:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    await db.execute("delete from posts where id=?", [post_id])
    raise web.HTTPSeeOther(location=f"/")


def get_db_path() -> Path:
    here = Path.cwd()
    return here / "db.sqlite3"


async def init_db(app: web.Application) -> AsyncIterator[None]:
    sqlite_db = get_db_path()
    db = await aiosqlite.connect(sqlite_db)
    db.row_factory = aiosqlite.Row
    app["DB"] = db
    yield
    await db.close()


async def init_app() -> web.Application:
    app = web.Application()
    app.add_routes(router)
    app.cleanup_ctx.append(init_db)
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader(str(Path.cwd() / "templates"))
    )
    return app


def try_make_db() -> None:
    sqlite_db = get_db_path()
    if sqlite_db.exists():
        return

    with sqlite3.connect(sqlite_db) as conn:
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            title TEXT,
            text TEXT,
            owner TEXT,
            editor TEXT)
        """
        )
        conn.commit()


try_make_db()


web.run_app(init_app())
