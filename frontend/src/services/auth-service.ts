import { apiFetch, tokenStore } from '@/src/lib/api'

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  nim: string | null
  faculty: string | null
  study_program: string | null
  role: string
}

interface TokenResponse {
  access_token: string
  refresh_token?: string | null
  token_type: string
  expires_in: number
}

export interface RegisterPayload {
  email: string
  password: string
  full_name: string
  nim: string
  faculty: string
  study_program: string
}

export const authService = {
  async register(payload: RegisterPayload): Promise<void> {
    await apiFetch('/api/micro-cred/auth/register', { method: 'POST', json: payload, auth: false })
  },

  async login(email: string, password: string): Promise<AuthUser> {
    const result = await apiFetch<{ user: AuthUser; tokens: TokenResponse }>('/api/micro-cred/auth/login', {
      method: 'POST',
      json: { email, password },
      auth: false,
    })
    tokenStore.set(result.tokens.access_token, result.tokens.refresh_token)
    return result.user
  },

  async me(): Promise<AuthUser> {
    const result = await apiFetch<{ user: AuthUser }>('/api/micro-cred/auth/me')
    return result.user
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiFetch('/api/micro-cred/auth/change-password', {
      method: 'POST',
      json: { current_password: currentPassword, new_password: newPassword },
    })
  },

  logout() {
    tokenStore.clear()
  },
}
