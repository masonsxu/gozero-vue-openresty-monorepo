// Code scaffolded by goctl. Safe to edit.
// goctl 1.10.2

package handler

import (
	"context"
	"net/http"

	"user-api/internal/logic"
	"user-api/internal/svc"
	"user-api/internal/types"

	"github.com/zeromicro/go-zero/rest/httpx"
)

func userInfoHandler(svcCtx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req types.UserInfoReq
		if err := httpx.Parse(r, &req); err != nil {
			httpx.ErrorCtx(r.Context(), w, err)
			return
		}

		// The gateway injects X-User after JWT verification; the
		// Authorization header is kept as a fallback for direct access.
		ctx := context.WithValue(r.Context(), logic.CtxKeyXUser, r.Header.Get("X-User"))
		ctx = context.WithValue(ctx, logic.CtxKeyAuthorization, r.Header.Get("Authorization"))

		l := logic.NewUserInfoLogic(ctx, svcCtx)
		resp, err := l.UserInfo(&req)
		if err != nil {
			httpx.ErrorCtx(ctx, w, err)
		} else {
			httpx.OkJsonCtx(ctx, w, resp)
		}
	}
}
