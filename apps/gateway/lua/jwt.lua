-- Minimal HS256 JWT verifier using OpenSSL HMAC via FFI.
-- Verifies signature and expiry only; token issuing lives in user-api.
-- Algorithm is pinned to HS256 to reject alg-confusion (e.g. "none").

local ffi = require "ffi"
local cjson = require "cjson.safe"

ffi.cdef[[
typedef struct evp_md_st EVP_MD;
const EVP_MD *EVP_sha256(void);
unsigned char *HMAC(const EVP_MD *evp_md, const void *key, int key_len,
                    const unsigned char *data, size_t data_len,
                    unsigned char *md, unsigned int *md_len);
int memcmp(const void *s1, const void *s2, size_t n);
]]

local DIGEST_LEN = 32

local function b64url_decode(s)
    s = s:gsub("-", "+"):gsub("_", "/")
    local rem = #s % 4
    if rem == 1 then
        return nil
    end
    if rem == 2 then
        s = s .. "=="
    elseif rem == 3 then
        s = s .. "="
    end
    return ngx.decode_base64(s)
end

local function hmac_sha256(key, data)
    local out = ffi.new("unsigned char[?]", DIGEST_LEN)
    local out_len = ffi.new("unsigned int[1]")
    ffi.C.HMAC(ffi.C.EVP_sha256(), key, #key, data, #data, out, out_len)
    return ffi.string(out, out_len[0])
end

local _M = {}

-- Returns the claims table, or nil + reason.
function _M.verify_hs256(token, secret)
    local header_b64, payload_b64, sig_b64 =
        token:match("^([^%.]+)%.([^%.]+)%.([^%.]+)$")
    if not header_b64 then
        return nil, "malformed token"
    end

    local header = cjson.decode(b64url_decode(header_b64) or "")
    if type(header) ~= "table" or header.alg ~= "HS256" then
        return nil, "unsupported alg"
    end

    local sig = b64url_decode(sig_b64)
    if not sig or #sig ~= DIGEST_LEN then
        return nil, "malformed signature"
    end

    local signing_input = header_b64 .. "." .. payload_b64
    local expected = hmac_sha256(secret, signing_input)
    if ffi.C.memcmp(sig, expected, DIGEST_LEN) ~= 0 then
        return nil, "signature mismatch"
    end

    local payload = cjson.decode(b64url_decode(payload_b64) or "")
    if type(payload) ~= "table" then
        return nil, "malformed payload"
    end
    if payload.exp and payload.exp <= ngx.time() then
        return nil, "token expired"
    end
    return payload
end

return _M
