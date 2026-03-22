import { useState, useEffect } from 'react'
import { api } from '../api'
import { fmt } from '../utils/formatters'

function PivotTable({ title, data, months }) {
  const names = Object.keys(data)
  if (names.length === 0) return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h3 className="font-semibold text-gray-800 mb-3">{title}</h3>
      <p className="text-gray-400 text-sm">No data yet</p>
    </div>
  )

  const rowTotals = names.map(n => months.reduce((s, m) => s + (data[n][m] || 0), 0))
  const colTotals = months.map(m => names.reduce((s, n) => s + (data[n][m] || 0), 0))
  const grandTotal = rowTotals.reduce((a, b) => a + b, 0)

  return (
    <div className="bg-white rounded-lg shadow mb-6 overflow-x-auto">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-gray-800">{title}</h3>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-gray-600 font-medium">Name</th>
            {months.map(m => <th key={m} className="px-4 py-2 text-right text-gray-600 font-medium">{m}</th>)}
            <th className="px-4 py-2 text-right text-gray-700 font-semibold">Total</th>
          </tr>
        </thead>
        <tbody>
          {names.map((name, i) => (
            <tr key={name} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-2 font-medium text-gray-700">{name}</td>
              {months.map(m => (
                <td key={m} className="px-4 py-2 text-right text-gray-600">
                  {data[name][m] ? fmt(data[name][m]) : <span className="text-gray-300">—</span>}
                </td>
              ))}
              <td className="px-4 py-2 text-right font-semibold text-gray-800">{fmt(rowTotals[i])}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 border-t-2 border-gray-200">
          <tr>
            <td className="px-4 py-2 font-semibold text-gray-700">Monthly Total</td>
            {colTotals.map((t, i) => (
              <td key={i} className="px-4 py-2 text-right font-semibold text-gray-700">{fmt(t)}</td>
            ))}
            <td className="px-4 py-2 text-right font-bold text-gray-900">{fmt(grandTotal)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

export default function TotalsTab({ month }) {
  const [totals, setTotals] = useState(null)
  const [varData, setVarData] = useState({ months: [], data: {} })
  const [monthlyData, setMonthlyData] = useState({ months: [], data: {} })

  useEffect(() => {
    api.getDashboardTotals(month).then(setTotals)
    api.getVariableByCategory().then(setVarData)
    api.getMonthlyByExpense().then(setMonthlyData)
  }, [month])

  return (
    <div>
      {/* Grand Total */}
      <div className="bg-white rounded-lg shadow mb-6 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-800">Grand Total — {month}</h3>
        </div>
        <table className="w-full text-sm">
          <tbody>
            {[
              ['Total Monthly Expenses', totals?.total_monthly],
              ['Total Variable Expenses', totals?.total_variable],
            ].map(([label, val]) => (
              <tr key={label} className="border-t border-gray-100">
                <td className="px-4 py-3 text-gray-600">{label}</td>
                <td className="px-4 py-3 text-right font-semibold text-gray-800">{fmt(val)}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-gray-200 bg-gray-50">
              <td className="px-4 py-3 font-bold text-gray-800">Grand Total Spending</td>
              <td className="px-4 py-3 text-right font-bold text-red-600 text-base">{fmt(totals?.grand_total)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <PivotTable title="Variable Expenses by Category" data={varData.data} months={varData.months} />
      <PivotTable title="Monthly Expenses by Name" data={monthlyData.data} months={monthlyData.months} />
    </div>
  )
}
