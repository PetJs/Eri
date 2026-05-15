import { useNavigate } from 'react-router-dom'
import { Plus, CheckCircle2, AlertTriangle, XCircle, ArrowRight } from 'lucide-react'
import { getStoredSuppliers } from '../../lib/storage'

function VerdictBadge({ verdict, score }: { verdict: string; score: number }) {
  if (verdict === 'green' || score >= 71) {
    return (
      <span className="inline-flex items-center gap-1 bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
        <CheckCircle2 size={9} /> TRUSTED
      </span>
    )
  }
  if (verdict === 'amber' || score >= 50) {
    return (
      <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
        <AlertTriangle size={9} /> CAUTION
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
      <XCircle size={9} /> HIGH RISK
    </span>
  )
}

export default function SupplierList() {
  const navigate = useNavigate()
  const suppliers = getStoredSuppliers()

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Verified Suppliers</h1>
          <p className="text-sm text-gray-500 mt-0.5">{suppliers.length} supplier{suppliers.length !== 1 ? 's' : ''} verified</p>
        </div>
        <button
          onClick={() => navigate('/verify-supplier')}
          className="flex items-center gap-2 bg-gray-900 text-white px-4 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
        >
          <Plus size={15} /> Verify new supplier
        </button>
      </div>

      {suppliers.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
          <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-gray-200">
            <CheckCircle2 size={24} className="text-gray-300" />
          </div>
          <p className="text-sm font-medium text-gray-500 mb-1">No suppliers verified yet</p>
          <p className="text-xs text-gray-400 mb-5">Run a supplier verification to see results here.</p>
          <button
            onClick={() => navigate('/verify-supplier')}
            className="inline-flex items-center gap-2 bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
          >
            Verify a supplier <ArrowRight size={14} />
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Company</th>
                <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">RC Number</th>
                <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Bank · Account</th>
                <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Trust Score</th>
                <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Verdict</th>
                <th className="text-left px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">Verified</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {suppliers.map((s, i) => (
                <tr
                  key={i}
                  onClick={() => navigate('/verify-supplier')}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ${
                        s.score >= 71 ? 'bg-green-700' : s.score >= 50 ? 'bg-amber-600' : 'bg-red-600'
                      }`}>
                        {s.name.slice(0, 2).toUpperCase()}
                      </div>
                      <span className="font-medium text-gray-900 text-xs">{s.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-gray-500 text-xs">{s.rc}</td>
                  <td className="px-5 py-3.5 text-gray-500 text-xs">{s.bank} · {s.account}</td>
                  <td className="px-5 py-3.5">
                    <span className={`text-sm font-bold ${s.score >= 71 ? 'text-green-600' : s.score >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                      {s.score}
                    </span>
                    <span className="text-xs text-gray-400">/100</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <VerdictBadge verdict={s.verdict} score={s.score} />
                  </td>
                  <td className="px-5 py-3.5 text-gray-400 text-xs">
                    {new Date(s.verifiedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </td>
                  <td className="px-5 py-3.5">
                    <ArrowRight size={14} className="text-gray-300" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
