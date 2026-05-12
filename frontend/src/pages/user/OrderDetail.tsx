import { useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Shield, FileText } from 'lucide-react'

const statusStyle: Record<string, string> = {
  RELEASED: 'bg-green-100 text-green-700',
  'ON HOLD': 'bg-amber-100 text-amber-700',
  FUNDED: 'bg-blue-100 text-blue-700',
  BLOCKED: 'bg-red-100 text-red-700',
}

const orders: Record<string, {
  id: string; supplier: string; product: string; nafdac: string
  manufacturer: string; quantity: string; amount: string; status: string; date: string
}> = {
  'ORD-882': {
    id: 'ORD-882', supplier: 'MedTrust Nigeria', product: 'Coartem 20/120mg',
    nafdac: '04-9412', manufacturer: 'Novartis', quantity: '100 boxes',
    amount: '₦1,200,000', status: 'RELEASED', date: '14 May 2026',
  },
  'ORD-883': {
    id: 'ORD-883', supplier: 'MedTrust Nigeria', product: 'Amoxicillin 500mg',
    nafdac: '04-8821', manufacturer: 'Emzor', quantity: '200 packs',
    amount: '₦1,200,000', status: 'ON HOLD', date: '13 May 2026',
  },
}

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const order = orders[id ?? ''] ?? {
    id: id ?? 'N/A', supplier: 'MedTrust Nigeria', product: 'Coartem 20/120mg',
    nafdac: '04-9412', manufacturer: 'Novartis', quantity: '100 boxes',
    amount: '₦1,200,000', status: 'RELEASED', date: '14 May 2026',
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-4">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-700 font-medium">{order.id}</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Order {order.id}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={`px-2.5 py-0.5 rounded-full font-bold text-xs ${statusStyle[order.status]}`}>
              {order.status}
            </span>
            <span className="text-xs text-gray-400">{order.date}</span>
          </div>
        </div>
        <button
          onClick={() => navigate(`/orders/${id}/verify`)}
          className="flex items-center gap-2 bg-gray-900 text-white px-4 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
        >
          View Delivery Verification <ArrowRight size={14} />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Order details */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-sm text-gray-700 mb-4">Order Details</h2>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3">
            {[
              { label: 'Supplier', val: order.supplier },
              { label: 'Product', val: order.product },
              { label: 'NAFDAC Number', val: order.nafdac },
              { label: 'Manufacturer', val: order.manufacturer },
              { label: 'Quantity', val: order.quantity },
              { label: 'Total Amount', val: order.amount },
            ].map(({ label, val }) => (
              <div key={label}>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-0.5">{label}</p>
                <p className="text-sm font-medium text-gray-800">{val}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 flex items-center gap-3">
            <button className="flex items-center gap-2 border border-gray-200 text-gray-600 px-4 py-2 rounded-lg text-xs font-medium hover:bg-gray-50 transition-colors">
              <FileText size={13} /> View documents
            </button>
          </div>
        </div>

        {/* Side info */}
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Supplier</h3>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 bg-gray-900 rounded-full flex items-center justify-center text-white text-xs font-bold">MT</div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{order.supplier}</p>
                <span className="text-[10px] text-green-600 font-semibold flex items-center gap-1">
                  <CheckCircle2 size={9} /> Verified Supplier
                </span>
              </div>
            </div>
            <button
              onClick={() => navigate('/verify-supplier')}
              className="w-full text-xs text-blue-600 font-medium border border-blue-200 py-1.5 rounded-lg hover:bg-blue-50 transition-colors"
            >
              View trust report
            </button>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
            <Shield size={16} className="text-green-600 mx-auto mb-2" />
            <p className="text-xs text-green-700 font-medium leading-snug">
              Protected by TrustLock Escrow Guarantee up to ₦5,000,000
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
