const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'https://eri-xw3i.onrender.com'

export class ApiError extends Error {
  status: number

  body?: unknown

  constructor(
    status: number,
    message: string,
    body?: unknown,
  ) {
    super(message)
    this.status = status
    this.body = body
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })

  if (!res.ok) {
    let body: unknown
    try { body = await res.json() } catch { /* ignore */ }
    throw new ApiError(res.status, `${res.status} ${res.statusText}`, body)
  }

  return res.json() as Promise<T>
}

export async function apiFetchForm<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    let body: unknown
    try { body = await res.json() } catch { /* ignore */ }
    throw new ApiError(res.status, `${res.status} ${res.statusText}`, body)
  }

  return res.json() as Promise<T>
}
