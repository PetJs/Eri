export interface User {
  id: string
  email: string
  name: string
  role: 'buyer' | 'supplier' | 'admin'
  organisation: string
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
}
