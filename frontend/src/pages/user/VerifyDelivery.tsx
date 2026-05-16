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
  Upload,
} from 'lucide-react'
import { useVerifyDelivery } from '../../api/verify'
import type { VerifyDeliveryResponse } from '../../api/types'
import { getStoredOrder } from '../../lib/storage'

/* ===================== UPLOAD VIEW ===================== */
function UploadView({ orderId, onResult }: { orderId: string; onResult: (r: VerifyDeliveryResponse) => void }) {
  const { mutate, isPending, error } = useVerifyDelivery()
  const navigate = useNavigate()
  const [quoteFile, setQuoteFile] = useState<File | null>(null)
  const [deliveryFile, setDeliveryFile] = useState<File | null>(null)

  const storedOrder = getStoredOrder(orderId)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!quoteFile || !deliveryFile) return
    mutate(
      {
        orderId,
        quoteImage: quoteFile,
        deliveryImage: deliveryFile,
        expectedNafdac: storedOrder?.expected_nafdac,
        expectedManufacturer: storedOrder?.expected_manufacturer,
        expectedProduct: storedOrder?.expected_product,
      },
      { onSuccess: onResult },
    )
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-5">
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-600">{orderId}</span>
        <span>›</span>
        <span className="font-semibold text-gray-700">Delivery Verification</span>
      </div>

      <div>
        <h1 className="text-xl font-bold text-gray-900">Verify delivery</h1>
        <p className="text-sm text-gray-500 mt-0.5">Upload a photo of the quoted product and the delivered product. The AI will compare them.</p>
      </div>

      {/* Order context pill */}
      {storedOrder && (storedOrder.expected_product || storedOrder.expected_nafdac) && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
          <CheckCircle2 size={14} className="text-blue-500 flex-shrink-0" />
          <div className="text-xs text-blue-700">
            <span className="font-semibold">Checking against order: </span>
            {[storedOrder.expected_product, storedOrder.expected_nafdac, storedOrder.expected_manufacturer]
              .filter(Boolean).join(' · ')}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Quoted product photo</p>
            <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors ${quoteFile ? 'border-green-300 bg-green-50/30' : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'}`}>
              {quoteFile ? (
                <>
                  <CheckCircle2 size={20} className="text-green-500 mb-2" />
                  <span className="text-xs text-green-700 font-medium text-center truncate max-w-full px-2">{quoteFile.name}</span>
                </>
              ) : (
                <>
                  <Upload size={20} className="text-gray-300 mb-2" />
                  <span className="text-xs text-gray-500 font-medium">Original / invoice photo</span>
                  <span className="text-[10px] text-gray-400 mt-1">Browse or drop here</span>
                </>
              )}
              <input type="file" accept="image/*" className="hidden" onChange={(e) => setQuoteFile(e.target.files?.[0] ?? null)} required />
            </label>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Delivered product photo</p>
            <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors ${deliveryFile ? 'border-green-300 bg-green-50/30' : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'}`}>
              {deliveryFile ? (
                <>
                  <CheckCircle2 size={20} className="text-green-500 mb-2" />
                  <span className="text-xs text-green-700 font-medium text-center truncate max-w-full px-2">{deliveryFile.name}</span>
                </>
              ) : (
                <>
                  <Upload size={20} className="text-gray-300 mb-2" />
                  <span className="text-xs text-gray-500 font-medium">What arrived today</span>
                  <span className="text-[10px] text-gray-400 mt-1">Browse or drop here</span>
                </>
              )}
              <input type="file" accept="image/*" className="hidden" onChange={(e) => setDeliveryFile(e.target.files?.[0] ?? null)} required />
            </label>
          </div>
        </div>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            Verification failed: {error.message}
          </p>
        )}

        <button
          type="submit"
          disabled={isPending || !quoteFile || !deliveryFile}
          className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 disabled:opacity-60 transition-colors"
        >
          {isPending ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Analysing with AI...
            </>
          ) : (
            <>Run AI verification <ArrowRight size={15} /></>
          )}
        </button>
      </form>
    </div>
  )
}

