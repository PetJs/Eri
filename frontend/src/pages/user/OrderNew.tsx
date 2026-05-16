import { useState, useRef, useCallback, useEffect } from 'react'
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
  AlertTriangle,
  Plus,
  X,
  Loader2,
} from 'lucide-react'
import { useExtractInvoice, useCreateOrderFromInvoice } from '../../api/orders'
import { useSimulatePayment } from '../../api/admin'
import type {
  ExtractInvoiceResponse,
  InvoiceBankAccount,
  InvoiceLineItem,
  InvoiceSupplier,
  OrderResponse,
} from '../../api/types'
import { saveOrder, updateStoredOrderStatus } from '../../lib/storage'

// ── Local types ──────────────────────────────────────────────────────────────

type PagePhase = 'upload' | 'review' | 'fund' | 'await'

interface EditableLineItem {
  _key: string
  product_name: string
  nafdac_registration: string
  manufacturer: string
  batch_number: string
  expiry_date: string
  quantity: number
  unit: string
  unit_price: number
}

interface EditableTotals {
  discount: number
  vat: number
}

// ── StepIndicator ────────────────────────────────────────────────────────────

function phaseToStep(phase: PagePhase): 1 | 2 | 3 {
  if (phase === 'fund') return 2
  if (phase === 'await') return 3
  return 1
}

