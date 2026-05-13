import { useNavigate } from 'react-router-dom'
import { Plus, Search, Filter, ArrowRight } from 'lucide-react'

const orders = [
  {
    id: 'ORD-882',
    supplier: 'MedTrust Nigeria',
    product: 'Coartem 20/120mg · 100 boxes',
    amount: '₦1,200,000',
    status: 'RELEASED',
    date: '14 May 2026',
    nafdac: '04-9412',
  },
  {
    id: 'ORD-883',
    supplier: 'MedTrust Nigeria',
    product: 'Amoxicillin 500mg · 200 packs',
    amount: '₦1,200,000',
    status: 'ON HOLD',
    date: '13 May 2026',
    nafdac: '04-8821',
  },
  {
    id: 'ORD-2023',
    supplier: 'PharmaPlus',
    product: 'Paracetamol 500mg · 500 units',
    amount: '₦1,100,000',
    status: 'FUNDED',
    date: '12 May 2026',
    nafdac: '04-5521',
  },
  {
    id: 'ORD-2034',
    supplier: 'Lagos Pharma',
    product: 'Surgical Gloves Grade A · 1000 boxes',
    amount: '₦14,300,000',
    status: 'FUNDED',
    date: '11 May 2026',
    nafdac: 'N/A',
  },
  {
    id: 'ORD-0038',
    supplier: 'SpecMeds',
    product: 'Insulin 100IU/mL · 50 vials',
    amount: '₦68,000',
    status: 'BLOCKED',
    date: '10 May 2026',
    nafdac: '04-6433',
  },
  {
    id: 'ORD-1203',
    supplier: 'MedTrust Nigeria',
    product: 'Metformin 1000mg · 2000 tablets',
    amount: '₦35,400,000',
    status: 'RELEASED',
    date: '08 May 2026',
    nafdac: '04-2210',
  },
]

const statusStyle: Record<string, string> = {
  RELEASED: 'bg-green-100 text-green-700',
  'ON HOLD': 'bg-amber-100 text-amber-700',
  FUNDED: 'bg-blue-100 text-blue-700',
  BLOCKED: 'bg-red-100 text-red-700',
}

export default function OrderList() {
  const navigate = useNavigate()

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Orders</h1>
          <p className="text-sm text-gray-500 mt-0.5">{orders.length} total · 3 active escrows</p>
        </div>
        <button
          onClick={() => navigate('/orders/new')}
          className="flex items-center gap-2 bg-gray-900 text-white px-4 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
        >
          <Plus size={15} /> New order
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search orders, suppliers, NAFDAC..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          />
        </div>
        <button className="flex items-center gap-2 border border-gray-200 bg-white text-gray-600 px-3 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors">
          <Filter size={14} /> Filter
        </button>
        {(['ALL', 'FUNDED', 'ON HOLD', 'RELEASED', 'BLOCKED'] as const).map((s) => (
          <button
            key={s}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
              s === 'ALL'
                ? 'bg-gray-900 text-white'
                : `border border-gray-200 text-gray-600 hover:bg-gray-50 ${statusStyle[s] ?? ''}`
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Order ID</th>
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Supplier</th>
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Product</th>
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">NAFDAC</th>
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Amount</th>
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Status</th>
              <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Date</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {orders.map((o) => (
              <tr
                key={o.id}
                onClick={() => navigate(`/orders/${o.id}/verify`)}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <td className="px-5 py-3.5 font-mono font-semibold text-gray-700 text-xs">{o.id}</td>
                <td className="px-5 py-3.5 text-gray-800 font-medium text-xs">{o.supplier}</td>
                <td className="px-5 py-3.5 text-gray-500 text-xs">{o.product}</td>
                <td className="px-5 py-3.5 font-mono text-gray-500 text-xs">{o.nafdac}</td>
                <td className="px-5 py-3.5 text-gray-800 font-semibold text-xs">{o.amount}</td>
                <td className="px-5 py-3.5">
                  <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${statusStyle[o.status]}`}>
                    {o.status}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-gray-400 text-xs">{o.date}</td>
                <td className="px-5 py-3.5">
                  <ArrowRight size={14} className="text-gray-300" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-center text-xs text-gray-400 mt-4">
        Showing {orders.length} orders · Sorted by date (newest first)
      </p>
    </div>
  )
}