/* ===================== RESULT VIEW ===================== */
function ResultView({ result, orderId }: { result: VerifyDeliveryResponse; orderId: string }) {
  const navigate = useNavigate()
  const isGreen = result.verdict === 'green'
  const isAmber = result.verdict === 'amber'

  const verdictColors = isGreen
    ? { bg: 'bg-green-100', icon: 'text-green-600', banner: 'bg-green-50 border-green-200', text: 'text-green-800', sub: 'text-green-600', badge: 'bg-green-100 text-green-700' }
    : isAmber
    ? { bg: 'bg-amber-100', icon: 'text-amber-600', banner: 'bg-amber-50 border-amber-200', text: 'text-amber-800', sub: 'text-amber-600', badge: 'bg-amber-100 text-amber-700' }
    : { bg: 'bg-red-100', icon: 'text-red-600', banner: 'bg-red-50 border-red-200', text: 'text-red-800', sub: 'text-red-600', badge: 'bg-red-100 text-red-700' }

  const confidencePct = Math.round(result.match_confidence * (result.match_confidence <= 1 ? 100 : 1))

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-600">{orderId}</span>
        <span>›</span>
        <span className="font-semibold text-gray-700">Delivery Verification</span>
      </div>

      {/* Title row */}
      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-full flex items-center justify-center ${verdictColors.bg}`}>
          {isGreen
            ? <CheckCircle2 size={18} className={verdictColors.icon} />
            : isAmber
            ? <AlertTriangle size={18} className={verdictColors.icon} />
            : <XCircle size={18} className={verdictColors.icon} />
          }
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {isGreen ? 'Delivery verified' : isAmber ? 'Delivery uncertain' : 'Delivery blocked'}
          </h1>
          <p className="text-sm text-gray-500">
            {isGreen
              ? 'Product matches the order. You can release funds to the supplier.'
              : isAmber
              ? 'Partial match detected. Review concerns before releasing funds.'
              : 'Issues detected. Funds remain in escrow until resolved.'}
          </p>
        </div>
        <span className={`ml-auto text-[10px] font-bold px-2.5 py-1 rounded-full ${verdictColors.badge}`}>
          {confidencePct}% MATCH
        </span>
      </div>

      {/* Status banner */}
      <div className={`border rounded-xl p-4 flex items-start gap-4 ${verdictColors.banner}`}>
        {isGreen
          ? <CheckCircle2 size={18} className={`${verdictColors.icon} flex-shrink-0`} />
          : <XCircle size={18} className={`${verdictColors.icon} flex-shrink-0`} />
        }
        <div className="flex-1">
          <p className={`text-sm font-semibold ${verdictColors.text}`}>
            {isGreen ? 'Goods match the order' : 'Product mismatch detected'}
          </p>
          {result.concerns.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {result.concerns.map((c, i) => (
                <li key={i} className={`text-xs ${verdictColors.sub} flex items-start gap-1`}>
                  <AlertTriangle size={10} className="mt-0.5 flex-shrink-0" /> {c}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* What was detected */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Detected product details</h3>
        <div className="space-y-2">
          {[
            { label: 'Brand / product name', val: result.delivered_brand },
            { label: 'Dosage', val: result.delivered_dosage },
            { label: 'NAFDAC number', val: result.delivered_nafdac },
          ].map(({ label, val }) => (
            <div key={label} className="flex items-center justify-between text-xs border-b border-gray-50 py-2 last:border-0">
              <span className="text-gray-500">{label}</span>
              <span className={`font-semibold ${val ? 'text-gray-800' : 'text-gray-300'}`}>
                {val ?? 'Not detected'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Differences */}
      {result.differences.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Differences found</h3>
          <div className="space-y-2">
            {result.differences.map((d, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border border-amber-100">
                <AlertTriangle size={13} className="text-amber-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-amber-800">{d}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Release / dispute */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        {isGreen ? (
          <>
            <h3 className="text-sm font-semibold text-gray-800 mb-1">Release escrowed funds</h3>
            <p className="text-xs text-gray-400 mb-3">
              AI confirmed the delivery matches your order. A confirmation step is shown before funds move.
            </p>
            <button
              onClick={() => navigate(`/orders/${orderId}`)}
              className="w-full flex items-center justify-center gap-2 bg-green-600 text-white py-3 rounded-xl text-sm font-semibold hover:bg-green-700 transition-colors"
            >
              <CheckCircle2 size={15} /> Go to order → Release funds
            </button>
          </>
        ) : (
          <>
            <div className="flex items-start gap-3 mb-4">
              <Shield size={16} className="text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-gray-900">Funds are protected</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Your escrow balance is safe. The AI flagged issues — release is blocked until you decide.
                </p>
              </div>
            </div>

            <button
              disabled
              className="w-full py-2.5 bg-gray-100 text-gray-400 rounded-lg text-sm font-semibold cursor-not-allowed flex items-center justify-center gap-2 mb-3"
            >
              <XCircle size={14} /> Release blocked — verification failed
            </button>

            <div className="grid grid-cols-2 gap-3 mb-3">
              <button
                onClick={() => navigate(`/orders/${orderId}`)}
                className="py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Open dispute
              </button>
              <button
                onClick={() => navigate(`/orders/${orderId}`)}
                className="py-2.5 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
              >
                <ArrowRight size={14} /> Request refund
              </button>
            </div>

            <div className="border-t border-gray-100 pt-3">
              <p className="text-[11px] text-gray-400 mb-1.5">
                If you inspected the goods and trust the supplier, you can override the AI decision.
              </p>
              <button
                onClick={() => navigate(`/orders/${orderId}`)}
                className="w-full py-2 border border-amber-300 text-amber-700 bg-amber-50 rounded-lg text-xs font-semibold hover:bg-amber-100 transition-colors flex items-center justify-center gap-1.5"
              >
                <AlertTriangle size={12} /> Override and release anyway
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

/* ===================== DEMO BLOCKED VIEW ===================== */
function BlockedView() {
  const navigate = useNavigate()

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-600">ORD-7891</span>
        <span>›</span>
        <span className="font-semibold text-gray-700 uppercase tracking-wide">DELIVERY VERIFICATION</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="bg-red-100 text-red-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">BLOCKED</span>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Delivery blocked</h1>
          <p className="text-sm text-gray-500">Multiple issues detected. Funds remain in escrow.</p>
        </div>
      </div>
      <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-start gap-4">
        <div className="w-9 h-9 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
          <XCircle size={18} className="text-red-600" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-red-800 text-sm">Possible counterfeit detected</p>
          <p className="text-xs text-red-600 mt-1">
            NAFDAC number does not match the expected product. Funds are <strong>SAFE</strong> in escrow.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Failure Indicators</h3>
          <div className="space-y-3">
            {[
              { title: 'NAFDAC Mismatch', desc: 'The registry code belongs to a different drug category (Proguanil vs Coartem).' },
              { title: 'Low Visual Similarity', desc: 'Package typography does not match manufacturer master plates.' },
              { title: 'Hue Shift Detected', desc: 'Packaging color values are outside brand tolerances.' },
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
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">NAFDAC Greenbook</h3>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl font-mono font-bold text-gray-900">04-6433</span>
            <span className="bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">MISMATCH</span>
          </div>
          <div className="bg-red-50 rounded-xl p-4 border border-red-100 text-xs">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-gray-400 mb-1 text-[10px] uppercase">What was ordered</p>
                <p className="font-semibold text-gray-800">Coartem 20/120 mg</p>
                <p className="text-gray-500">Novartis</p>
              </div>
              <div>
                <p className="text-red-500 mb-1 text-[10px] uppercase">This number is registered to</p>
                <p className="font-semibold text-red-800">Proguanil 100mg tablets</p>
                <p className="text-red-600">A different company</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <Shield size={16} className="text-green-500 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-gray-900">Funds protected</p>
            <p className="text-xs text-gray-500 mt-0.5">Your escrow balance is safe. The Release Funds button is disabled.</p>
          </div>
        </div>
        <button disabled className="w-full py-2.5 bg-gray-100 text-gray-400 rounded-lg text-sm font-semibold cursor-not-allowed flex items-center justify-center gap-2 mb-3">
          <XCircle size={14} /> Release blocked — verification failed
        </button>
        <div className="grid grid-cols-2 gap-3">
          <button className="py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">Open dispute</button>
          <button className="py-2.5 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 flex items-center justify-center gap-2">
            <ArrowRight size={14} /> Refund my escrow
          </button>
        </div>
      </div>
    </div>
  )
}

/* ===================== DEMO CONFIRMED VIEW ===================== */
function ConfirmedView() {
  const navigate = useNavigate()
  const [releasing, setReleasing] = useState(false)
  const [released, setReleased] = useState(false)

  function handleRelease() {
    setReleasing(true)
    setTimeout(() => { setReleasing(false); setReleased(true) }, 2000)
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-600">OPO-8842</span>
        <span>›</span>
        <span className="font-semibold text-gray-700">Delivery verification</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-green-100 rounded-full flex items-center justify-center">
          <CheckCircle2 size={18} className="text-green-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Delivery verified</h1>
          <p className="text-sm text-gray-500">All checks passed. You can release funds to the supplier.</p>
        </div>
      </div>
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-4">
        <CheckCircle2 size={18} className="text-green-600 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-green-800">Goods match the order</p>
          <div className="flex items-center gap-4 mt-1">
            {['Visual similarity 96%', 'NAFDAC verified', 'No tampering detected'].map((item) => (
              <span key={item} className="text-xs text-green-600 flex items-center gap-1">
                <CheckCircle2 size={10} /> {item}
              </span>
            ))}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">NAFDAC Greenbook</h3>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl font-mono font-bold text-gray-900">04-9412</span>
            <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded-full">ACTIVE</span>
          </div>
          <div className="space-y-1.5">
            {[
              { label: 'Product', val: 'Coartem 20/120 mg' },
              { label: 'Manufacturer', val: 'Novartis Pharmaceuticals' },
              { label: 'Status', val: 'ACTIVE', green: true },
            ].map(({ label, val, green }) => (
              <div key={label} className="flex items-center justify-between text-xs py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-gray-500">{label}</span>
                <span className={`font-semibold ${green ? 'text-green-600' : 'text-gray-800'}`}>{val}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Transaction anomaly check</h3>
          <div className="space-y-3">
            {[
              { icon: TrendingUp, color: 'text-green-600', val: '102%', label: 'PRICE VS MARKET', badge: 'Stable', badgeColor: 'bg-green-100 text-green-700' },
              { icon: Clock, color: 'text-blue-600', val: '5+ Years', label: 'SUPPLIER AGE', badge: 'Trusted', badgeColor: 'bg-blue-100 text-blue-700' },
              { icon: CreditCard, color: 'text-gray-600', val: 'Unchanged', label: 'BANK DETAILS', badge: 'Verified', badgeColor: 'bg-gray-100 text-gray-700' },
            ].map(({ icon: Icon, color, val, label, badge, badgeColor }) => (
              <div key={label} className="flex items-center gap-3 p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                <Icon size={14} className={`${color} flex-shrink-0`} />
                <div className="flex-1">
                  <p className="text-xs font-bold text-gray-900">{val}</p>
                  <p className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</p>
                </div>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${badgeColor}`}>{badge}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-800 mb-3">Release escrowed funds</h3>
        <p className="text-xs text-gray-500 mb-4">₦1,200,000 will be transferred to MedTrust Nigeria Ltd via Squad Transfer API.</p>
        {released ? (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
            <CheckCircle2 size={24} className="text-green-600 mx-auto mb-2" />
            <p className="text-sm font-semibold text-green-800">₦1,200,000 released successfully!</p>
          </div>
        ) : (
          <button
            onClick={handleRelease}
            disabled={releasing}
            className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 disabled:opacity-70 transition-colors"
          >
            {releasing ? (
              <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Processing...</>
            ) : (
              <><CheckCircle2 size={15} /> Release ₦1,200,000 to supplier</>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

/* ===================== MAIN ===================== */
export default function VerifyDelivery() {
  const { id } = useParams<{ id: string }>()
  const orderId = id ?? 'unknown'
  const [result, setResult] = useState<VerifyDeliveryResponse | null>(null)

  const isDemoBlocked = orderId === 'ORD-7891'
  const isDemoConfirmed = orderId === 'ORD-882'
  const [demoView, setDemoView] = useState<'blocked' | 'confirmed'>(isDemoBlocked ? 'blocked' : 'confirmed')
  const isDemo = isDemoBlocked || isDemoConfirmed

  if (isDemo) {
    return (
      <div>
        <div className="flex items-center gap-2 px-6 pt-4">
          <span className="text-xs text-gray-400 font-medium">Demo view:</span>
          <div className="flex rounded-lg border border-gray-200 overflow-hidden">
            <button
              onClick={() => setDemoView('blocked')}
              className={`px-3 py-1.5 text-xs font-semibold transition-colors ${demoView === 'blocked' ? 'bg-red-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              Product Blocked
            </button>
            <button
              onClick={() => setDemoView('confirmed')}
              className={`px-3 py-1.5 text-xs font-semibold transition-colors ${demoView === 'confirmed' ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              Product Confirmed
            </button>
          </div>
        </div>
        {demoView === 'blocked' ? <BlockedView /> : <ConfirmedView />}
      </div>
    )
  }

  if (result) {
    return <ResultView result={result} orderId={orderId} />
  }

  return <UploadView orderId={orderId} onResult={setResult} />
}
