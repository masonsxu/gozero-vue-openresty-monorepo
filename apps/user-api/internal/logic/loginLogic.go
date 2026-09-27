package logic

import (
	"context"
	"errors"
	"time"

	"user-api/internal/svc"
	"user-api/internal/types"

	"github.com/golang-jwt/jwt/v5"
	"github.com/zeromicro/go-zero/core/logx"
)

type LoginLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewLoginLogic(ctx context.Context, svcCtx *svc.ServiceContext) *LoginLogic {
	return &LoginLogic{
		Logger: logx.WithContext(ctx),
		ctx:    ctx,
		svcCtx: svcCtx,
	}
}

func (l *LoginLogic) Login(req *types.LoginReq) (resp *types.LoginResp, err error) {
	auth := l.svcCtx.Config.Auth
	if req.Username != auth.DemoUsername || req.Password != auth.DemoPassword {
		return nil, errors.New("invalid username or password")
	}

	now := time.Now()
	expiry := now.Add(time.Duration(auth.JwtExpireHours) * time.Hour)
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub": req.Username,
		"iat": now.Unix(),
		"exp": expiry.Unix(),
	}).SignedString([]byte(auth.JwtSecret))
	if err != nil {
		return nil, err
	}

	return &types.LoginResp{
		Token:     token,
		ExpiresIn: int64(auth.JwtExpireHours) * 3600,
	}, nil
}
