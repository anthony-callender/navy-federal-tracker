const BASE = '/api'

const getToken = () => localStorage.getItem('auth_token') || ''

const h = (extra = {}) => ({ 'X-Auth-Token': getToken(), ...extra })
const jh = () => ({ 'Content-Type': 'application/json', 'X-Auth-Token': getToken() })

const req = (url, opts = {}) => fetch(url, opts).then(r => r.json())

export const api = {
  // auth
  login: (username, password) => req(`${BASE}/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) }),

  // transactions
  getTransactions: (params = {}) => req(`${BASE}/transactions?` + new URLSearchParams(params), { headers: h() }),
  updateTransaction: (id, body) => req(`${BASE}/transactions/${id}`, { method: 'PATCH', headers: jh(), body: JSON.stringify(body) }),

  // categories
  getCategories: () => req(`${BASE}/categories`, { headers: h() }),
  createCategory: (body) => req(`${BASE}/categories`, { method: 'POST', headers: jh(), body: JSON.stringify(body) }),
  updateCategory: (id, body) => req(`${BASE}/categories/${id}`, { method: 'PATCH', headers: jh(), body: JSON.stringify(body) }),
  deleteCategory: (id) => req(`${BASE}/categories/${id}`, { method: 'DELETE', headers: h() }),

  // monthly expenses
  getMonthlyExpenses: () => req(`${BASE}/monthly-expenses`, { headers: h() }),
  createMonthlyExpense: (body) => req(`${BASE}/monthly-expenses`, { method: 'POST', headers: jh(), body: JSON.stringify(body) }),
  updateMonthlyExpense: (id, body) => req(`${BASE}/monthly-expenses/${id}`, { method: 'PATCH', headers: jh(), body: JSON.stringify(body) }),
  deleteMonthlyExpense: (id) => req(`${BASE}/monthly-expenses/${id}`, { method: 'DELETE', headers: h() }),

  // debts
  getDebts: () => req(`${BASE}/debts`, { headers: h() }),
  createDebt: (body) => req(`${BASE}/debts`, { method: 'POST', headers: jh(), body: JSON.stringify(body) }),
  updateDebt: (id, body) => req(`${BASE}/debts/${id}`, { method: 'PATCH', headers: jh(), body: JSON.stringify(body) }),
  deleteDebt: (id) => req(`${BASE}/debts/${id}`, { method: 'DELETE', headers: h() }),

  // config
  getConfig: (key) => req(`${BASE}/config/${key}`, { headers: h() }),
  setConfig: (key, value) => req(`${BASE}/config/${key}`, { method: 'PATCH', headers: jh(), body: JSON.stringify({ value }) }),

  // classify
  classifyTransactions: (month) => req(`${BASE}/classify-transactions?month=${month}`, { method: 'POST', headers: h() }),
  clearClassifications: (month) => req(`${BASE}/clear-classifications?month=${month}`, { method: 'POST', headers: h() }),

  // dashboard
  getDashboardTotals: (month) => req(`${BASE}/dashboard/totals?month=${month}`, { headers: h() }),
  getVariableByCategory: () => req(`${BASE}/dashboard/variable-by-category`, { headers: h() }),
  getMonthlyByExpense: () => req(`${BASE}/dashboard/monthly-by-expense`, { headers: h() }),
  getFreeSpending: (month) => req(`${BASE}/dashboard/free-spending?month=${month}`, { headers: h() }),
  getChartData: (offset = 0) => req(`${BASE}/dashboard/chart-data?offset=${offset}`, { headers: h() }),
  getYearlyChartData: () => req(`${BASE}/dashboard/chart-data/yearly`, { headers: h() }),
}
