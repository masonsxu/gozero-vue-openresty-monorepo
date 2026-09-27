-- Dynamic routing backed by Redis: the hash `gateway:routes` maps service
-- names to "host:port" upstreams, e.g.
--   redis-cli HSET gateway:routes user-api 10.0.0.5:8888
-- Takes effect without an nginx reload; cached for CACHE_TTL seconds in the
-- 'routes' shared dict. Falls back to the static upstream when Redis has no
-- entry or is unreachable.

local redis = require "resty.redis"

local CACHE_TTL = 5
local REDIS_PORT = 6379

local _M = {}

function _M.default_upstream()
    return os.getenv("USER_API_UPSTREAM") or "user-api:8888"
end

local function fetch_upstream(service)
    local red = redis:new()
    red:set_timeout(200)

    local ok, err = red:connect(os.getenv("REDIS_HOST") or "redis", REDIS_PORT)
    if not ok then
        ngx.log(ngx.WARN, "redis connect failed: ", err)
        return nil
    end

    local upstream, err = red:hget("gateway:routes", service)
    red:close()

    if not upstream or upstream == ngx.null then
        return nil
    end
    return upstream
end

-- Returns the upstream target (host:port) or the static upstream name.
function _M.resolve(service_name)
    local cache_key = "routes:" .. service_name
    local cached = ngx.shared.routes:get(cache_key)
    if cached then
        return cached
    end

    local upstream = fetch_upstream(service_name)
    local target = upstream or _M.default_upstream()
    ngx.shared.routes:set(cache_key, target, CACHE_TTL)
    return target
end

return _M
