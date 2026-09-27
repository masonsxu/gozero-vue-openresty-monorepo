FROM openresty/openresty:alpine

COPY conf/nginx.conf.template /usr/local/openresty/nginx/conf/nginx.conf.template
# vendored pure-lua libraries (resty/limit/req.lua from lua-resty-limit-traffic)
COPY vendor/ /usr/local/openresty/lualib/
COPY lua/ /usr/local/openresty/nginx/lua/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
