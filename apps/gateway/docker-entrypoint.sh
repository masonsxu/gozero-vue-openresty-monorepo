#!/bin/sh
set -e

# Derive the DNS resolver from the container network (podman aardvark-dns,
# docker embedded DNS, or any other network) and materialize nginx.conf.
DNS_RESOLVER=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)

CONF_DIR=/usr/local/openresty/nginx/conf
sed "s/__DNS_RESOLVER__/${DNS_RESOLVER}/" \
    "${CONF_DIR}/nginx.conf.template" > "${CONF_DIR}/nginx.conf"

exec openresty -g 'daemon off;'
