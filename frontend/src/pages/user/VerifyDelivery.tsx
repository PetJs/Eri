import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Shield,
  ArrowRight,
  TrendingUp,
  Clock,
  CreditCard,
} from 'lucide-react'

type ViewMode = 'blocked' | 'confirmed'

/* ===================== PRODUCT BLOCKED VIEW ===================== */
function BlockedView() {
  const navigate = useNavigate()

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">orders</span>
        <span>›</span>
        <span className="text-gray-600">ORD-7891</span>
        <span>›</span>
        <span className="font-semibold text-gray-700 uppercase tracking-wide">DELIVERY VERIFICATION</span>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="bg-red-100 text-red-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
          BLOCKED
        </span>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Delivery blocked</h1>
          <p className="text-sm text-gray-500">Multiple issues detected. Funds remain in escrow.</p>
        </div>
      </div>

      {/* Main alert */}
      <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-start gap-4">
        <div className="w-9 h-9 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
          <XCircle size={18} className="text-red-600" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-red-800 text-sm">Possible counterfeit detected</p>
          <p className="text-xs text-red-600 mt-1">
            NAFDAC number does not match the expected product. Funds are{' '}
            <strong>SAFE</strong> in escrow.
          </p>
        </div>
        <span className="text-[10px] font-bold text-gray-400 bg-gray-100 px-2 py-1 rounded-full flex-shrink-0">
          VERIFIED 29 OCTOBER AGO
        </span>
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Product visual comparison */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Product Visual Comparison</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            {[
              { label: 'QUOTED PRODUCT', bg: 'bg-blue-50', text: 'text-blue-600' },
              { label: 'DELIVERED PRODUCT', bg: 'bg-red-50', text: 'text-red-600' },
            ].map(({ label, bg, text }) => (
              <div key={label}>
                <p className={`text-[10px] font-bold ${text} uppercase tracking-wide mb-2`}>{label}</p>
                <div className={`${bg} rounded-xl h-28 flex items-center justify-center border border-current/10`}>
                  <div className="text-center">
                    <div className="w-12 h-14 mx-auto bg-white/80 rounded-lg border border-current/20 flex items-center justify-center mb-1">
                      <span className="text-[10px] font-bold text-gray-500">COARTEM</span>
                    </div>
                    <p className="text-[9px] text-gray-400">20/120mg</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Similarity bar */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-600 font-medium">Visual similarity</span>
              <span className="text-sm font-bold text-amber-600">71%</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-amber-400 rounded-full" style={{ width: '71%' }} />
            </div>
            <p className="text-[10px] text-gray-400 mt-1.5">
              Note: Similarity below 80% threshold — likely different product.
            </p>
          </div>
        </div>

        {/* Failure indicators */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Failure Indicators</h3>
          <div className="space-y-3">
            {[
              {
                title: 'NAFDAC Mismatch',
                desc: "The registry code belongs to a different drug category (Proquanil vs Coartem).",
              },
              {
                title: 'Low Visual Similarity',
                desc: 'Package typography does not match manufacturer master plates (0% vs 96%).',
              },
              {
                title: 'Hue Shift Detected',
                desc: 'Packaging color values are 12% outside of brand tolerances for Novartis Blue.',
              },
            ].map(({ title, desc }) => (
              <div key={title} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-100">
                <XCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-red-800">{title}</p>
                  <p className="text-[11px] text-red-600 mt-0.5 leading-snug">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* NAFDAC Greenbook */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">NAFDAC Greenbook Verification</h3>
          <Shield size={16} className="text-red-400" />
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-widest mb-1">Detected on packaging</p>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-mono font-bold text-gray-900">04-6433</span>
              <span className="bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">NOT REGISTERED</span>
            </div>
          </div>
          <div className="flex items-center justify-end">
            <XCircle size={32} className="text-red-300" />
          </div>
        </div>

        <div className="bg-red-50 rounded-xl p-4 border border-red-100">
          <p className="text-[10px] text-red-500 uppercase tracking-widest font-bold mb-3">
            NAFDAC registration number 04-6433 is registered in the Greenbook — but for a DIFFERENT product.
          </p>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-gray-400 mb-1 text-[10px] uppercase tracking-wide">What was ordered</p>
              <p className="font-semibold text-gray-800">Coartem 20/120 mg</p>
              <p className="text-gray-500">Manufacturer: Novartis</p>
            </div>
            <div>
              <p className="text-red-500 mb-1 text-[10px] uppercase tracking-wide">What this number is registered to</p>
              <p className="font-semibold text-red-800">Proguanil 100mg tablets</p>
              <p className="text-red-600">A different company</p>
            </div>
          </div>
        </div>

        <div className="mt-3 flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
          <AlertTriangle size={13} className="text-amber-500 mt-0.5 flex-shrink-0" />
          <p className="text-[11px] text-amber-700">
            This pattern matches NAFDAC Public Alert #023/2026 — known counterfeit Coartem with forged NAFDAC number 04-6433.
          </p>
        </div>
      </div>

      {/* Funds protected */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <Shield size={16} className="text-green-500 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-gray-900">Funds protected</p>
            <p className="text-xs text-gray-500 mt-0.5">
              ₦1,200,000 remains in your Squad escrow account. The Release Funds button is disabled.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <button disabled className="w-full py-2.5 bg-gray-100 text-gray-400 rounded-lg text-sm font-semibold cursor-not-allowed flex items-center justify-center gap-2">
            <XCircle size={14} /> Release blocked — verification failed
          </button>
          <div className="grid grid-cols-2 gap-3">
            <button className="py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
              Open dispute with supplier
            </button>
            <button className="py-2.5 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 transition-colors flex items-center justify-center gap-2">
              <ArrowRight size={14} /> Refund my escrow
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ===================== PRODUCT CONFIRMED VIEW ===================== */
function ConfirmedView() {
  const navigate = useNavigate()
  const [releasing, setReleasing] = useState(false)
  const [released, setReleased] = useState(false)

  function handleRelease() {
    setReleasing(true)
    setTimeout(() => {
      setReleasing(false)
      setReleased(true)
    }, 2000)
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-600">OPO-8842</span>
        <span>›</span>
        <span className="font-semibold text-gray-700">Delivery verification</span>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-green-100 rounded-full flex items-center justify-center">
          <CheckCircle2 size={18} className="text-green-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Delivery verified</h1>
          <p className="text-sm text-gray-500">All checks passed. You can release funds to the supplier.</p>
        </div>
      </div>

      {/* Success banner */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-4">
        <CheckCircle2 size={18} className="text-green-600 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-green-800">Goods match the order</p>
          <div className="flex items-center gap-4 mt-1">
            {[
              'Visual similarity 96%',
              'NAFDAC verified',
              'No tampering detected',
            ].map((item) => (
              <span key={item} className="text-xs text-green-600 flex items-center gap-1">
                <CheckCircle2 size={10} /> {item}
              </span>
            ))}
          </div>
        </div>
        <span className="text-[10px] text-green-500 font-medium flex-shrink-0">Verified 12 seconds ago</span>
      </div>

      {/* Two-column content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Product comparison */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Product comparison</h3>
            <CheckCircle2 size={14} className="text-green-500" />
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            {[
              { label: 'QUOTED PRODUCT', accent: 'text-gray-500' },
              { label: 'DELIVERED PRODUCT', accent: 'text-blue-600' },
            ].map(({ label, accent }) => (
              <div key={label}>
                <p className={`text-[10px] font-bold ${accent} uppercase tracking-wide mb-2`}>{label}</p>
                <div className="bg-blue-50 rounded-xl h-32 flex items-center justify-center border border-blue-100">
                  <div className="text-center">
                    <div className="w-14 h-16 mx-auto bg-white rounded-lg border border-blue-200 flex items-center justify-center mb-1 shadow-sm">
                      <span className="text-[10px] font-bold text-blue-700">COARTEM</span>
                    </div>
                    <p className="text-[9px] text-blue-400">20/120mg</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Similarity bar */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-600 font-medium">Visual similarity</span>
              <span className="text-sm font-bold text-green-600">96%</span>
            </div>
            <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: '96%' }} />
            </div>
            <p className="text-[10px] text-green-600 mt-1.5 flex items-center gap-1">
              <CheckCircle2 size={10} /> CLIP ViT-B-32 cosine similarity · RELIABLE, CONFIDENT, HIGH
            </p>
          </div>
        </div>

        {/* NAFDAC Greenbook */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">NAFDAC Greenbook</h3>
            <CheckCircle2 size={14} className="text-green-500" />
          </div>

          <div className="mb-4">
            <p className="text-[10px] text-gray-400 uppercase tracking-widest mb-1">Detected on packaging</p>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-mono font-bold text-gray-900">04-9412</span>
              <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded-full">ACTIVE</span>
            </div>
          </div>

          <div className="space-y-2">
            {[
              { label: 'Product', val: 'Coartem 20/120 mg' },
              { label: 'Manufacturer', val: 'Novartis Pharmaceuticals' },
              { label: 'Type', val: 'Artemether/Lumefantrine' },
              { label: 'Status', val: 'ACTIVE', green: true },
              { label: 'Expires', val: '6/2027' },
            ].map(({ label, val, green }) => (
              <div key={label} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0 text-xs">
                <span className="text-gray-500">{label}</span>
                <span className={`font-semibold ${green ? 'text-green-600' : 'text-gray-800'}`}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Transaction anomaly check */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Transaction anomaly check</h3>
          <div className="w-4 h-4 rounded-full border border-gray-300 flex items-center justify-center cursor-help">
            <span className="text-[8px] text-gray-400 font-bold">?</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            {
              icon: TrendingUp,
              color: 'text-green-600',
              val: '102%',
              sub: '(Stable)',
              label: 'PRICE VS MARKET',
              badge: 'Stable',
              badgeColor: 'bg-green-100 text-green-700',
            },
            {
              icon: Clock,
              color: 'text-blue-600',
              val: '5+ Years',
              sub: '(Trusted)',
              label: 'SUPPLIER AGE',
              badge: 'Trusted',
              badgeColor: 'bg-blue-100 text-blue-700',
            },
            {
              icon: CreditCard,
              color: 'text-gray-600',
              val: 'Unchanged',
              sub: '(Verified)',
              label: 'BANK DETAILS',
              badge: 'Verified',
              badgeColor: 'bg-gray-100 text-gray-700',
            },
          ].map(({ icon: Icon, color, val, sub, label, badge, badgeColor }) => (
            <div key={label} className="flex items-start gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
              <Icon size={16} className={`${color} mt-0.5 flex-shrink-0`} />
              <div>
                <p className="text-sm font-bold text-gray-900">
                  {val} <span className="text-xs font-normal text-gray-400">{sub}</span>
                </p>
                <p className="text-[10px] text-gray-400 uppercase tracking-wide mt-0.5">{label}</p>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${badgeColor}`}>{badge}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Release funds */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-800 mb-3">Release escrowed funds</h3>
        <p className="text-xs text-gray-500 mb-4">
          ₦1,200,000 will be transferred to MedTrust Nigeria Ltd via Squad Transfer API.
        </p>

        <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl border border-gray-100 mb-4">
          <div className="w-9 h-9 bg-gray-900 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            MT
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">MedTrust Nigeria Ltd</p>
            <p className="text-xs text-gray-500">GTBank · 01234567B9</p>
          </div>
          <button className="ml-auto text-xs text-blue-600 hover:text-blue-700 font-medium">
            View all statistics
          </button>
        </div>

        {released ? (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
            <CheckCircle2 size={24} className="text-green-600 mx-auto mb-2" />
            <p className="text-sm font-semibold text-green-800">₦1,200,000 released successfully!</p>
            <p className="text-xs text-green-600 mt-1">Funds transferred to MedTrust Nigeria Ltd via Squad Transfer API</p>
          </div>
        ) : (
          <button
            onClick={handleRelease}
            disabled={releasing}
            className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 disabled:opacity-70 transition-colors"
          >
            {releasing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Processing transfer...
              </>
            ) : (
              <>
                <CheckCircle2 size={15} /> Release ₦1,200,000 to supplier
              </>
            )}
          </button>
        )}
        <p className="text-center text-[10px] text-gray-400 mt-2">
          Powered by <span className="font-semibold">Squad Transfer API</span>
        </p>
      </div>
    </div>
  )
}

/* ===================== MAIN ===================== */
export default function VerifyDelivery() {
  const { id } = useParams()
  const [view, setView] = useState<ViewMode>(id === 'ORD-7891' ? 'blocked' : 'confirmed')

  return (
    <div>
      {/* Demo toggle */}
      <div className="flex items-center gap-2 px-6 pt-4">
        <span className="text-xs text-gray-400 font-medium">Demo view:</span>
        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
          <button
            onClick={() => setView('blocked')}
            className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
              view === 'blocked' ? 'bg-red-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            Product Blocked
          </button>
          <button
            onClick={() => setView('confirmed')}
            className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
              view === 'confirmed' ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            Product Confirmed
          </button>
        </div>
      </div>

      {view === 'blocked' ? <BlockedView /> : <ConfirmedView />}
    </div>
  )
}
