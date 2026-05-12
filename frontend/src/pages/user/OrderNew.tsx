import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  Upload,
  ArrowRight,
  Copy,
  ExternalLink,
  Truck,
  Shield,
  RefreshCw,
  MessageSquare,
  FileText,
} from 'lucide-react'

type Step = 1 | 2 | 3

interface StepIndicatorProps {
  current: Step
}

function StepIndicator({ current }: StepIndicatorProps) {
  const steps = [
    { n: 1, label: 'Order details' },
    { n: 2, label: 'Fund escrow' },
    { n: 3, label: 'Awaiting delivery' },
  ]
  return (
    <div className="flex items-center gap-1">
      {steps.map(({ n, label }, i) => (
        <div key={n} className="flex items-center gap-1">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
            current === n
              ? 'bg-gray-900 text-white'
              : current > n
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-400'
          }`}>
            {current > n ? (
              <CheckCircle2 size={12} />
            ) : (
              <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px]">{n}</span>
            )}
            {label}
          </div>
          {i < steps.length - 1 && (
            <div className={`w-6 h-px ${current > i + 1 ? 'bg-green-400' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

/* ===================== STEP 1: ORDER DETAILS ===================== */
function Step1({ onNext }: { onNext: () => void }) {
  const [form, setForm] = useState({
    product: '',
    nafdac: '',
    manufacturer: '',
    quantity: '100',
    unitPrice: '12000',
  })

  const total = (Number(form.quantity) * Number(form.unitPrice)).toLocaleString()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onNext()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Supplier card */}
      <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4">
        <div className="w-10 h-10 bg-gray-900 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
          82
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-gray-900">MedTrust Nigeria Ltd</span>
            <span className="inline-flex items-center gap-1 bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
              <CheckCircle2 size={9} /> Verified 2 minutes ago
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">RC: 1234567 · GTBank · 01234567889</p>
        </div>
        <button type="button" className="text-xs text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1">
          Change supplier <ArrowRight size={11} />
        </button>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1.5">What are you ordering?</label>
        <input
          type="text"
          value={form.product}
          onChange={(e) => setForm({ ...form, product: e.target.value })}
          placeholder="e.g. Surgical Gloves Grade A (Bulk)"
          className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Expected NAFDAC registration</label>
          <input
            type="text"
            value={form.nafdac}
            onChange={(e) => setForm({ ...form, nafdac: e.target.value })}
            placeholder="04-1234"
            className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Expected manufacturer</label>
          <input
            type="text"
            value={form.manufacturer}
            onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
            placeholder="Vivo-Care Globas"
            className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Quantity</label>
          <input
            type="number"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Unit price</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">₦</span>
            <input
              type="number"
              value={form.unitPrice}
              onChange={(e) => setForm({ ...form, unitPrice: e.target.value })}
              className="w-full pl-6 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Total</label>
          <div className="px-3 py-2.5 text-sm bg-blue-50 border border-blue-200 rounded-lg text-blue-700 font-semibold">
            ₦{total}
          </div>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1.5">
          Supporting Documents (Purchase Order/Pro-forma)
        </label>
        <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-200 rounded-xl p-5 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-colors">
          <Upload size={18} className="text-gray-400 mb-2" />
          <p className="text-xs text-gray-500">
            Drop PDF or image here, or{' '}
            <span className="text-blue-600 font-medium">browse files</span>
          </p>
          <p className="text-[10px] text-gray-400 mt-1">Max file size: 10MB</p>
          <input type="file" className="hidden" />
        </label>
      </div>

      <button
        type="submit"
        className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 transition-colors"
      >
        Create escrow account <ArrowRight size={15} />
      </button>
      <p className="text-center text-xs text-gray-400">
        Clicking this will create a dedicated Squad virtual account for this order.
      </p>

      {/* Step hints */}
      <div className="grid grid-cols-2 gap-4 pt-2">
        {[
          { title: 'Step 2: Fund Escrow', desc: 'Securely transfer ₦1,200,000 to the dedicated virtual account.' },
          { title: 'Step 3: Awaiting Delivery', desc: "Monitor when it's delivered and verify to release funds to supplier." },
        ].map(({ title, desc }) => (
          <div key={title} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-xs font-semibold text-gray-500 mb-1">{title}</p>
            <p className="text-[11px] text-gray-400 leading-snug">{desc}</p>
          </div>
        ))}
      </div>
    </form>
  )
}

/* ===================== STEP 2: FUND ESCROW ===================== */
function Step2({ onNext }: { onNext: () => void }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-5">
      {/* Supplier chip */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gray-900 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
            MT
          </div>
          <div>
            <p className="font-semibold text-sm text-gray-900">MedTrust Nigeria Ltd</p>
            <span className="inline-flex items-center gap-1 text-green-600 text-[10px] font-semibold">
              <CheckCircle2 size={9} /> Verified Supplier
            </span>
          </div>
        </div>
        <button className="text-xs text-blue-600 font-medium hover:text-blue-700">View full report</button>
      </div>

      {/* Account card */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <p className="text-xs font-medium text-gray-500">Pay to this account</p>
          <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">
            SQUAD VIRTUAL ACCOUNT
          </span>
        </div>

        <div className="text-center space-y-3">
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">Guaranty Trust Bank</p>
            <p className="text-3xl font-bold font-mono text-gray-900 tracking-widest">7834927713</p>
            <p className="text-xs text-gray-500 mt-2 font-mono">TRUSTLOCK-MEDTRUST-ORD8842</p>
          </div>

          <div>
            <p className="text-xs text-gray-400 mb-1">Total amount due</p>
            <p className="text-2xl font-bold text-gray-900">₦1,200,000</p>
          </div>

          <div className="flex items-center justify-center gap-2 text-amber-600">
            <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
            <p className="text-xs font-medium">Awaiting payment detection...</p>
          </div>
          <p className="text-[10px] text-gray-400 leading-relaxed">
            Squad webhooks detect payment automatically. Once confirmed, funds are locked in escrow until delivery is verified.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 mt-5">
          <button
            onClick={handleCopy}
            className="flex items-center justify-center gap-2 border border-gray-200 text-gray-700 py-2.5 rounded-lg text-xs font-semibold hover:bg-gray-50 transition-colors"
          >
            <Copy size={13} /> {copied ? 'Copied!' : 'Copy Details'}
          </button>
          <button className="flex items-center justify-center gap-2 border border-gray-200 text-gray-700 py-2.5 rounded-lg text-xs font-semibold hover:bg-gray-50 transition-colors">
            <ExternalLink size={13} /> Payment Link
          </button>
        </div>
      </div>

      {/* Info footer */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: Shield, title: 'Funds held by Squad', desc: "Your payment is held in a secure Squad-managed track and never touches TrustLock's treasury." },
          { icon: CheckCircle2, title: 'Released on verification', desc: 'Funds are only moved to the supplier once you provide the delivery verification code.' },
          { icon: RefreshCw, title: 'Full refund if blocked', desc: "If the order is cancelled or delivery fails, funds are returned to your source bank within 24h." },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-gray-50 rounded-xl p-3 border border-gray-100">
            <Icon size={14} className="text-gray-500 mb-2" />
            <p className="text-xs font-semibold text-gray-700 mb-1">{title}</p>
            <p className="text-[10px] text-gray-400 leading-snug">{desc}</p>
          </div>
        ))}
      </div>

      {/* Demo shortcut */}
      <button
        onClick={onNext}
        className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
      >
        <CheckCircle2 size={14} /> Simulate payment received (demo)
      </button>

      <p className="text-center text-xs text-gray-400">
        <button className="text-red-500 hover:underline">Cancel order and release virtual account</button>
      </p>
    </div>
  )
}

/* ===================== STEP 3: AWAITING DELIVERY ===================== */
function Step3() {
  const navigate = useNavigate()
  const [photos, setPhotos] = useState<Record<string, string>>({})

  const photoSlots = [
    { key: 'supplier', label: 'SUPPLIER DOC' },
    { key: 'photo', label: 'MAX PHOTOGRAPH' },
    { key: 'ai', label: 'AI CONFIRM' },
  ]

  function handlePhotoUpload(key: string, e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      setPhotos((prev) => ({ ...prev, [key]: URL.createObjectURL(file) }))
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      {/* Left: main */}
      <div className="lg:col-span-2 space-y-4">
        {/* Success banner */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
          <CheckCircle2 size={16} className="text-green-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-green-800">Payment received and held in escrow</p>
            <p className="text-xs text-green-600 mt-0.5">
              ₦1,200,000 was remitted at 5:48pm via Squad webhook · The escrow ref: SQ-MER1P-28
            </p>
          </div>
          <span className="text-[10px] font-bold bg-green-100 text-green-700 px-2 py-0.5 rounded-full flex-shrink-0">
            POST IN ESCROW
          </span>
        </div>

        {/* Waiting state */}
        <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
          <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-gray-200">
            <Truck size={24} className="text-gray-400" />
          </div>
          <p className="text-base font-semibold text-gray-800 mb-1">Waiting for supplier to confirm shipment</p>
          <p className="text-sm text-gray-400 mb-6">
            Once MedTrust Nigeria makes the order as shipped you'll get a notification with a link to upload delivery photos for AI verification.
          </p>

          {/* Photo upload grid */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            {photoSlots.map(({ key, label }) => (
              <label key={key} className="aspect-square border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-blue-300 hover:bg-blue-50/20 transition-colors relative overflow-hidden">
                {photos[key] ? (
                  <img src={photos[key]} alt={label} className="absolute inset-0 w-full h-full object-cover rounded-xl" />
                ) : (
                  <>
                    <Upload size={18} className="text-gray-300 mb-2" />
                    <span className="text-[9px] text-gray-400 font-bold tracking-wide">{label}</span>
                  </>
                )}
                <input type="file" accept="image/*" className="hidden" onChange={(e) => handlePhotoUpload(key, e)} />
              </label>
            ))}
          </div>

          <div className="flex items-center gap-3 justify-center">
            <button
              onClick={() => navigate('/orders/ORD-882/verify')}
              className="flex items-center gap-2 bg-gray-900 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
            >
              <CheckCircle2 size={14} /> I've received the delivery
            </button>
            <button className="flex items-center gap-2 border border-gray-200 text-gray-700 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
              <MessageSquare size={14} /> Message supplier
            </button>
          </div>
        </div>

        {/* Order summary */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Order Summary</h3>
          <div className="space-y-2">
            {[
              { label: 'Product', val: 'Coartem 20¹/120' },
              { label: 'NAFDAC', val: '04-XXXX' },
              { label: 'Manufacturer', val: 'Novartis' },
              { label: 'Quantity', val: '100 boxes' },
            ].map(({ label, val }) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-gray-500">{label}</span>
                <span className="text-gray-800 font-medium">{val}</span>
              </div>
            ))}
            <div className="border-t border-gray-100 pt-2 mt-2 flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-800">Total Amount</span>
              <span className="text-sm font-bold text-gray-900">₦1,300,000</span>
            </div>
          </div>
          <button className="mt-3 w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-600 py-2 rounded-lg text-xs font-medium hover:bg-gray-50">
            <FileText size={12} /> View full document
          </button>
        </div>
      </div>

      {/* Right: escrow info */}
      <div className="space-y-4">
        {/* Supplier */}
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center text-white text-xs font-bold">MT</div>
            <div>
              <p className="text-sm font-semibold text-gray-900">MedTrust Nigeria Ltd</p>
              <span className="text-[10px] text-green-600 font-semibold flex items-center gap-1">
                <CheckCircle2 size={9} /> 92 Trust Score
              </span>
            </div>
          </div>
          {[
            { label: 'Register no.', val: 'RC 4764987' },
            { label: 'GTBank', val: '127604' },
            { label: 'Account', val: '81234567B9' },
          ].map(({ label, val }) => (
            <div key={label} className="flex justify-between text-xs py-1 border-b border-gray-50 last:border-0">
              <span className="text-gray-400">{label}</span>
              <span className="text-gray-700 font-medium">{val}</span>
            </div>
          ))}
        </div>

        {/* Escrow account */}
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Escrow Account</h3>
          {[
            { label: 'ACCOUNT NUMBER', val: '7834927713' },
            { label: 'ACCOUNT NAME', val: 'TRUSTLOCK-MEDTRUST-SET-ORD8842' },
          ].map(({ label, val }) => (
            <div key={label} className="mb-2.5">
              <p className="text-[9px] text-gray-400 uppercase tracking-widest">{label}</p>
              <p className="text-xs font-mono font-semibold text-gray-800">{val}</p>
            </div>
          ))}
          <div className="flex gap-2 mt-3">
            <button className="flex-1 text-[10px] text-gray-600 border border-gray-200 py-1.5 rounded-lg hover:bg-gray-50">Request refund</button>
            <button className="flex-1 text-[10px] text-gray-600 border border-gray-200 py-1.5 rounded-lg hover:bg-gray-50">View dispute</button>
          </div>
        </div>

        {/* Trust badge */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
          <Shield size={18} className="text-green-600 mx-auto mb-2" />
          <p className="text-xs text-green-700 font-medium leading-snug">
            This transaction is insured by the TrustLock Escrow Guarantee up to ₦5,000,000
          </p>
        </div>
      </div>
    </div>
  )
}

/* ===================== MAIN COMPONENT ===================== */
export default function OrderNew() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>(1)

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-2">
        <span
          onClick={() => navigate('/verify-supplier')}
          className="hover:text-gray-600 cursor-pointer"
        >
          Verify supplier
        </span>
        <span>›</span>
        <span className="text-gray-600 font-medium">MedTrust Nigeria Ltd</span>
        <span>›</span>
        <span className="text-gray-600 font-medium">
          {step === 1 ? 'New order' : `Order GRO-8842`}
        </span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {step === 1 ? 'Create order' : step === 2 ? 'Fund escrow' : 'Awaiting delivery'}
          </h1>
          {step === 1 && (
            <p className="text-xs text-gray-400 mt-0.5">
              Step 1 of 3 — Funds will be held in a dedicated Squad virtual account until delivery is verified.
            </p>
          )}
        </div>
        <StepIndicator current={step} />
      </div>

      {step === 1 && <Step1 onNext={() => setStep(2)} />}
      {step === 2 && <Step2 onNext={() => setStep(3)} />}
      {step === 3 && <Step3 />}
    </div>
  )
}
