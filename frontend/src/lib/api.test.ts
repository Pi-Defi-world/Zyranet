import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, clearToken, getToken, setToken } from './api'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api client', () => {
  beforeEach(() => {
    clearToken()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('stores and clears the JWT in localStorage', () => {
    expect(getToken()).toBeNull()
    setToken('abc.def.ghi')
    expect(localStorage.getItem('zyranet_token')).toBe('abc.def.ghi')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('sends the Authorization header on authenticated requests', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse(200, { total: 0, items: [] }))

    setToken('token-123')
    await api.listDevices({})

    const [url, init] = fetchMock.mock.calls[0]!
    expect(String(url)).toBe('/api/v1/devices')
    const headers = new Headers(init!.headers)
    expect(headers.get('Authorization')).toBe('Bearer token-123')
  })

  it('throws ApiError with the backend detail message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse(401, { detail: 'Invalid username or password' }),
    )

    const err = await api.login('admin', 'wrong').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as Error).message).toBe('Invalid username or password')
  })

  it('serialises filter params', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse(200, { total: 0, items: [] }))

    await api.listDevices({ q: 'sw', online: true, location_id: 2 })

    const [url] = fetchMock.mock.calls[0]!
    expect(String(url)).toBe('/api/v1/devices?q=sw&online=true&location_id=2')
  })
})
