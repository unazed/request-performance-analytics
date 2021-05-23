from aiohttp import web


nreq = 0


async def handle(request):
    global nreq
    nreq += 1
    print(f"\r{nreq} requests", end="")
    return web.Response(text="\xaa"*1536)


app = web.Application()
app.router.add_get('/', handle)
web.run_app(app)
