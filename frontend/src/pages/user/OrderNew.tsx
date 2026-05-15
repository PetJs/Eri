import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
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
import { useCreateOrder } from '../../api/orders'
import { useSimulatePayment } from '../../api/admin'
import type { OrderResponse } from '../../api/types'

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

interface SupplierInfo {
  name: string
  rc: string
  bank: string
  account: string
  score: number
  verdict: string
}

/* ===================== STEP 1: ORDER DETAILS ===================== */
function Step1({ onCreated, supplier }: { onCreated: (order: OrderResponse) => void; supplier: SupplierInfo }) {
  const navigate = useNavigate()
  const { mutate, isPending, error } = useCreateOrder()
  const [form, setForm] = useState({
    product: '',
    nafdac: '',
    manufacturer: '',
    quantity: '100',
    unitPrice: '12000',
  })

  const total = (Number(form.quantity) * Number(form.unitPrice)).toLocaleString()
  const scoreColor = supplier.score >= 71 ? 'bg-green-700' : supplier.score >= 50 ? 'bg-amber-600' : 'bg-red-600'

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const description = [
      form.product,
      form.quantity && `Qty: ${form.quantity}`,
      form.nafdac && `NAFDAC: ${form.nafdac}`,
    ].filter(Boolean).join(' · ')

    mutate(
      {
        supplier_id: 'sup_medtrust',
        amount_ngn: Number(form.quantity) * Number(form.unitPrice),
        description,
        buyer_email: 'demo@eri.app',
      },
      { onSuccess: onCreated },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Supplier card */}
      <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4">
        <div className={`w-10 h-10 ${scoreColor} rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}>
          {supplier.score}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-gray-900">{supplier.name}</span>
            <span className="inline-flex items-center gap-1 bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
              <CheckCircle2 size={9} /> Verified
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{supplier.rc} · {supplier.bank} · {supplier.account}</p>
        </div>
        <button type="button" onClick={() => navigate('/verify-supplier')} className="text-xs text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1">
          Change supplier <ArrowRight size={11} />
        </button>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1.5">What are you ordering?</label>
        <input
          type="text"
          value={form.product}
          onChange={(e) => setForm({ ...form, product: e.target.value })}
          placeholder="e.g. Coartem 20/120 mg tablets"
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
            placeholder="04-9412"
            className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Expected manufacturer</label>
          <input
            type="text"
            value={form.manufacturer}
            onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
            placeholder="Novartis"
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

      {error && (
        <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          Failed to create order: {error.message}
        </p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 disabled:opacity-60 transition-colors"
      >
        {isPending ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Creating escrow account...
          </>
        ) : (
          <>Create escrow account <ArrowRight size={15} /></>
        )}
      </button>
      <p className="text-center text-xs text-gray-400">
        Clicking this will create a dedicated Squad virtual account for this order.
      </p>

      <div className="grid grid-cols-2 gap-4 pt-2">
        {[
          { title: 'Step 2: Fund Escrow', desc: 'Securely transfer to the dedicated virtual account.' },
          { title: 'Step 3: Awaiting Delivery', desc: 'Monitor delivery and verify to release funds to supplier.' },
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
function Step2({ order, supplier, onNext }: { order: OrderResponse; supplier: SupplierInfo; onNext: () => void }) {
  const [copied, setCopied] = useState(false)
  const { mutate: simulate, isPending } = useSimulatePayment(order.id)

  function handleCopy() {
    if (order.virtual_account_number) {
      navigator.clipboard.writeText(order.virtual_account_number).catch(() => {})
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const accountNumber = order.virtual_account_number ?? '—'
  const accountName = order.virtual_account_name ?? `TRUSTLOCK-${order.id.toUpperCase()}`
  const bankName = order.virtual_account_bank ?? 'Guaranty Trust Bank'
  const amount = order.amount_ngn.toLocaleString()

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gray-900 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
            {supplier.name.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-sm text-gray-900">{supplier.name}</p>
            <span className="inline-flex items-center gap-1 text-green-600 text-[10px] font-semibold">
              <CheckCircle2 size={9} /> Verified Supplier
            </span>
          </div>
        </div>
        <button className="text-xs text-blue-600 font-medium hover:text-blue-700">View full report</button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <p className="text-xs font-medium text-gray-500">Pay to this account</p>
          <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">
            SQUAD VIRTUAL ACCOUNT
          </span>
        </div>

        <div className="text-center space-y-3">
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">{bankName}</p>
            <p className="text-3xl font-bold font-mono text-gray-900 tracking-widest">{accountNumber}</p>
            <p className="text-xs text-gray-500 mt-2 font-mono">{accountName}</p>
          </div>

          <div>
            <p className="text-xs text-gray-400 mb-1">Total amount due</p>
            <p className="text-2xl font-bold text-gray-900">₦{amount}</p>
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

      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: Shield, title: 'Funds held by Squad', desc: "Your payment is held in a secure Squad-managed account and never touches TrustLock's treasury." },
          { icon: CheckCircle2, title: 'Released on verification', desc: 'Funds are only moved to the supplier once you provide the delivery verification code.' },
          { icon: RefreshCw, title: 'Full refund if blocked', desc: "If delivery fails, funds are returned to your source bank within 24h." },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-gray-50 rounded-xl p-3 border border-gray-100">
            <Icon size={14} className="text-gray-500 mb-2" />
            <p className="text-xs font-semibold text-gray-700 mb-1">{title}</p>
            <p className="text-[10px] text-gray-400 leading-snug">{desc}</p>
          </div>
        ))}
      </div>

      <button
        onClick={() => simulate(undefined, { onSuccess: onNext })}
        disabled={isPending}
        className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-60 transition-colors flex items-center justify-center gap-2"
      >
        {isPending ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <><CheckCircle2 size={14} /> Simulate payment received (demo)</>
        )}
      </button>

      <p className="text-center text-xs text-gray-400">
        <button className="text-red-500 hover:underline">Cancel order and release virtual account</button>
      </p>
    </div>
  )
}

/* ===================== STEP 3: AWAITING DELIVERY ===================== */
function Step3({ order, supplier }: { order: OrderResponse; supplier: SupplierInfo }) {
  const navigate = useNavigate()
  const [photos, setPhotos] = useState<Record<string, string>>({})

  const photoSlots = [
    { key: 'supplier', label: 'SUPPLIER DOC' },
    { key: 'photo', label: 'PHOTOGRAPH' },
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
      <div className="lg:col-span-2 space-y-4">
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
          <CheckCircle2 size={16} className="text-green-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-green-800">Payment received and held in escrow</p>
            <p className="text-xs text-green-600 mt-0.5">
              ₦{order.amount_ngn.toLocaleString()} is locked in escrow · Order: {order.id}
            </p>
          </div>
          <span className="text-[10px] font-bold bg-green-100 text-green-700 px-2 py-0.5 rounded-full flex-shrink-0">
            IN ESCROW
          </span>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
          <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-gray-200">
            <Truck size={24} className="text-gray-400" />
          </div>
          <p className="text-base font-semibold text-gray-800 mb-1">Waiting for supplier to confirm shipment</p>
          <p className="text-sm text-gray-400 mb-6">
            Once the supplier marks the order as shipped you'll get a notification with a link to upload delivery photos for AI verification.
          </p>

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
              onClick={() => navigate(`/orders/${order.id}/verify`)}
              className="flex items-center gap-2 bg-gray-900 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
            >
              <CheckCircle2 size={14} /> I've received the delivery
            </button>
            <button className="flex items-center gap-2 border border-gray-200 text-gray-700 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
              <MessageSquare size={14} /> Message supplier
            </button>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Order Summary</h3>
          <div className="space-y-2">
            {[
              { label: 'Description', val: order.description },
              { label: 'Order ID', val: order.id },
              { label: 'Status', val: order.status },
            ].map(({ label, val }) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-gray-500">{label}</span>
                <span className="text-gray-800 font-medium">{val}</span>
              </div>
            ))}
            <div className="border-t border-gray-100 pt-2 mt-2 flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-800">Total Amount</span>
              <span className="text-sm font-bold text-gray-900">₦{order.amount_ngn.toLocaleString()}</span>
            </div>
          </div>
          <button className="mt-3 w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-600 py-2 rounded-lg text-xs font-medium hover:bg-gray-50">
            <FileText size={12} /> View full document
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center text-white text-xs font-bold">
              {supplier.name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">{supplier.name}</p>
              <span className="text-[10px] text-green-600 font-semibold flex items-center gap-1">
                <CheckCircle2 size={9} /> Score: {supplier.score}
              </span>
            </div>
          </div>
          <div className="text-xs text-gray-500">{supplier.rc} · {supplier.bank} · {supplier.account}</div>
        </div>

        {order.virtual_account_number && (
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Escrow Account</h3>
            <div className="mb-2.5">
              <p className="text-[9px] text-gray-400 uppercase tracking-widest">ACCOUNT NUMBER</p>
              <p className="text-xs font-mono font-semibold text-gray-800">{order.virtual_account_number}</p>
            </div>
            {order.virtual_account_name && (
              <div className="mb-2.5">
                <p className="text-[9px] text-gray-400 uppercase tracking-widest">ACCOUNT NAME</p>
                <p className="text-xs font-mono font-semibold text-gray-800">{order.virtual_account_name}</p>
              </div>
            )}
          </div>
        )}

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

const DEFAULT_SUPPLIER: SupplierInfo = {
  name: 'Unknown Supplier',
  rc: '—',
  bank: '—',
  account: '—',
  score: 0,
  verdict: 'green',
}

/* ===================== MAIN COMPONENT ===================== */
export default function OrderNew() {
  const navigate = useNavigate()
  const location = useLocation()
  const [step, setStep] = useState<Step>(1)
  const [order, setOrder] = useState<OrderResponse | null>(null)

  const supplier: SupplierInfo = (location.state as { supplier?: SupplierInfo })?.supplier ?? DEFAULT_SUPPLIER

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-2">
        <span
          onClick={() => navigate('/verify-supplier')}
          className="hover:text-gray-600 cursor-pointer"
        >
          Verify supplier
        </span>
        <span>›</span>
        <span className="text-gray-600 font-medium">{supplier.name}</span>
        <span>›</span>
        <span className="text-gray-600 font-medium">
          {step === 1 ? 'New order' : `Order ${order?.id ?? ''}`}
        </span>
      </div>

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

      {step === 1 && (
        <Step1
          supplier={supplier}
          onCreated={(o) => {
            setOrder(o)
            setStep(2)
          }}
        />
      )}
      {step === 2 && order && <Step2 order={order} supplier={supplier} onNext={() => setStep(3)} />}
      {step === 3 && order && <Step3 order={order} supplier={supplier} />}
    </div>
  )
}
