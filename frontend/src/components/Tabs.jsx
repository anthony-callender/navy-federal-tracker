export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="bg-white border-b border-gray-200 px-6">
      <div className="flex gap-0">
        {tabs.map((tab, i) => (
          <button
            key={tab}
            onClick={() => onChange(i)}
            className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
              active === i
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  )
}
