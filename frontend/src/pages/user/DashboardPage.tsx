import { useNavigate } from 'react-router-dom'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ArrowRight,
  Star,
  BarChart2,
} from 'lucide-react'

const orders = [
  { id: 'ORD-882', supplier: 'MedTrust Nigeria', amount: '₦1.2M', status: 'RELEASED', refId: 'SQ-48891-28' },
  { id: 'ORD-883', supplier: 'MedTrust Nigeria', amount: '₦1.2M', status: 'ON HOLD', refId: 'SQ-48892-01' },
  { id: 'ORD-2023', supplier: 'PharmaPlus', amount: '₦1.1M', status: 'FUNDED', refId: 'SQ-48901-12' },
  { id: 'ORD-2034', supplier: 'Lagos Pharma', amount: '₦14.3M', status: 'FUNDED', refId: 'SQ-48910-44' },
  { id: 'ORD-0038', supplier: 'SpecMeds', amount: '₦68K', status: 'BLOCKED', refId: 'SQ-48923-09' },
  { id: 'ORD-1203', supplier: 'MedTrust Nigeria', amount: '₦35.4M', status: 'RELEASED', refId: 'SQ-48945-77' },
]

const suppliers = [
  { name: 'MedTrust Nigeria', tier: 'Tier 3 Partner', status: 'verified', score: 82 },
  { name: 'PharmaPlus', status: 'verified', score: 91 },
  { name: 'Lagos Pharma', status: 'renewal_pending', score: 74 },
  { name: 'QuickMeds', status: 'action_required', score: 43 },
]

const statusStyle: Record<string, string> = {
  RELEASED: 'bg-green-100 text-green-700',
  'ON HOLD': 'bg-amber-100 text-amber-700',
  FUNDED: 'bg-blue-100 text-blue-700',
  BLOCKED: 'bg-red-100 text-red-700',
}

const statusDot: Record<string, string> = {
  verified: 'bg-green-500',
  renewal_pending: 'bg-amber-500',
  action_required: 'bg-red-500',
}

const supplierStatusLabel: Record<string, string> = {
  verified: 'Active partner',
  renewal_pending: 'Renewal pending',
  action_required: 'Action required',
}

const chartBars = [
  { month: 'JAN', h: 30 },
  { month: 'FEB', h: 45 },
  { month: 'MAR', h: 35 },
  { month: 'APR', h: 55 },
  { month: 'MAY', h: 40 },
  { month: 'JUN', h: 70 },
  { month: 'JUL', h: 85, active: true },
]

