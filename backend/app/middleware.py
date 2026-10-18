class AppPatchOverrideMiddleware:
    """WeChat wx.request supports POST, but not PATCH.

    Only an exact, single PATCH override on POST app API requests is accepted.
    Authentication and route authorization still run on the resulting PATCH.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope["type"] == "http" and scope["method"] == "POST"
                and scope.get("path", "").startswith("/api/v1/app/")):
            overrides = [value for name, value in scope.get("headers", [])
                         if name.lower() == b"x-http-method-override"]
            if overrides == [b"PATCH"]:
                scope = {**scope, "method": "PATCH"}
        await self.app(scope, receive, send)
