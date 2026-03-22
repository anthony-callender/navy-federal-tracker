import { useState, useEffect } from 'react'
import { api } from '../api'
import { fmt } from '../utils/formatters'

export default function TransactionsTab({ month, categories, monthlyExpenses }) {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    api.getTransactions({ month }).then(data => {
      setTransactions(data)
      setLoading(false)
    })
  }

  useEffect(() => { load() }, [month])

  const getCategoryColor = (categoryName) => {
    const cat = categories.find(c => c.name === categoryName)
    return cat ? cat.color : '#9ca3af'
  }

  const handleCategoryChange = async (tx, newCat) => {
    await api.updateTransaction(tx.id, { category: newCat })
    setTransactions(prev => prev.map(t => t.id === tx.id ? { ...t, category: newCat } : t))
  }

  const handleMonthlyExpenseChange = async (tx, meId) => {
    const val = meId === '' ? null : parseInt(meId)
    await api.updateTransaction(tx.id, { monthly_expense_id: val })
    const me = monthlyExpenses.find(m => m.id === val)
    setTransactions(prev => prev.map(t => t.id === tx.id ? { ...t, monthly_expense_id_joined: val, monthly_expense_name: me?.name || null } : t))
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading transactions...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Transactions — {transactions.length} records</h2>
        <button onClick={load} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700">Refresh</button>
      </div>
      <div className="overflow-x-auto rounded-lg shadow">
        <table className="w-full text-sm bg-white">
          <thead className="bg-[#1a3a5c] text-white">
            <tr>
              {['Date','Merchant','Amount','Type','Category','Monthly Expense','Account'].map(h => (
                <th key={h} className="px-3 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">No transactions found for this month</td></tr>
            ) : transactions.map(tx => {
              const color = getCategoryColor(tx.category)
              return (
                <tr key={tx.id} style={{ backgroundColor: color + '26' }} className="border-b border-gray-100 hover:brightness-95">
                  <td className="px-3 py-2 whitespace-nowrap font-mono text-xs">{tx.date}</td>
                  <td className="px-3 py-2 font-medium max-w-[180px] truncate">{tx.merchant || tx.description}</td>
                  <td className={`px-3 py-2 font-semibold whitespace-nowrap ${tx.transaction_type === 'credit' ? 'text-green-600' : 'text-red-600'}`}>
                    {tx.transaction_type === 'credit' ? '+' : '-'}{fmt(tx.amount)}
                  </td>
                  <td className="px-3 py-2 capitalize text-gray-600">{tx.transaction_type}</td>
                  <td className="px-3 py-2">
                    <select
                      value={tx.category || ''}
                      onChange={e => handleCategoryChange(tx, e.target.value)}
                      className="text-xs border border-gray-300 rounded px-1 py-0.5 bg-white"
                    >
                      {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={tx.monthly_expense_id_joined ?? ''}
                      onChange={e => handleMonthlyExpenseChange(tx, e.target.value)}
                      className="text-xs border border-gray-300 rounded px-1 py-0.5 bg-white"
                    >
                      <option value="">— Variable —</option>
                      {monthlyExpenses.map(me => <option key={me.id} value={me.id}>{me.name}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2 text-gray-500 text-xs">{tx.account}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
