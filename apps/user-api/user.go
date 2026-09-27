// Code scaffolded by goctl. Safe to edit.
// goctl 1.10.2

package main

import (
	"flag"
	"fmt"
	"os"

	"user-api/internal/config"
	"user-api/internal/handler"
	"user-api/internal/svc"

	"context"
	"net/http"

	"github.com/zeromicro/go-zero/core/conf"
	"github.com/zeromicro/go-zero/rest"
	"github.com/zeromicro/go-zero/rest/httpx"
)

var configFile = flag.String("f", "etc/user-api.yaml", "the config file")

func main() {
	flag.Parse()

	var c config.Config
	conf.MustLoad(*configFile, &c)

	// Environment overrides for deployment secrets; must match the gateway.
	if s := os.Getenv("JWT_SECRET"); s != "" {
		c.Auth.JwtSecret = s
	}

	// Uniform JSON error body: {"message": "..."}, consumed by api-client.
	httpx.SetErrorHandlerCtx(func(ctx context.Context, err error) (int, any) {
		return http.StatusBadRequest, map[string]any{"message": err.Error()}
	})

	server := rest.MustNewServer(c.RestConf, rest.WithCors())
	defer server.Stop()

	ctx := svc.NewServiceContext(c)
	handler.RegisterHandlers(server, ctx)

	fmt.Printf("Starting server at %s:%d...\n", c.Host, c.Port)
	server.Start()
}
