from starlette.responses import Response


class AsgiProxy(Response):
    def __init__(self, app, path: str):
        super().__init__()
        self._app = app
        self._path = path

    async def __call__(self, scope, receive, send) -> None:
        inner = dict(scope)
        inner["path"] = self._path
        inner["raw_path"] = self._path.encode()
        inner["root_path"] = ""
        await self._app(inner, receive, send)
