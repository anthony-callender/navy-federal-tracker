import { useState, useEffect } from 'react'
import { api } from './api'
import Tabs from './components/Tabs'
import TransactionsTab from './components/TransactionsTab'
import TotalsTab from './components/TotalsTab'
import FreeSpendingTab from './components/FreeSpendingTab'
import SettingsTab from './components/SettingsTab'
import LoginScreen from './components/LoginScreen'
import { currentMonth } from './utils/formatters'

const TABS = ['Transactions', 'Totals', 'Free Spending', 'Settings']

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('auth_token'))
  const [activeTab, setActiveTab] = useState(0)
  const [categories, setCategories] = useState([])
  const [monthlyExpenses, setMonthlyExpenses] = useState([])
  const [month, setMonth] = useState(currentMonth())

  const refreshCategories = () => api.getCategories().then(setCategories)
  const refreshMonthlyExpenses = () => api.getMonthlyExpenses().then(setMonthlyExpenses)

  useEffect(() => {
    if (!authed) return
    refreshCategories()
    refreshMonthlyExpenses()
  }, [authed])

  if (!authed) return <LoginScreen onLogin={() => setAuthed(true)} />

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-[#1a3a5c] text-white px-6 py-4 flex items-center justify-between shadow-lg">
        <div>
          <h1 className="text-xl font-bold">Navy Federal Budget Dashboard</h1>
          <p className="text-blue-200 text-sm">Tracking {month}</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="month"
            value={month}
            onChange={e => setMonth(e.target.value)}
            className="bg-[#1a3a5c] border border-blue-400 text-white rounded px-2 py-1 text-sm"
          />
          <button
            onClick={() => { localStorage.removeItem('auth_token'); setAuthed(false) }}
            className="text-blue-300 hover:text-white text-sm border border-blue-400 rounded px-2 py-1"
          >
            Sign Out
          </button>
        </div>
      </header>
      <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />
      <main className="p-6">
        {activeTab === 0 && <TransactionsTab month={month} categories={categories} monthlyExpenses={monthlyExpenses} />}
        {activeTab === 1 && <TotalsTab month={month} />}
        {activeTab === 2 && <FreeSpendingTab month={month} />}
        {activeTab === 3 && <SettingsTab month={month} categories={categories} monthlyExpenses={monthlyExpenses} onRefreshCategories={refreshCategories} onRefreshMonthlyExpenses={refreshMonthlyExpenses} />}
      </main>
    </div>
  )
}
