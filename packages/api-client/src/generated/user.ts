import { webapi } from "./gocliRequest"
import * as components from "./userComponents"
export * from "./userComponents"

/**
 * @description 
 * @param req
 */
export function login(req: components.LoginReq) {
	return webapi.post<components.LoginResp>(`/auth/login`, req)
}

/**
 * @description 
 */
export function userInfo() {
	return webapi.get<components.UserInfoResp>(`/user/info`)
}

/**
 * @description 
 */
export function ping() {
	return webapi.get<null>(`/user/ping`)
}
