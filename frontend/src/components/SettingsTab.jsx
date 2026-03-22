import { useState } from 'react'
import { api } from '../api'
import { fmt } from '../utils/formatters'

export default function SettingsTab({ categories, monthlyExpenses, onRefreshCategories, onRefreshMonthlyExpenses }) {
  const [newCat, setNewCat] = useState({ name: '', color: '#3b82f6' })
  const [newMe, setNewMe] = useState({ name: '', expected_amount: '', category: 'Bills & Utilities' })

  const handleAddCategory = async (e) => {
    e.preventDefault()
    if (!newCat.name.trim()) return
    await api.createCategory(newCat)
    setNewCat({ name: '', color: '#3b82f6' })
    onRefreshCategories()
  }

  const handleDeleteCategory = async (id) => {
    const res = await api.deleteCategory(id)
    if (res.error) alert(res.error)
    else onRefreshCategories()
  }

  const handleAddMonthlyExpense = async (e) => {
    e.preventDefault()
    if (!newMe.name.trim()) return
    await api.createMonthlyExpense({ ...newMe, expected_amount: parseFloat(newMe.expected_amount) || 0 })
    setNewMe({ name: '', expected_amount: '', category: 'Bills & Utilities' })
    onRefreshMonthlyExpenses()
  }

  const handleDeleteMonthlyExpense = async (id) => {
    await api.deleteMonthlyExpense(id)
    onRefreshMonthlyExpenses()
  }

  const handleToggleMonthlyExpense = async (me) => {
    await api.updateMonthlyExpense(me.id, { is_active: me.is_active ? 0 : 1 })
    onRefreshMonthlyExpenses()
  }

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Categories */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-800">Categories</h3>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{['Color','Name','Type',''].map(h => <th key={h} className="px-4 py-2 text-left text-gray-600 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {categories.map(c => (
              <tr key={c.id} className="border-t border-gray-100">
                <td className="px-4 py-2">
                  <div className="w-6 h-6 rounded-full border" style={{ backgroundColor: c.color }} />
                </td>
                <td className="px-4 py-2 font-medium">{c.name}</td>
                <td className="px-4 py-2 text-gray-400 text-xs">{c.is_default ? 'Default' : 'Custom'}</td>
                <td className="px-4 py-2">
                  {!c.is_default && (
                    <button onClick={() => handleDeleteCategory(c.id)} className="text-red-500 hover:text-red-700 text-xs">Delete</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <form onSubmit={handleAddCategory} className="px-4 py-3 border-t border-gray-200 flex gap-2 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input value={newCat.name} onChange={e => setNewCat({...newCat, name: e.target.value})}
              placeholder="Category name" className="border border-gray-300 rounded px-2 py-1.5 text-sm w-40" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Color</label>
            <input type="color" value={newCat.color} onChange={e => setNewCat({...newCat, color: e.target.value})}
              className="h-8 w-12 rounded border border-gray-300 cursor-pointer" />
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700">Add</button>
        </form>
      </div>

      {/* Monthly Expenses */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-800">Monthly Expenses</h3>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{['Name','Expected','Category','Active',''].map(h => <th key={h} className="px-4 py-2 text-left text-gray-600 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {monthlyExpenses.map(me => (
              <tr key={me.id} className="border-t border-gray-100">
                <td className="px-4 py-2 font-medium">{me.name}</td>
                <td className="px-4 py-2 text-gray-700">{fmt(me.expected_amount)}</td>
                <td className="px-4 py-2 text-gray-500">{me.category}</td>
                <td className="px-4 py-2">
                  <button onClick={() => handleToggleMonthlyExpense(me)}
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${me.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {me.is_active ? 'Active' : 'Inactive'}
                  </button>
                </td>
                <td className="px-4 py-2">
                  <button onClick={() => handleDeleteMonthlyExpense(me.id)} className="text-red-500 hover:text-red-700 text-xs">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <form onSubmit={handleAddMonthlyExpense} className="px-4 py-3 border-t border-gray-200 flex gap-2 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input value={newMe.name} onChange={e => setNewMe({...newMe, name: e.target.value})}
              placeholder="e.g. Netflix" className="border border-gray-300 rounded px-2 py-1.5 text-sm w-36" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Amount</label>
            <input type="number" step="0.01" value={newMe.expected_amount} onChange={e => setNewMe({...newMe, expected_amount: e.target.value})}
              placeholder="0.00" className="border border-gray-300 rounded px-2 py-1.5 text-sm w-24" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Category</label>
            <select value={newMe.category} onChange={e => setNewMe({...newMe, category: e.target.value})}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm">
              {['Bills & Utilities','Subscriptions','Transportation','Shopping','Other'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700">Add</button>
        </form>
      </div>
    </div>
  )
}
