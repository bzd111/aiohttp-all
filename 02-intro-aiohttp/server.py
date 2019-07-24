from aiohttp import web


routes = web.RouteTableDef()


@routes.get("/")
async def handler(request):
    return web.Response(text="Hello, World")


@routes.get("/{username}/{password}")
async def greet_user(request: web.Request) -> web.Response:
    user = request.match_info.get("username", "")
    password = request.match_info.get("password", "")
    page_num = request.rel_url.query.get("page", "")
    return web.Response(text=f"Hello, {user} {password} {page_num}")


@routes.post("/json")
async def handler_json(request):
    print(request)
    args = await request.json()
    print(args)
    data = {"value": args.get("key", "none")}
    return web.json_response(data)


@routes.post("/add_user")
async def add_user(request: web.Request) -> web.Response:
    data = await request.post()
    username = data.get("username")
    return web.Response(text=f"{username} was added")


async def init_app():
    app = web.Application()
    app.add_routes(routes)
    return app


web.run_app(init_app())
