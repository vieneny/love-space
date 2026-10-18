import { reactive } from 'vue'

const TOKEN_KEY = 'love-space.admin.access-token'
const USER_KEY = 'love-space.admin.username'

export const session = reactive({
  token: sessionStorage.getItem(TOKEN_KEY) || '',
  username: sessionStorage.getItem(USER_KEY) || '',
})

export function setSession(token: string, username: string) {
  session.token = token
  session.username = username
  sessionStorage.setItem(TOKEN_KEY, token)
  sessionStorage.setItem(USER_KEY, username)
}

export function clearSession() {
  session.token = ''
  session.username = ''
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}
