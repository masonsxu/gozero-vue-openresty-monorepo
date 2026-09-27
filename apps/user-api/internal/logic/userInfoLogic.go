package logic

import (
	"context"
	"errors"
	"strings"

	"user-api/internal/svc"
	"user-api/internal/types"

	"github.com/golang-jwt/jwt/v5"
	"github.com/zeromicro/go-zero/core/logx"
)

type contextKey string

const (
	CtxKeyXUser         contextKey = "X-User"
	CtxKeyAuthorization contextKey = "Authorization"
)

type UserInfoLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewUserInfoLogic(ctx context.Context, svcCtx *svc.ServiceContext) *UserInfoLogic {
	return &UserInfoLogic{
		Logger: logx.WithContext(ctx),
		ctx:    ctx,
		svcCtx: svcCtx,
	}
}

func (l *UserInfoLogic) UserInfo(req *types.UserInfoReq) (resp *types.UserInfoResp, err error) {
	username, _ := l.ctx.Value(CtxKeyXUser).(string)
	if username == "" {
		// Direct access without the gateway: parse the bearer token ourselves.
		header, _ := l.ctx.Value(CtxKeyAuthorization).(string)
		username, err = subjectFromToken(header, l.svcCtx.Config.Auth.JwtSecret)
		if err != nil {
			return nil, err
		}
	}

	return &types.UserInfoResp{
		Id:       1,
		Username: username,
		Email:    username + "@example.com",
	}, nil
}

func subjectFromToken(header, secret string) (string, error) {
	if !strings.HasPrefix(header, "Bearer ") {
		return "", errors.New("unauthorized")
	}
	token, err := jwt.Parse(strings.TrimPrefix(header, "Bearer "), func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return []byte(secret), nil
	})
	if err != nil || !token.Valid {
		return "", errors.New("invalid token")
	}
	sub, err := token.Claims.GetSubject()
	if err != nil || sub == "" {
		return "", errors.New("invalid token subject")
	}
	return sub, nil
}
