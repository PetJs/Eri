import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertTriangle, Circle, Upload, ArrowRight, ChevronDown } from 'lucide-react'

type CheckState = 'pending' | 'loading' | 'pass' | 'warn' | 'fail'

interface CheckItem {
  label: string
  detail: string
  state: CheckState
}

const INITIAL_CHECKS: CheckItem[] = [
  { label: 'CAC Registration', detail: "Active, registered as 'XYZ Pharmaceuticals Ltd' since 2002", state: 'pending' },
  { label: 'NAFDAC License', detail: 'License expired November 2024', state: 'pending' },
  { label: 'Bank Name Match', detail: '94% match between business name and bank account name', state: 'pending' },
  { label: 'Phone Verification', detail: 'Number is registered and not in fraud blacklist', state: 'pending' },
  { label: 'Prior Performance', detail: '2 prior buyers reported significant delivery delays', state: 'pending' },
  { label: 'Invoice Consistency', detail: 'Invoice details match supplier records', state: 'pending' },
]

const FINAL_STATES: CheckState[] = ['pass', 'warn', 'pass', 'pass', 'warn', 'pass']

function TrustScoreRing({ score }: { score: number }) {
  const r = 72
  const cx = 88
  const cy = 88
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - score / 100)
  const color = score >= 71 ? '#16a34a' : score >= 50 ? '#d97706' : '#dc2626'
  const label = score >= 71 ? 'TRUSTED' : score >= 50 ? 'CAUTION' : 'HIGH RISK'
  const labelColor = score >= 71 ? 'text-green-600' : score >= 50 ? 'text-amber-600' : 'text-red-600'

  return (
    <div className="flex flex-col items-center">
      <svg width="176" height="176" className="transform -rotate-90">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e5e7eb" strokeWidth="12" />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.2s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold text-gray-900">{score}</span>
        <span className="text-xs text-gray-400 font-medium">/100</span>
      </div>
      <p className={`text-xs font-bold mt-2 uppercase tracking-widest ${labelColor}`}>{label}</p>
      <p className="text-[10px] text-gray-400 mt-0.5">Verified 1 second ago</p>
    </div>
  )
}