export default function DashboardPage() {
  const navigate = useNavigate()

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Good afternoon, Adaeze</h1>
        <p className="text-sm text-gray-500 mt-0.5">Thursday, 14 May 2026 · 3 active orders</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'ACTIVE ESCROW',
            value: '3',
            sub: '₦4.2M held',
            icon: BarChart2,
            color: 'text-blue-600',
            bg: 'bg-blue-50',
          },
          {
            label: 'SUPPLIERS QUALIFIED',
            value: '12',
            sub: (
              <span className="flex items-center gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={10} className="fill-amber-400 text-amber-400" />
                ))}
                <span className="ml-1 text-[10px] text-gray-400">Average</span>
              </span>
            ),
            icon: CheckCircle2,
            color: 'text-green-600',
            bg: 'bg-green-50',
          },
          {
            label: 'FREE MONTH',
            value: '₦18.4M',
            sub: 'returned to suppliers',
            icon: TrendingUp,
            color: 'text-purple-600',
            bg: 'bg-purple-50',
          },
          {
            label: 'DISPUTES',
            value: '0',
            sub: 'all clear',
            icon: AlertTriangle,
            color: 'text-gray-400',
            bg: 'bg-gray-100',
          },
        ].map(({ label, value, sub, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase">{label}</p>
              <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon size={14} className={color} />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900 mb-1">{value}</p>
            <div className="text-xs text-gray-500">{sub}</div>
          </div>
        ))}
      </div>

      {/* Two column content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Orders */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-sm text-gray-900">Recent orders</h2>
            <button className="text-xs text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1">
              View archive <ArrowRight size={12} />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left px-5 py-3 text-gray-400 font-semibold uppercase tracking-wider">Order ID</th>
                  <th className="text-left px-5 py-3 text-gray-400 font-semibold uppercase tracking-wider">Supplier</th>
                  <th className="text-left px-5 py-3 text-gray-400 font-semibold uppercase tracking-wider">Amount</th>
                  <th className="text-left px-5 py-3 text-gray-400 font-semibold uppercase tracking-wider">Status</th>
                  <th className="text-left px-5 py-3 text-gray-400 font-semibold uppercase tracking-wider">Ref ID</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => navigate(`/orders/${o.id}`)}
                    className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3 font-mono font-medium text-gray-700">{o.id}</td>
                    <td className="px-5 py-3 text-gray-700">{o.supplier}</td>
                    <td className="px-5 py-3 text-gray-700 font-medium">{o.amount}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${statusStyle[o.status]}`}>
                        {o.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 font-mono text-gray-400">{o.refId}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Suppliers */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-sm text-gray-900">Top suppliers</h2>
          </div>
          <div className="p-3 space-y-1">
            {suppliers.map((s) => (
              <div
                key={s.name}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                  {s.name.split(' ').map((w) => w[0]).slice(0, 2).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{s.name}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${statusDot[s.status]}`}></span>
                    <p className="text-[10px] text-gray-400">{supplierStatusLabel[s.status]}</p>
                  </div>
                </div>
                <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />
              </div>
            ))}
          </div>
          <div className="px-5 pb-4">
            <button className="w-full py-2 border border-gray-200 rounded-lg text-xs font-semibold text-gray-600 hover:bg-gray-50 transition-colors">
              Expand supplier network
            </button>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Performance chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
          <div className="mb-4">
            <h2 className="font-semibold text-sm text-gray-900">Performance insights</h2>
            <p className="text-xs text-gray-400 mt-0.5">Monthly escrow volume & release efficiency</p>
          </div>
          <div className="flex items-end gap-2 h-28">
            {chartBars.map(({ month, h, active }) => (
              <div key={month} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t-md transition-all ${active ? 'bg-blue-600' : 'bg-gray-100'}`}
                  style={{ height: `${h}%` }}
                />
                <span className="text-[9px] text-gray-400 uppercase">{month}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Operational Excellence */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-sm text-gray-900 mb-4 uppercase tracking-wide">Operational Excellence</h2>
          <div className="space-y-4">
            {[
              { icon: TrendingUp, color: 'text-green-500', val: '₦18.4M', label: 'Released without friction this cycle' },
              { icon: TrendingDown, color: 'text-red-500', val: '₦40K', label: 'Blocked due to compliance mismatch' },
              { icon: CheckCircle2, color: 'text-blue-500', val: '6.2s', label: 'Average verification response time' },
              { icon: AlertTriangle, color: 'text-gray-400', val: '0%', label: 'False positive verification rate' },
            ].map(({ icon: Icon, color, val, label }) => (
              <div key={val + label} className="flex items-start gap-3">
                <Icon size={14} className={`${color} mt-0.5 flex-shrink-0`} />
                <div>
                  <p className="text-sm font-semibold text-gray-800">{val}</p>
                  <p className="text-[11px] text-gray-400 leading-tight">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick action */}
      <div className="pb-2">
        <button
          onClick={() => navigate('/orders/new')}
          className="fixed bottom-6 right-6 flex items-center gap-2 bg-blue-600 text-white px-5 py-3 rounded-full text-sm font-semibold shadow-lg hover:bg-blue-700 transition-colors"
        >
          + New Verification
        </button>
      </div>
    </div>
  )
}
