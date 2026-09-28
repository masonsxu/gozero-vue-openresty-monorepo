import { request } from './client'
import type { LoginReq, LoginResp, UserInfoResp } from './generated/userComponents'

export { ApiError, configureClient } from './client'
export type { ClientOptions } from './client'
export type { LoginReq, LoginResp, UserInfoResp } from './generated/userComponents'
export * from './forecast'

// Route paths mirror the .api contract; the gateway strips the /api prefix
// before proxying to user-api.
export function login(req: LoginReq): Promise<LoginResp> {
  return request<LoginResp>('POST', '/auth/login', req)
}

export function userInfo(): Promise<UserInfoResp> {
  return request<UserInfoResp>('GET', '/user/info')
}

export function ping(): Promise<null> {
  return request<null>('GET', '/user/ping')
}
