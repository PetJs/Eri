import { useRef, useState } from 'react'
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

/* ===================== UPLOAD VIEW ===================== */
function UploadView({ orderId }: { orderId: string }) {
  const navigate = useNavigate()
  const { mutate, isPending, error } = useVerifyDelivery()
  const quoteRef = useRef<HTMLInputElement>(null)
  const deliveryRef = useRef<HTMLInputElement>(null)
  const [quoteFile, setQuoteFile] = useState<File | null>(null)
  const [deliveryFile, setDeliveryFile] = useState<File | null>(null)
  const [nafdac, setNafdac] = useState('')
  const [manufacturer, setManufacturer] = useState('')
  const [product, setProduct] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!quoteFile || !deliveryFile) return
    mutate(
      {
        orderId,
        quoteImage: quoteFile,
        deliveryImage: deliveryFile,
        expectedNafdac: nafdac || undefined,
        expectedManufacturer: manufacturer || undefined,
        expectedProduct: product || undefined,
      },
      {
        onSuccess: (result) => {
          navigate(`/orders/${orderId}/verify`, { state: { result } })
          window.location.reload()
        },
      },
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
        <p className="text-sm text-gray-500 mt-0.5">Upload both product images for AI-powered comparison.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          {/* Quote image */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Quoted product photo</p>
            <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-5 cursor-pointer transition-colors ${quoteFile ? 'border-green-300 bg-green-50/30' : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'}`}>
              {quoteFile ? (
                <>
                  <CheckCircle2 size={18} className="text-green-500 mb-1" />
                  <span className="text-xs text-green-700 font-medium text-center truncate max-w-full px-2">{quoteFile.name}</span>
                </>
              ) : (
                <>
                  <Upload size={18} className="text-gray-400 mb-2" />
                  <span className="text-xs text-gray-500">Browse or drop image</span>
                </>
              )}
              <input
                ref={quoteRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setQuoteFile(e.target.files?.[0] ?? null)}
                required
              />
            </label>
          </div>

          {/* Delivery image */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Delivered product photo</p>
            <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-5 cursor-pointer transition-colors ${deliveryFile ? 'border-green-300 bg-green-50/30' : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'}`}>
              {deliveryFile ? (
                <>
                  <CheckCircle2 size={18} className="text-green-500 mb-1" />
                  <span className="text-xs text-green-700 font-medium text-center truncate max-w-full px-2">{deliveryFile.name}</span>
                </>
              ) : (
                <>
                  <Upload size={18} className="text-gray-400 mb-2" />
                  <span className="text-xs text-gray-500">Browse or drop image</span>
                </>
              )}
              <input
                ref={deliveryRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setDeliveryFile(e.target.files?.[0] ?? null)}
                required
              />
            </label>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Expected NAFDAC #</label>
            <input
              type="text"
              value={nafdac}
              onChange={(e) => setNafdac(e.target.value)}
              placeholder="04-9412"
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Manufacturer</label>
            <input
              type="text"
              value={manufacturer}
              onChange={(e) => setManufacturer(e.target.value)}
              placeholder="Novartis"
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Product name</label>
            <input
              type="text"
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              placeholder="Coartem"
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            />
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

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">Orders</span>
        <span>›</span>
        <span className="text-gray-600">{orderId}</span>
        <span>›</span>
        <span className="font-semibold text-gray-700">Delivery Verification</span>
      </div>

      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-full flex items-center justify-center ${isGreen ? 'bg-green-100' : 'bg-red-100'}`}>
          {isGreen
            ? <CheckCircle2 size={18} className="text-green-600" />
            : <XCircle size={18} className="text-red-600" />
          }
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {isGreen ? 'Delivery verified' : 'Delivery blocked'}
          </h1>
          <p className="text-sm text-gray-500">
            {isGreen
              ? 'All checks passed. You can release funds to the supplier.'
              : 'Issues detected. Funds remain in escrow.'}
          </p>
        </div>
        <span className={`ml-auto text-[10px] font-bold px-2.5 py-1 rounded-full ${isGreen ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          SCORE {result.score}
        </span>
      </div>

      {/* Status banner */}
      <div className={`border rounded-xl p-4 flex items-start gap-4 ${isGreen ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
        {isGreen
          ? <CheckCircle2 size={18} className="text-green-600 flex-shrink-0" />
          : <XCircle size={18} className="text-red-600 flex-shrink-0" />
        }
        <div className="flex-1">
          <p className={`text-sm font-semibold ${isGreen ? 'text-green-800' : 'text-red-800'}`}>
            {isGreen ? 'Goods match the order' : 'Product mismatch detected'}
          </p>
          {result.concerns.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {result.concerns.map((c, i) => (
                <li key={i} className={`text-xs ${isGreen ? 'text-green-600' : 'text-red-600'} flex items-start gap-1`}>
                  <AlertTriangle size={10} className="mt-0.5 flex-shrink-0" /> {c}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Checks breakdown */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Verification Checks</h3>
        <div className="space-y-3">
          {result.checks.map((c) => (
            <div key={c.name} className="flex items-start gap-3">
              {c.status === 'pass' && <CheckCircle2 size={15} className="text-green-500 mt-0.5 flex-shrink-0" />}
              {c.status === 'fail' && <XCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />}
              {(c.status === 'warn' || c.status === 'unverified') && <AlertTriangle size={15} className="text-amber-500 mt-0.5 flex-shrink-0" />}
              <div>
                <p className="text-sm font-medium text-gray-800">{c.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">{c.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* NAFDAC lookup */}
      {result.detected_nafdac_number && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">NAFDAC Greenbook</h3>
            <Shield size={14} className={isGreen ? 'text-green-500' : 'text-red-400'} />
          </div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl font-mono font-bold text-gray-900">{result.detected_nafdac_number}</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${isGreen ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {isGreen ? 'ACTIVE' : 'MISMATCH'}
            </span>
          </div>
          {result.nafdac_lookup_result && (
            <div className="space-y-1.5">
              {Object.entries(result.nafdac_lookup_result)
                .filter(([k]) => ['product_name', 'manufacturer', 'status'].includes(k))
                .map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-xs border-b border-gray-50 pb-1.5">
                    <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-gray-800">{String(v)}</span>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Release / dispute */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        {isGreen ? (
          <>
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Release escrowed funds</h3>
            <button
              onClick={() => navigate(`/orders/${orderId}`)}
              className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 transition-colors"
            >
              <CheckCircle2 size={15} /> Go to order to release funds
            </button>
          </>
        ) : (
          <>
            <div className="flex items-start gap-3 mb-4">
              <Shield size={16} className="text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-gray-900">Funds protected</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Your escrow balance is safe. The Release Funds button is disabled.
                </p>
              </div>
            </div>
            <button disabled className="w-full py-2.5 bg-gray-100 text-gray-400 rounded-lg text-sm font-semibold cursor-not-allowed flex items-center justify-center gap-2 mb-3">
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

  return <UploadView orderId={orderId} />
}