function CheckRow({ item }: { item: CheckItem }) {
  const isLoading = item.state === 'loading'
  const isPending = item.state === 'pending'

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-100 last:border-0">
      <div className="flex-shrink-0 mt-0.5">
        {item.state === 'pass' && <CheckCircle2 size={16} className="text-green-500" />}
        {item.state === 'warn' && <AlertTriangle size={16} className="text-amber-500" />}
        {item.state === 'fail' && <AlertTriangle size={16} className="text-red-500" />}
        {(isLoading || isPending) && (
          <div className={`w-4 h-4 rounded-full border-2 ${isLoading ? 'border-blue-400 border-t-transparent animate-spin' : 'border-gray-300'}`} />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">{item.label}</p>
        {(item.state === 'pass' || item.state === 'warn' || item.state === 'fail') ? (
          <p className="text-xs text-gray-500 mt-0.5 leading-snug">{item.detail}</p>
        ) : isLoading ? (
          <p className="text-xs text-gray-400 mt-0.5">Verifying...</p>
        ) : (
          <p className="text-xs text-gray-300 mt-0.5">Loading...</p>
        )}
      </div>
    </div>
  )
}

export default function VerifySupplier() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<'form' | 'verifying' | 'result'>('form')
  const [checks, setChecks] = useState<CheckItem[]>(INITIAL_CHECKS)
  const [form, setForm] = useState({
    company: '',
    rc: '',
    industry: 'Healthcare',
    bank: '',
    account: '',
    phone: '',
  })

  useEffect(() => {
    if (phase !== 'verifying') return

    const setChecksLoading = () =>
      setChecks((c) => c.map((item) => ({ ...item, state: 'loading' as CheckState })))
    const revealChecks = () => {
      setChecks((c) =>
        c.map((item, i) => ({
          ...item,
          state: FINAL_STATES[i],
        }))
      )
      setTimeout(() => setPhase('result'), 600)
    }

    const t1 = setTimeout(setChecksLoading, 300)
    const t2 = setTimeout(revealChecks, 2800)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [phase])

  function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    setChecks(INITIAL_CHECKS)
    setPhase('verifying')
  }

  function handleReset() {
    setPhase('form')
    setChecks(INITIAL_CHECKS)
  }

  const demoFill = () =>
    setForm({
      company: 'MedTrust Nigeria Ltd',
      rc: 'RC 1234567',
      industry: 'Healthcare',
      bank: 'GTBank',
      account: '81234567B9',
      phone: '+234 801 234 5678',
    })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Verify Supplier</h1>
        <p className="text-sm text-gray-500 mt-0.5">Institutional KYC & AML Due Diligence</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Form */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-sm text-gray-700 mb-5">Entity Information</h2>
          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Company Registered Name</label>
              <input
                type="text"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                placeholder="MedTrust Nigeria Ltd"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">RC Number</label>
                <input
                  type="text"
                  value={form.rc}
                  onChange={(e) => setForm({ ...form, rc: e.target.value })}
                  placeholder="RC 1234567"
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Industry Segment</label>
                <div className="relative">
                  <select
                    value={form.industry}
                    onChange={(e) => setForm({ ...form, industry: e.target.value })}
                    className="w-full appearance-none px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-white"
                  >
                    <option>Healthcare</option>
                    <option>Pharmaceuticals</option>
                    <option>Government</option>
                    <option>Construction</option>
                    <option>Logistics</option>
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Bank Name</label>
                <input
                  type="text"
                  value={form.bank}
                  onChange={(e) => setForm({ ...form, bank: e.target.value })}
                  placeholder="GTBank"
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Account Number</label>
                <input
                  type="text"
                  value={form.account}
                  onChange={(e) => setForm({ ...form, account: e.target.value })}
                  placeholder="0123456789"
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Verified Contact Number</label>
              <input
                type="text"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+234 801 234 5678"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
              />
            </div>

            {/* Invoice upload */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Invoice upload</label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-200 rounded-xl p-6 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-colors">
                <Upload size={20} className="text-gray-400 mb-2" />
                <p className="text-xs text-gray-500 text-center">
                  Drag your invoice PDF here, or{' '}
                  <span className="text-blue-600 font-medium">browse files</span>
                </p>
                <p className="text-[10px] text-gray-400 mt-1">Max file size: 5MB</p>
                <input type="file" accept=".pdf,image/*" className="hidden" />
              </label>
            </div>

            <div className="flex gap-3 pt-1">
              <button
                type="button"
                onClick={demoFill}
                className="flex-shrink-0 px-4 py-2.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Fill demo data
              </button>
              <button
                type="submit"
                className="flex-1 flex items-center justify-center gap-2 bg-gray-900 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
              >
                Run Verification <ArrowRight size={15} />
              </button>
            </div>
          </form>
        </div>

        {/* Right: Result panel */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          {phase === 'form' && (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mb-4 border border-gray-200">
                <Circle size={32} className="text-gray-300" />
              </div>
              <p className="text-sm font-medium text-gray-500">Enter supplier details and run verification</p>
              <p className="text-xs text-gray-400 mt-1">Results will appear here</p>
            </div>
          )}

          {(phase === 'verifying' || phase === 'result') && (
            <>
              {/* Score ring — only in result */}
              {phase === 'result' && (
                <div className="relative flex justify-center mb-6 pt-2">
                  <TrustScoreRing score={62} />
                </div>
              )}

              {phase === 'verifying' && (
                <div className="text-center mb-6">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    <h2 className="text-base font-semibold text-gray-800">Verifying...</h2>
                  </div>
                  <p className="text-xs text-gray-400">Cross-checking 6 public registries...</p>
                </div>
              )}

              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">
                {phase === 'result' ? 'Verification Breakdown' : 'Live Checks'}
              </h3>
              <div>
                {checks.map((item) => (
                  <CheckRow key={item.label} item={item} />
                ))}
              </div>

              {phase === 'result' && (
                <div className="mt-5 space-y-3">
                  <button
                    onClick={() => navigate('/orders/new')}
                    className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
                  >
                    Proceed to escrow <ArrowRight size={15} />
                  </button>
                  <button
                    onClick={handleReset}
                    className="w-full py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                  >
                    Save and review later
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer note */}
      <p className="text-center text-[10px] text-gray-400 mt-4">
        © 2026 TrustLock Financial Services. All verifications are real-time.
      </p>
    </div>
  )
}
