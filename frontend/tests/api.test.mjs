// Jalankan: node --test tests/api.test.mjs   (Node 22.18+ membaca .ts langsung)
import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'

const store = new Map()
globalThis.window = {
  localStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => void store.set(k, String(v)),
    removeItem: (k) => void store.delete(k),
  },
  location: { pathname: '/beranda', assign: (p) => { globalThis.__redirect = p } },
}
const { apiFetch, tokenStore, ApiError } = await import('../src/lib/api.ts')

const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
let calls
let handler
beforeEach(() => {
  store.clear()
  globalThis.__redirect = undefined
  calls = []
  globalThis.fetch = async (url, init = {}) => {
    const auth = new Headers(init.headers).get('Authorization')
    calls.push({ url: String(url), auth, body: init.body })
    return handler(String(url), auth, init)
  }
})

test('401 karena token kedaluwarsa: refresh sekali lalu ulangi dengan token baru', async () => {
  tokenStore.set('lama', 'refresh-1')
  handler = (url, auth) => {
    if (url === '/api/identity/auth/refresh') return json(200, { access_token: 'baru', refresh_token: 'refresh-2' })
    return auth === 'Bearer baru' ? json(200, { ok: true }) : json(401, { detail: 'Token kedaluwarsa' })
  }
  assert.deepEqual(await apiFetch('/api/identity/auth/saya'), { ok: true })
  assert.equal(tokenStore.get(), 'baru')
  assert.equal(tokenStore.getRefresh(), 'refresh-2')
  assert.equal(calls.filter((c) => c.url.endsWith('/refresh')).length, 1)
})

test('banyak permintaan 401 bersamaan hanya memakai refresh token satu kali', async () => {
  tokenStore.set('lama', 'refresh-1')
  handler = async (url, auth) => {
    if (url === '/api/identity/auth/refresh') {
      await new Promise((r) => setTimeout(r, 20))
      return json(200, { access_token: 'baru', refresh_token: 'refresh-2' })
    }
    return auth === 'Bearer baru' ? json(200, { ok: true }) : json(401, {})
  }
  const hasil = await Promise.all([apiFetch('/api/a'), apiFetch('/api/b'), apiFetch('/api/c')])
  assert.equal(hasil.length, 3)
  assert.equal(calls.filter((c) => c.url.endsWith('/refresh')).length, 1)
})

test('refresh ditolak: sesi dibersihkan dan diarahkan ke login', async () => {
  tokenStore.set('lama', 'refresh-1')
  handler = (url) => (url.endsWith('/refresh') ? json(401, { detail: 'x' }) : json(401, { detail: 'Token kedaluwarsa' }))
  await assert.rejects(() => apiFetch('/api/identity/fakultas'), ApiError)
  assert.equal(tokenStore.get(), null)
  assert.equal(globalThis.__redirect, '/login')
})

test('layanan lama (micro-cred) menolak token identity: pesan jelas dan sesi TETAP', async () => {
  tokenStore.set('sah', 'refresh-1')
  handler = (url, auth) => {
    if (url.endsWith('/refresh')) return json(200, { access_token: 'sah2', refresh_token: 'refresh-2' })
    return json(401, { detail: 'invalid' })
  }
  await assert.rejects(
    () => apiFetch('/api/micro-cred/tracks'),
    (e) => e instanceof ApiError && e.status === 401 && /sedang dipindahkan/.test(e.message),
  )
  assert.equal(tokenStore.get(), 'sah2')
  assert.equal(globalThis.__redirect, undefined)
})

test('galat jaringan saat refresh tidak mengeluarkan pengguna', async () => {
  tokenStore.set('lama', 'refresh-1')
  handler = (url) => {
    if (url.endsWith('/refresh')) throw new TypeError('network')
    return json(401, {})
  }
  await assert.rejects(() => apiFetch('/api/x'), (e) => e instanceof ApiError && e.status === 0)
  assert.equal(tokenStore.get(), 'lama')
  assert.equal(globalThis.__redirect, undefined)
})

test('login (auth:false) tidak memicu refresh dan tidak mengeluarkan sesi', async () => {
  handler = () => json(401, { detail: 'Email atau sandi salah' })
  await assert.rejects(() => apiFetch('/api/identity/auth/login', { method: 'POST', json: {}, auth: false }), /Email atau sandi salah/)
  assert.equal(calls.length, 1)
})

test('isi FormData dikirim ulang utuh setelah refresh', async () => {
  tokenStore.set('lama', 'refresh-1')
  const form = new FormData()
  form.append('file', new Blob(['pdf']), 'khs.pdf')
  handler = (url, auth) => (url.endsWith('/refresh') ? json(200, { access_token: 'baru', refresh_token: 'r2' }) : auth === 'Bearer baru' ? json(200, { ok: 1 }) : json(401, {}))
  await apiFetch('/api/matkul-recommender/khs/upload', { method: 'POST', body: form })
  const unggah = calls.filter((c) => c.url.includes('khs/upload'))
  assert.equal(unggah.length, 2)
  assert.equal(unggah[1].body, form)
})
