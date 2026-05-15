import { useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Shield, FileText } from 'lucide-react'
import { useOrder } from '../../api/orders'

const STATUS_LABEL: Record<string, string> = {
  pending_payment: 'PENDING',
  funded: 'FUNDED',
  delivered_pending: 'DELIVERED',
  released: 'RELEASED',
  disputed: 'DISPUTED',
  refunded: 'REFUNDED',
  cancelled: 'CANCELLED',
}

const STATUS_STYLE: Record<string, string> = {
  pending_payment: 'bg-gray-100 text-gray-600',
  funded: 'bg-blue-100 text-blue-700',
  delivered_pending: 'bg-amber-100 text-amber-700',
  released: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-700',
  refunded: 'bg-purple-100 text-purple-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: order, isLoading, error } = useOrder(id)

  if (isLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto flex items-center justify-center py-20">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-3" />
        <span className="text-sm text-gray-500">Loading order...</span>
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-center">
          <p className="text-sm font-semibold text-red-800">Order not found</p>
          <p className="text-xs text-red-600 mt-1">{error?.message ?? 'This order does not exist.'}</p>
          <button
            onClick={() => navigate('/orders')}
            className="mt-3 text-xs text-blue-600 font-medium hover:underline"
          >
            Back to orders
          </button>
        </div>
      </div>
    )
  }

  const statusLabel = STATUS_LABEL[order.status] ?? order.status.toUpperCase()
  const statusClass = STATUS_STYLE[order.status] ?? 'bg-gray-100 text-gray-600'
  const createdDate = new Date(order.created_at).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-4">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-700 font-medium">{order.id}</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Order {order.id}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={`px-2.5 py-0.5 rounded-full font-bold text-xs ${statusClass}`}>
              {statusLabel}
            </span>
            <span className="text-xs text-gray-400">{createdDate}</span>
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
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-sm text-gray-700 mb-4">Order Details</h2>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3">
            {[
              { label: 'Supplier', val: order.supplier_name },
              { label: 'Description', val: order.description },
              { label: 'Status', val: statusLabel },
              { label: 'Total Amount', val: `₦${order.amount_ngn.toLocaleString()}` },
              order.virtual_account_number
                ? { label: 'Virtual Account', val: order.virtual_account_number }
                : null,
              order.expected_delivery_by
                ? { label: 'Expected by', val: new Date(order.expected_delivery_by).toLocaleDateString('en-GB') }
                : null,
            ]
              .filter((x): x is { label: string; val: string } => x !== null)
              .map(({ label, val }) => (
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

        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Supplier</h3>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 bg-gray-900 rounded-full flex items-center justify-center text-white text-xs font-bold">
                {order.supplier_name.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{order.supplier_name}</p>
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

          {order.trust_score_at_creation != null && (
            <div className="bg-white border border-gray-200 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-400 mb-1">Trust Score at Creation</p>
              <p className="text-2xl font-bold text-gray-900">{order.trust_score_at_creation}</p>
              {order.trust_verdict_at_creation && (
                <p className="text-xs text-gray-500 mt-0.5 capitalize">{order.trust_verdict_at_creation}</p>
              )}
            </div>
          )}

          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
            <Shield size={16} className="text-green-600 mx-auto mb-2" />
            <p className="text-xs text-green-700 font-medium leading-snug">
              Protected by Eri Escrow Guarantee up to ₦5,000,000
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
