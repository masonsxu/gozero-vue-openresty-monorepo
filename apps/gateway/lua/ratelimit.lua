-- Per-IP rate limiting with lua-resty-limit-traffic (leaky bucket:
-- rate 10 req/s, burst 20). Counters live in the 'limit_store' shared dict.

local limit_req = require "resty.limit.req"

local RATE = 10
local BURST = 20

local _M = {}

function _M.check()
    local lim, err = limit_req.new("limit_store", RATE, BURST)
    if not lim then
        ngx.log(ngx.ERR, "failed to create limiter: ", err)
        return true -- fail open: never take the site down over the limiter
    end

    local delay, err = lim:incoming(ngx.var.binary_remote_addr, true)
    if not delay then
        if err == "rejected" then
            return false
        end
        ngx.log(ngx.ERR, "limiter error: ", err)
        return true
    end

    if delay > 0 then
        -- delay is in seconds; exceeding the burst means queuing, not rejecting
        ngx.sleep(delay)
    end
    return true
end

return _M
