# syntax=docker/dockerfile:1

FROM golang:1.26-alpine AS builder
# Mainland-China friendly module proxy; override at build time if not needed.
ENV GOPROXY=https://goproxy.cn,direct
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/user-api .

FROM alpine:3.21
RUN addgroup -S app && adduser -S app -G app
COPY --from=builder /out/user-api /usr/local/bin/user-api
COPY etc/user-api.yaml /etc/user-api/user-api.yaml
USER app
EXPOSE 8888
ENTRYPOINT ["user-api", "-f", "/etc/user-api/user-api.yaml"]
