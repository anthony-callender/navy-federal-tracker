const BASE = '/api'

export const api = {
  // transactions
  getTransactions: (params = {}) => fetch(`${BASE}/transactions?` + new URLSearchParams(params)).then(r => r.json()),
  updateTransaction: (id, body) => fetch(`${BASE}/transactions/${id}`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),

  // categories
  getCategories: () => fetch(`${BASE}/categories`).then(r => r.json()),
  createCategory: (body) => fetch(`${BASE}/categories`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  updateCategory: (id, body) => fetch(`${BASE}/categories/${id}`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  deleteCategory: (id) => fetch(`${BASE}/categories/${id}`, { method: 'DELETE' }).then(r => r.json()),

  // monthly expenses
  getMonthlyExpenses: () => fetch(`${BASE}/monthly-expenses`).then(r => r.json()),
  createMonthlyExpense: (body) => fetch(`${BASE}/monthly-expenses`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  updateMonthlyExpense: (id, body) => fetch(`${BASE}/monthly-expenses/${id}`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  deleteMonthlyExpense: (id) => fetch(`${BASE}/monthly-expenses/${id}`, { method: 'DELETE' }).then(r => r.json()),

  // debts
  getDebts: () => fetch(`${BASE}/debts`).then(r => r.json()),
  createDebt: (body) => fetch(`${BASE}/debts`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  updateDebt: (id, body) => fetch(`${BASE}/debts/${id}`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  deleteDebt: (id) => fetch(`${BASE}/debts/${id}`, { method: 'DELETE' }).then(r => r.json()),

  // classify
  classifyTransactions: (month) => fetch(`${BASE}/classify-transactions?month=${month}`, { method: 'POST' }).then(r => r.json()),
  clearClassifications: (month) => fetch(`${BASE}/clear-classifications?month=${month}`, { method: 'POST' }).then(r => r.json()),

  // dashboard
  getDashboardTotals: (month) => fetch(`${BASE}/dashboard/totals?month=${month}`).then(r => r.json()),
  getVariableByCategory: () => fetch(`${BASE}/dashboard/variable-by-category`).then(r => r.json()),
  getMonthlyByExpense: () => fetch(`${BASE}/dashboard/monthly-by-expense`).then(r => r.json()),
  getFreeSpending: (month) => fetch(`${BASE}/dashboard/free-spending?month=${month}`).then(r => r.json()),
  getChartData: () => fetch(`${BASE}/dashboard/chart-data`).then(r => r.json()),
}
