export const fmt = (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n ?? 0)
export const currentMonth = () => new Date().toISOString().slice(0, 7)
