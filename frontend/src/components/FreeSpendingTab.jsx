import { useState, useEffect } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../api'
import { fmt } from '../utils/formatters'

function DebtModal({ onClose, onSave }) {
  const [form, setForm] = useState({ name: '', amount_owed: '', creditor: '', due_date: '', notes: '' })
  const handleSubmit = async (e) => {
    e.preventDefault()
    await onSave({ ...form, amount_owed: parseFloat(form.amount_owed) })
    onClose()
  }
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 className="font-bold text-lg mb-4">Add Debt</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          {[['name','Name *','text'],['amount_owed','Amount Owed *','number'],['creditor','Creditor','text'],['due_date','Due Date','date'],['notes','Notes','text']].map(([key,label,type]) => (
            <div key={key}>
              <label className="block text-sm text-gray-600 mb-1">{label}</label>
              <input type={type} value={form[key]} onChange={e => setForm({...form,[key]:e.target.value})}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" required={label.includes('*')} />
            </div>
          ))}
          <div className="flex gap-2 pt-2">
            <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded text-sm hover:bg-blue-700">Save</button>
            <button type="button" onClick={onClose} className="flex-1 border border-gray-300 py-2 rounded text-sm hover:bg-gray-50">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function FreeSpendingTab({ month }) {
  const [status, setStatus] = useState(null)
  const [debts, setDebts] = useState([])
  const [chartData, setChartData] = useState([])
  const [chartType, setChartType] = useState('bar')
  const [viewMode, setViewMode] = useState('monthly') // 'monthly' | 'yearly'
  const [offset, setOffset] = useState(0)
  const [hasPrev, setHasPrev] = useState(false)
  const [hasNext, setHasNext] = useState(false)
  const [showDebtModal, setShowDebtModal] = useState(false)

  const loadChart = (mode, off) => {
    if (mode === 'yearly') {
      api.getYearlyChartData().then(r => { setChartData(r.data); setHasPrev(false); setHasNext(false) })
    } else {
      api.getChartData(off).then(r => { setChartData(r.data); setHasPrev(r.has_prev); setHasNext(r.has_next) })
    }
  }

  const load = () => {
    api.getFreeSpending(month).then(setStatus)
    api.getDebts().then(setDebts)
    loadChart(viewMode, offset)
  }

  useEffect(() => { load() }, [month])
  useEffect(() => { loadChart(viewMode, offset) }, [viewMode, offset])

  const handleAddDebt = async (body) => {
    await api.createDebt(body)
    api.getDebts().then(setDebts)
  }

  const handleDeleteDebt = async (id) => {
    await api.deleteDebt(id)
    setDebts(prev => prev.filter(d => d.id !== id))
  }

  const ftsp = status?.free_to_spend ?? 0
  const ftspColor = ftsp > 200 ? 'text-green-600' : ftsp > 0 ? 'text-yellow-600' : 'text-red-600'
  const ftspBg = ftsp > 200 ? 'bg-green-50 border-green-200' : ftsp > 0 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'

  return (
    <div className="space-y-6">
      {/* Big metric */}
      <div className={`rounded-xl border-2 p-8 text-center ${ftspBg}`}>
        <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Free to Spend</p>
        <p className={`text-6xl font-bold ${ftspColor}`}>{fmt(ftsp)}</p>
        <div className="flex justify-center gap-8 mt-6 text-sm text-gray-600">
          <div><span className="text-gray-400">Income</span><br /><span className="font-semibold">{fmt(status?.income)}</span></div>
          <div className="text-gray-300 self-center text-2xl">−</div>
          <div><span className="text-gray-400">Fixed</span><br /><span className="font-semibold">{fmt(status?.total_fixed)}</span></div>
          <div className="text-gray-300 self-center text-2xl">−</div>
          <div><span className="text-gray-400">Variable</span><br /><span className="font-semibold">{fmt(status?.total_variable)}</span></div>
        </div>
      </div>

      {/* Debts */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
          <h3 className="font-semibold text-gray-800">Debts Tracker</h3>
          <button onClick={() => setShowDebtModal(true)} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700">+ Add Debt</button>
        </div>
        {debts.length === 0 ? (
          <p className="text-center py-8 text-gray-400 text-sm">No debts tracked</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>{['Name','Amount Owed','Creditor','Due Date','Notes',''].map(h => <th key={h} className="px-4 py-2 text-left text-gray-600 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {debts.map(d => (
                <tr key={d.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{d.name}</td>
                  <td className="px-4 py-2 text-red-600 font-semibold">{fmt(d.amount_owed)}</td>
                  <td className="px-4 py-2 text-gray-600">{d.creditor || '—'}</td>
                  <td className="px-4 py-2 text-gray-600">{d.due_date || '—'}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{d.notes || '—'}</td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleDeleteDebt(d.id)} className="text-red-500 hover:text-red-700 text-xs">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
          <h3 className="font-semibold text-gray-800">Income vs Spending</h3>
          <div className="flex gap-2 flex-wrap">
            {/* View mode */}
            {['monthly','yearly'].map(v => (
              <button key={v} onClick={() => { setViewMode(v); setOffset(0) }}
                className={`px-3 py-1 rounded text-sm capitalize ${viewMode === v ? 'bg-[#1a3a5c] text-white' : 'border border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                {v}
              </button>
            ))}
            <div className="w-px bg-gray-200 mx-1" />
            {/* Chart type */}
            {['bar','line'].map(t => (
              <button key={t} onClick={() => setChartType(t)}
                className={`px-3 py-1 rounded text-sm capitalize ${chartType === t ? 'bg-blue-600 text-white' : 'border border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                {t}
              </button>
            ))}
            {/* Pagination — only shown in monthly mode */}
            {viewMode === 'monthly' && (
              <>
                <div className="w-px bg-gray-200 mx-1" />
                <button onClick={() => setOffset(o => o + 1)} disabled={!hasPrev}
                  className="px-3 py-1 rounded text-sm border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-30">← Older</button>
                <button onClick={() => setOffset(o => Math.max(0, o - 1))} disabled={!hasNext}
                  className="px-3 py-1 rounded text-sm border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-30">Newer →</button>
              </>
            )}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          {chartType === 'bar' ? (
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis yAxisId="left" tickFormatter={v => `$${(v/1000).toFixed(1)}k`} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={v => `$${(v/1000).toFixed(1)}k`} />
              <Tooltip formatter={v => fmt(v)} />
              <Legend />
              <Bar yAxisId="left" dataKey="income" name="Income" fill="#22c55e" />
              <Bar yAxisId="left" dataKey="spending" name="Spending" fill="#ef4444" />
              <Line yAxisId="right" type="monotone" dataKey="balance" name="Balance" stroke="#1a3a5c" strokeWidth={2} dot />
            </BarChart>
          ) : (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis yAxisId="left" tickFormatter={v => `$${(v/1000).toFixed(1)}k`} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={v => `$${(v/1000).toFixed(1)}k`} />
              <Tooltip formatter={v => fmt(v)} />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="income" name="Income" stroke="#22c55e" strokeWidth={2} dot />
              <Line yAxisId="left" type="monotone" dataKey="spending" name="Spending" stroke="#ef4444" strokeWidth={2} dot />
              <Line yAxisId="right" type="monotone" dataKey="balance" name="Balance" stroke="#1a3a5c" strokeWidth={2} dot />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {showDebtModal && <DebtModal onClose={() => setShowDebtModal(false)} onSave={handleAddDebt} />}
    </div>
  )
}
