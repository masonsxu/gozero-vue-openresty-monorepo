-- Access-phase entry point: rate limit -> JWT auth -> dynamic route resolve.
-- Runs for every /api/ request; public paths skip JWT verification.

local ratelimit = require "lua.ratelimit"
local auth = require "lua.auth"
local router = require "lua.router"

local PUBLIC_PATHS = {
    ["/auth/login"] = true,
    ["/user/ping"] = true,
}

local function respond(status, message)
    ngx.status = status
    ngx.header.content_type = "application/json"
    ngx.say(string.format('{"message":"%s"}', message))
    ngx.exit(status)
end

if not ratelimit.check() then
    return respond(429, "rate limit exceeded")
end

-- ngx.var.uri is the rewritten URI (rewrite phase runs before access phase)
if not PUBLIC_PATHS[ngx.var.uri] then
    local claims, err = auth.verify()
    if not claims then
        ngx.log(ngx.WARN, "jwt verification failed: ", err or "unknown")
        return respond(401, "unauthorized")
    end
    ngx.var.x_user = claims.sub or ""
end

local ok, upstream = pcall(router.resolve, "user-api")
if ok and upstream then
    ngx.var.api_upstream = upstream
else
    ngx.var.api_upstream = router.default_upstream()
end
