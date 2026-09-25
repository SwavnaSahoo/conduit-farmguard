const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || `Request failed: ${response.status}`)
  }
  return response.json()
}

export const getDashboard = () => request('/api/dashboard')
export const askFarmGuard = (question) => request('/api/ask', {
  method: 'POST',
  body: JSON.stringify({ question }),
})
