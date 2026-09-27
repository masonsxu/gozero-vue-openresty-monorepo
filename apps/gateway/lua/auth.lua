-- JWT verification at the gateway. The token is issued by user-api's
-- /auth/login and signed with the HS256 secret shared via JWT_SECRET.

local jwt = require "lua.jwt"

local _M = {}

local function shared_secret()
    return os.getenv("JWT_SECRET") or "dev-only-jwt-secret-change-me"
end

-- Returns the verified claims table, or nil + reason.
function _M.verify()
    local header = ngx.var.http_authorization
    if not header or header:sub(1, 7) ~= "Bearer " then
        return nil, "missing bearer token"
    end

    return jwt.verify_hs256(header:sub(8), shared_secret())
end

return _M