function StepIndicator({ phase }: { phase: PagePhase }) {
  const current = phaseToStep(phase)
  const steps = [
    { n: 1, label: 'Order details' },
    { n: 2, label: 'Fund escrow' },
    { n: 3, label: 'Awaiting delivery' },
  ]
  return (
    <div className="flex items-center gap-1">
      {steps.map(({ n, label }, i) => (
        <div key={n} className="flex items-center gap-1">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
              current === n
                ? 'bg-gray-900 text-white'
                : current > n
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-400'
            }`}
          >
            {current > n ? (
              <CheckCircle2 size={12} />
            ) : (
              <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px]">
                {n}
              </span>
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

// ── InvoiceDropZone ──────────────────────────────────────────────────────────

function InvoiceDropZone({
  onFile,
  isLoading,
  error,
}: {
  onFile: (f: File) => void
  isLoading: boolean
  error?: string
}) {
  const [isDragging, setIsDragging] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File) => {
      setLocalError(null)
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setLocalError('Only PDF files are supported.')
        return
      }
      if (file.size > 10 * 1024 * 1024) {
        setLocalError('File is too large. Maximum size is 10MB.')
        return
      }
      onFile(file)
    },
    [onFile],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const displayError = localError ?? error

  return (
    <div className="max-w-lg mx-auto mt-10">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          if (!isLoading) setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !isLoading && inputRef.current?.click()}
        className={`flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-16 transition-colors ${
          isDragging
            ? 'border-blue-400 bg-blue-50 cursor-copy'
            : isLoading
            ? 'border-gray-200 bg-gray-50 cursor-default'
            : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50/20 cursor-pointer'
        }`}
      >
        {isLoading ? (
          <>
            <Loader2 size={32} className="text-blue-500 animate-spin mb-4" />
            <p className="text-sm font-medium text-gray-700">Reading invoice...</p>
            <p className="text-xs text-gray-400 mt-1">Extracting line items with AI</p>
          </>
        ) : (
          <>
            <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
              <Upload size={22} className="text-gray-500" />
            </div>
            <p className="text-sm font-semibold text-gray-800">Upload invoice or pro-forma to begin</p>
            <p className="text-xs text-gray-500 mt-1">
              Drop a PDF here or{' '}
              <span className="text-blue-600 font-medium">browse files</span>
            </p>
            <p className="text-[10px] text-gray-400 mt-3">PDF only · Max 10MB</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
            e.target.value = ''
          }}
        />
      </div>
      {displayError && (
        <div className="mt-3 flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertTriangle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-700">{displayError}</p>
        </div>
      )}
    </div>
  )
}

// ── LineItemRow ──────────────────────────────────────────────────────────────

function LineItemRow({
  item,
  index,
  onChangeText,
  onChangeNumber,
  onRemove,
  canRemove,
}: {
  item: EditableLineItem
  index: number
  onChangeText: (field: 'product_name' | 'nafdac_registration' | 'manufacturer' | 'batch_number' | 'expiry_date' | 'unit', value: string) => void
  onChangeNumber: (field: 'quantity' | 'unit_price', value: number) => void
  onRemove: () => void
  canRemove: boolean
}) {
  const lineTotal = item.quantity * item.unit_price

  return (
    <tr className="border-b border-gray-100 group">
      <td className="px-3 py-2 text-xs text-gray-400 text-center w-8 select-none">{index + 1}</td>
      <td className="px-3 py-2 min-w-[160px]">
        <input
          value={item.product_name}
          onChange={(e) => onChangeText('product_name', e.target.value)}
          className="w-full text-xs bg-transparent outline-none focus:bg-gray-50 rounded px-1 py-0.5"
          placeholder="Product name"
        />
      </td>
      <td className="px-3 py-2 min-w-[100px]">
        <input
          value={item.nafdac_registration}
          onChange={(e) => onChangeText('nafdac_registration', e.target.value)}
          className="w-full text-xs font-mono bg-transparent outline-none focus:bg-gray-50 rounded px-1 py-0.5"
          placeholder="—"
        />
      </td>
      <td className="px-3 py-2 min-w-[120px]">
        <input
          value={item.manufacturer}
          onChange={(e) => onChangeText('manufacturer', e.target.value)}
          className="w-full text-xs bg-transparent outline-none focus:bg-gray-50 rounded px-1 py-0.5"
          placeholder="—"
        />
      </td>
      <td className="px-3 py-2 w-20">
        <input
          type="number"
          value={item.quantity}
          onChange={(e) => onChangeNumber('quantity', Math.max(1, Number(e.target.value)))}
          className="w-full text-xs bg-transparent outline-none focus:bg-gray-50 rounded px-1 py-0.5 text-right"
          min={1}
        />
      </td>
      <td className="px-3 py-2 w-32">
        <div className="flex items-center gap-0.5">
          <span className="text-xs text-gray-400 flex-shrink-0">₦</span>
          <input
            type="number"
            value={item.unit_price}
            onChange={(e) => onChangeNumber('unit_price', Math.max(0, Number(e.target.value)))}
            className="w-full text-xs bg-transparent outline-none focus:bg-gray-50 rounded px-1 py-0.5 text-right"
            min={0}
          />
        </div>
      </td>
      <td className="px-3 py-2 w-32 text-right">
        <span className="text-xs font-semibold text-gray-700">₦{lineTotal.toLocaleString()}</span>
      </td>
      <td className="px-3 py-2 w-8 text-center">
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition-all"
          >
            <X size={13} />
          </button>
        )}
      </td>
    </tr>
  )
}

// ── ReviewForm ───────────────────────────────────────────────────────────────

function ReviewForm({
  extraction,
  filename,
  onCreated,
}: {
  extraction: ExtractInvoiceResponse
  filename: string
  onCreated: (order: OrderResponse) => void
}) {
  const navigate = useNavigate()
  const { mutate: createOrder, isPending, error: createError } = useCreateOrderFromInvoice()

  const [supplier, setSupplier] = useState<InvoiceSupplier>({ ...extraction.supplier })
  const [items, setItems] = useState<EditableLineItem[]>(() =>
    extraction.line_items.map((it, i) => ({
      _key: `${i}-${it.product_name}`,
      product_name: it.product_name,
      nafdac_registration: it.nafdac_registration ?? '',
      manufacturer: it.manufacturer ?? '',
      batch_number: it.batch_number ?? '',
      expiry_date: it.expiry_date ?? '',
      quantity: it.quantity,
      unit: it.unit,
      unit_price: it.unit_price,
    })),
  )
  const [editableTotals, setEditableTotals] = useState<EditableTotals>({
    discount: extraction.totals.discount,
    vat: extraction.totals.vat,
  })

  const subtotal = items.reduce((s, it) => s + it.quantity * it.unit_price, 0)
  const grandTotal = subtotal - editableTotals.discount + editableTotals.vat

  function updateItemText(
    key: string,
    field: 'product_name' | 'nafdac_registration' | 'manufacturer' | 'batch_number' | 'expiry_date' | 'unit',
    value: string,
  ) {
    setItems((prev) => prev.map((it) => (it._key === key ? { ...it, [field]: value } : it)))
  }

  function updateItemNumber(key: string, field: 'quantity' | 'unit_price', value: number) {
    setItems((prev) => prev.map((it) => (it._key === key ? { ...it, [field]: value } : it)))
  }

  function removeItem(key: string) {
    setItems((prev) => prev.filter((it) => it._key !== key))
  }

  function addItem() {
    setItems((prev) => [
      ...prev,
      {
        _key: `new-${Date.now()}`,
        product_name: '',
        nafdac_registration: '',
        manufacturer: '',
        batch_number: '',
        expiry_date: '',
        quantity: 1,
        unit: 'units',
        unit_price: 0,
      },
    ])
  }

  function updateSupplierField(field: keyof Omit<InvoiceSupplier, 'bank_account'>, value: string) {
    setSupplier((s) => ({ ...s, [field]: value }))
  }

  function updateBankField(field: keyof InvoiceBankAccount, value: string) {
    setSupplier((s) => ({ ...s, bank_account: { ...s.bank_account, [field]: value } }))
  }

  function handleSubmit() {
    if (items.length === 0 || grandTotal <= 0) return

    const lineItems: InvoiceLineItem[] = items.map((it, i) => ({
      line_number: i + 1,
      product_name: it.product_name,
      nafdac_registration: it.nafdac_registration || null,
      manufacturer: it.manufacturer || null,
      batch_number: it.batch_number || null,
      expiry_date: it.expiry_date || null,
      quantity: it.quantity,
      unit: it.unit,
      unit_price: it.unit_price,
      line_total: it.quantity * it.unit_price,
    }))

    createOrder(
      {
        supplier,
        buyer: extraction.buyer,
        invoice_metadata: extraction.invoice_metadata,
        line_items: lineItems,
        totals: {
          subtotal,
          discount: editableTotals.discount,
          vat: editableTotals.vat,
          grand_total: grandTotal,
        },
      },
      {
        onSuccess: (order) => {
          saveOrder(order, {
            expected_nafdac: items[0]?.nafdac_registration || undefined,
            expected_manufacturer: items[0]?.manufacturer || undefined,
            expected_product: items[0]?.product_name || undefined,
          })
          onCreated(order)
        },
      },
    )
  }

  const canSubmit = items.length > 0 && grandTotal > 0 && !isPending

  const supplierFields: { label: string; value: string; onUpdate: (v: string) => void }[] = [
    { label: 'Name', value: supplier.name, onUpdate: (v) => updateSupplierField('name', v) },
    { label: 'RC Number', value: supplier.rc_number, onUpdate: (v) => updateSupplierField('rc_number', v) },
    { label: 'Bank', value: supplier.bank_account.bank_name, onUpdate: (v) => updateBankField('bank_name', v) },
    { label: 'Account No.', value: supplier.bank_account.account_number, onUpdate: (v) => updateBankField('account_number', v) },
  ]

  const buyerFields = [
    { label: 'Name', val: extraction.buyer.name },
    { label: 'Email', val: extraction.buyer.email },
    { label: 'Phone', val: extraction.buyer.phone },
    { label: 'Invoice No.', val: extraction.invoice_metadata.invoice_number },
  ]

  return (
    <div className="space-y-5">
      {/* Banner */}
      <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-xl px-4 py-3">
        <CheckCircle2 size={14} className="text-green-600 flex-shrink-0" />
        <p className="text-xs font-medium text-green-800">
          Extracted from <span className="font-bold">{filename}</span> — review and correct before continuing
        </p>
      </div>

      {/* Supplier & buyer cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Supplier</h3>
            <button
              type="button"
              onClick={() => navigate('/verify-supplier')}
              className="text-xs text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1"
            >
              Change <ArrowRight size={11} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {supplierFields.map(({ label, value, onUpdate }) => (
              <div key={label}>
                <p className="text-[9px] text-gray-400 uppercase tracking-widest mb-0.5">{label}</p>
                <input
                  value={value}
                  onChange={(e) => onUpdate(e.target.value)}
                  className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Buyer</h3>
          <div className="grid grid-cols-2 gap-2">
            {buyerFields.map(({ label, val }) => (
              <div key={label}>
                <p className="text-[9px] text-gray-400 uppercase tracking-widest mb-0.5">{label}</p>
                <p className="text-xs text-gray-700 font-medium truncate">{val || '—'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Line items table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 className="text-xs font-bold text-gray-700">Line Items</h3>
          <span className="text-[10px] text-gray-400">
            {items.length} item{items.length !== 1 ? 's' : ''}
          </span>
        </div>
        {items.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-xs text-gray-400">No items extracted — add them manually below.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-center w-8">
                    #
                  </th>
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-left">
                    Product
                  </th>
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-left">
                    NAFDAC Reg
                  </th>
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-left">
                    Manufacturer
                  </th>
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-right w-20">
                    Qty
                  </th>
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-right w-32">
                    Unit Price
                  </th>
                  <th className="px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-400 text-right w-32">
                    Line Total
                  </th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <LineItemRow
                    key={item._key}
                    item={item}
                    index={index}
                    onChangeText={(field, value) => updateItemText(item._key, field, value)}
                    onChangeNumber={(field, value) => updateItemNumber(item._key, field, value)}
                    onRemove={() => removeItem(item._key)}
                    canRemove={items.length > 1}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="px-4 py-2.5 border-t border-gray-50">
          <button
            type="button"
            onClick={addItem}
            className="flex items-center gap-1.5 text-xs text-blue-600 font-medium hover:text-blue-700 transition-colors"
          >
            <Plus size={13} /> Add line item
          </button>
        </div>
      </div>

      {/* Totals */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 max-w-xs ml-auto space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">Subtotal</span>
          <span className="text-gray-700 font-medium">₦{subtotal.toLocaleString()}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">Discount</span>
          <div className="flex items-center gap-1">
            <span className="text-gray-400">₦</span>
            <input
              type="number"
              value={editableTotals.discount}
              onChange={(e) =>
                setEditableTotals((t) => ({ ...t, discount: Math.max(0, Number(e.target.value)) }))
              }
              className="w-20 text-xs text-right border border-gray-200 rounded px-1.5 py-0.5 outline-none focus:border-blue-400"
              min={0}
            />
          </div>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">VAT</span>
          <div className="flex items-center gap-1">
            <span className="text-gray-400">₦</span>
            <input
              type="number"
              value={editableTotals.vat}
              onChange={(e) =>
                setEditableTotals((t) => ({ ...t, vat: Math.max(0, Number(e.target.value)) }))
              }
              className="w-20 text-xs text-right border border-gray-200 rounded px-1.5 py-0.5 outline-none focus:border-blue-400"
              min={0}
            />
          </div>
        </div>
        <div className="border-t border-gray-200 pt-2.5 flex items-center justify-between">
          <span className="text-sm font-bold text-gray-900">Grand Total</span>
          <span className="text-sm font-bold text-gray-900">₦{grandTotal.toLocaleString()}</span>
        </div>
      </div>

      {createError && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          <AlertTriangle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-700">Failed to create order: {createError.message}</p>
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 disabled:opacity-60 transition-colors"
      >
        {isPending ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Creating escrow account...
          </>
        ) : (
          <>
            Create escrow account <ArrowRight size={15} />
          </>
        )}
      </button>
      <p className="text-center text-xs text-gray-400">
        This will create a dedicated Squad virtual account for this order.
      </p>
    </div>
  )
}

// ── FundEscrow ───────────────────────────────────────────────────────────────

function FundEscrow({
  order,
  supplierName,
  onNext,
}: {
  order: OrderResponse
  supplierName: string
  onNext: () => void
}) {
  const [copied, setCopied] = useState(false)
  const [showSimModal, setShowSimModal] = useState(false)
  const [simMessage, setSimMessage] = useState('')
  const { mutate: simulate, isPending } = useSimulatePayment(order.id)

  function handleCopy() {
    if (order.virtual_account_number) {
      navigator.clipboard.writeText(order.virtual_account_number).catch(() => {})
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const accountNumber = order.virtual_account_number ?? '—'
  const accountName = order.virtual_account_name ?? `ERI-${order.id.toUpperCase()}`
  const bankName = order.virtual_account_bank ?? 'Guaranty Trust Bank'
  const amount = order.amount_ngn.toLocaleString()

  useEffect(() => {
    if (!showSimModal) return undefined
    const timeout = window.setTimeout(() => {
      setShowSimModal(false)
      onNext()
    }, 1400)
    return () => window.clearTimeout(timeout)
  }, [onNext, showSimModal])

  function handleSimulateTransfer() {
    simulate(undefined, {
      onSuccess: (result) => {
        updateStoredOrderStatus(order.id, 'funded')
        setSimMessage(result.message)
        setShowSimModal(true)
      },
    })
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gray-900 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
            {supplierName.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-sm text-gray-900">{supplierName}</p>
            <span className="inline-flex items-center gap-1 text-green-600 text-[10px] font-semibold">
              <CheckCircle2 size={9} /> Verified Supplier
            </span>
          </div>
        </div>
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
            Squad webhooks detect payment automatically. Once confirmed, funds are locked in escrow
            until delivery is verified.
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
          {
            icon: Shield,
            title: 'Funds held by Squad',
            desc: "Your payment is held in a secure Squad-managed account and never touches Eri's treasury.",
          },
          {
            icon: CheckCircle2,
            title: 'Released on verification',
            desc: 'Funds are only moved to the supplier once you provide the delivery verification code.',
          },
          {
            icon: RefreshCw,
            title: 'Full refund if blocked',
            desc: 'If delivery fails, funds are returned to your source bank within 24h.',
          },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-gray-50 rounded-xl p-3 border border-gray-100">
            <Icon size={14} className="text-gray-500 mb-2" />
            <p className="text-xs font-semibold text-gray-700 mb-1">{title}</p>
            <p className="text-[10px] text-gray-400 leading-snug">{desc}</p>
          </div>
        ))}
      </div>

      <button
        onClick={handleSimulateTransfer}
        disabled={isPending}
        className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-60 transition-colors flex items-center justify-center gap-2"
      >
        {isPending ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <CheckCircle2 size={14} /> Simulate transfer received (demo)
          </>
        )}
      </button>

      {showSimModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-gray-100">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-700">
              <CheckCircle2 size={24} />
            </div>
            <h3 className="text-lg font-bold text-gray-900 text-center">
              Transfer simulated successfully
            </h3>
            <p className="mt-2 text-sm text-gray-600 text-center leading-relaxed">
              {simMessage ||
                'Squad received the sandbox transfer simulation. Escrow will move to funded once the webhook lands.'}
            </p>
            <div className="mt-5 flex justify-center">
              <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-100">
                <div className="h-full w-full animate-pulse rounded-full bg-green-500" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── AwaitDelivery ────────────────────────────────────────────────────────────

function AwaitDelivery({ order, supplierName }: { order: OrderResponse; supplierName: string }) {
  const navigate = useNavigate()

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
          <p className="text-base font-semibold text-gray-800 mb-1">
            Waiting for supplier to confirm shipment
          </p>
          <p className="text-sm text-gray-400 mb-6">
            Once the supplier marks the order as shipped, verify the delivery to release funds.
          </p>
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
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
            Order Summary
          </h3>
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
              <span className="text-sm font-bold text-gray-900">
                ₦{order.amount_ngn.toLocaleString()}
              </span>
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
              {supplierName.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">{supplierName}</p>
              <span className="text-[10px] text-green-600 font-semibold flex items-center gap-1">
                <CheckCircle2 size={9} /> Verified
              </span>
            </div>
          </div>
        </div>

        {order.virtual_account_number && (
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
              Escrow Account
            </h3>
            <div className="mb-2.5">
              <p className="text-[9px] text-gray-400 uppercase tracking-widest">ACCOUNT NUMBER</p>
              <p className="text-xs font-mono font-semibold text-gray-800">
                {order.virtual_account_number}
              </p>
            </div>
            {order.virtual_account_name && (
              <div>
                <p className="text-[9px] text-gray-400 uppercase tracking-widest">ACCOUNT NAME</p>
                <p className="text-xs font-mono font-semibold text-gray-800">
                  {order.virtual_account_name}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
          <Shield size={18} className="text-green-600 mx-auto mb-2" />
          <p className="text-xs text-green-700 font-medium leading-snug">
            This transaction is insured by the Eri Escrow Guarantee up to ₦5,000,000
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function OrderNew() {
  const navigate = useNavigate()
  const { mutate: extractInvoice, isPending: isExtracting, error: extractError } = useExtractInvoice()

  const [phase, setPhase] = useState<PagePhase>('upload')
  const [extraction, setExtraction] = useState<ExtractInvoiceResponse | null>(null)
  const [filename, setFilename] = useState('')
  const [order, setOrder] = useState<OrderResponse | null>(null)

  function handleFile(file: File) {
    setFilename(file.name)
    extractInvoice(file, {
      onSuccess: (data) => {
        setExtraction(data)
        setPhase('review')
      },
    })
  }

  const supplierName = extraction?.supplier.name ?? order?.supplier_name ?? '—'

  const pageTitle =
    phase === 'fund'
      ? 'Fund escrow'
      : phase === 'await'
      ? 'Awaiting delivery'
      : 'Create order'

  const pageSubtitle =
    phase === 'upload' || phase === 'review'
      ? 'Step 1 of 3 — Upload and review your invoice before creating an escrow account.'
      : null

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-2">
        <span onClick={() => navigate('/orders')} className="hover:text-gray-600 cursor-pointer">
          Orders
        </span>
        <span>›</span>
        <span className="text-gray-600 font-medium">New order</span>
      </div>

      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{pageTitle}</h1>
          {pageSubtitle && <p className="text-xs text-gray-400 mt-0.5">{pageSubtitle}</p>}
        </div>
        <StepIndicator phase={phase} />
      </div>

      {phase === 'upload' && (
        <InvoiceDropZone
          onFile={handleFile}
          isLoading={isExtracting}
          error={extractError?.message}
        />
      )}

      {phase === 'review' && extraction && (
        <ReviewForm
          extraction={extraction}
          filename={filename}
          onCreated={(o) => {
            setOrder(o)
            setPhase('fund')
          }}
        />
      )}

      {phase === 'fund' && order && (
        <FundEscrow
          order={order}
          supplierName={supplierName}
          onNext={() => {
            setOrder((current) => (current ? { ...current, status: 'funded' } : current))
            setPhase('await')
          }}
        />
      )}

      {phase === 'await' && order && (
        <AwaitDelivery order={order} supplierName={supplierName} />
      )}
    </div>
  )
}
