// Code scaffolded by goctl. Safe to edit.
// goctl 1.10.2

package config

import "github.com/zeromicro/go-zero/rest"

type Config struct {
	rest.RestConf
	// Auth holds JWT signing material shared with the OpenResty gateway
	// via the JWT_SECRET environment variable in production.
	Auth struct {
		JwtSecret      string
		JwtExpireHours int64
		// Demo credentials replace a user store until a database is wired in.
		DemoUsername string
		DemoPassword string
	}
}
