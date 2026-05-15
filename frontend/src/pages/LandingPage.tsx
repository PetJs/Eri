import { useNavigate } from 'react-router-dom'
import { Shield, Search, CheckCircle, ArrowRight, Globe, Share2, Briefcase, Landmark } from 'lucide-react'
import heroImg from '../assets/hero.png'

const steps = [
  { label: 'BUYER', sub: 'Initiates Order' },
  { label: 'VERIFY', sub: 'KYC / Compliance' },
  { label: 'ESCROW', sub: 'Locked Funds', active: true },
  { label: 'VERIFY', sub: 'Delivery Check' },
  { label: 'RELEASE', sub: 'Smart Payment' },
  { label: 'SUPPLIER', sub: 'Settlement' },
]

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-white text-gray-900 font-sans">

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center gap-8">
          <div className="flex items-center gap-2 mr-4">
            <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center">
              <Shield size={14} className="text-white" />
            </div>
            <span className="font-bold text-base">Eri</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-600">
            <a href="#how" className="hover:text-gray-900 transition-colors">How it works</a>
            <a href="#healthcare" className="hover:text-gray-900 transition-colors">For Healthcare</a>
            <a href="#government" className="hover:text-gray-900 transition-colors">For Government</a>
            <a href="#squad" className="hover:text-gray-900 transition-colors">Built on Squad</a>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <button
              onClick={() => navigate('/login')}
              className="text-sm text-gray-600 hover:text-gray-900 font-medium transition-colors px-3 py-1.5"
            >
              Log In
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="text-sm bg-gray-900 text-white px-4 py-2 rounded-lg font-medium hover:bg-gray-700 transition-colors"
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16 flex flex-col md:flex-row items-center gap-12">
        <div className="flex-1 max-w-xl">
          <div className="inline-flex items-center gap-2 bg-gray-900 text-white text-[10px] font-semibold tracking-widest uppercase px-3 py-1.5 rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-pink-400 rounded-full animate-pulse" />
            BUILT ON SQUAD · CHALLENGE 01: PROOF OF LIFE
          </div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-none mb-6">
            Trust before<br />you transfer.
          </h1>
          <p className="text-gray-500 text-lg leading-relaxed mb-10">
            AI-gated escrow for Nigerian procurement. We secure high-stakes
            transactions by verifying identities and authenticating goods before
            releasing payments.
          </p>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 bg-gray-900 text-white px-6 py-3 rounded-lg font-medium text-sm hover:bg-gray-700 transition-colors"
            >
              Try the demo <ArrowRight size={16} />
            </button>
            <a href="#how" className="text-sm text-gray-600 font-medium hover:text-gray-900 transition-colors">
              How it works
            </a>
          </div>
        </div>
        <div className="flex-1 flex justify-center md:justify-end">
          <img
            src={heroImg}
            alt="Eri verification platform"
            className="w-full max-w-md rounded-2xl object-cover"
            draggable={false}
          />
        </div>
      </section>

      {/* Stats */}
      <section className="bg-gray-50 border-y border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-200 text-center">
            {[
              { value: '90%+', label: 'PROCUREMENT FRAUD RATE' },
              { value: '₦3 trillion', label: 'ANNUAL TRANSACTION LOSS' },
              { value: '13–50%', label: 'COUNTERFEIT DRUG PENETRATION' },
            ].map(({ value, label }) => (
              <div key={label} className="py-6 md:py-0 md:px-8">
                <p className="text-4xl font-bold text-gray-900 mb-2">{value}</p>
                <p className="text-xs font-semibold tracking-widest text-gray-400 uppercase">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Three checks */}
      <section id="how" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold mb-3">Three checks. One release.</h2>
          <p className="text-gray-500">Our verification engine automates trust at every milestone.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: Shield,
              title: 'Supplier Verified',
              desc: "Real-time CAC, TIN, and bank account verification using Squad's deep data APIs.",
              active: false,
            },
            {
              icon: Search,
              title: 'Goods Authenticated',
              desc: 'AI-powered visual inspection and NAFDAC number validation for medical supplies.',
              active: true,
            },
            {
              icon: CheckCircle,
              title: 'Anomalies Caught',
              desc: 'Pattern matching for price inflation and duplicate invoicing across government channels.',
              active: false,
            },
          ].map(({ icon: Icon, title, desc, active }) => (
            <div
              key={title}
              className={`p-8 rounded-2xl border ${
                active
                  ? 'bg-blue-600 border-blue-600 text-white'
                  : 'bg-white border-gray-200 text-gray-800'
              }`}
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-5 ${
                active ? 'bg-white/20' : 'bg-gray-100'
              }`}>
                <Icon size={20} className={active ? 'text-white' : 'text-gray-600'} />
              </div>
              <h3 className="font-semibold text-lg mb-2">{title}</h3>
              <p className={`text-sm leading-relaxed ${active ? 'text-blue-100' : 'text-gray-500'}`}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How money moves */}
      <section className="bg-gray-50 border-y border-gray-100 py-16">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-12">How money moves through Eri</h2>
          <div className="flex items-center justify-center flex-wrap gap-0">
            {steps.map((step, i) => (
              <div key={i} className="flex items-center">
                <div className={`px-4 py-3 rounded-lg text-center min-w-[100px] ${
                  step.active
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white border border-gray-200 text-gray-600'
                }`}>
                  <p className={`text-xs font-bold ${step.active ? 'text-white' : 'text-gray-800'}`}>{step.label}</p>
                  <p className={`text-[10px] mt-0.5 ${step.active ? 'text-blue-200' : 'text-gray-400'}`}>{step.sub}</p>
                </div>
                {i < steps.length - 1 && (
                  <div className="w-6 flex items-center justify-center">
                    <ArrowRight size={12} className="text-gray-300" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Sectors */}
      <section id="healthcare" className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-2xl font-bold text-center mb-12">
          Built for Nigeria's most fraud-exposed sectors
        </h2>
        <div id="government" className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[
            {
              icon: Briefcase,
              title: 'Healthcare procurement',
              points: [
                'Verified pharmaceutical supply chains with NAFDAC tracking.',
                'Proof-of-Life verification for high-value equipment deliveries.',
                'Automated escrow release upon digital signature of medical directors.',
              ],
            },
            {
              icon: Landmark,
              title: 'Government & corporate procurement',
              points: [
                'Strict KYC/AML compliance via direct CAC portal integration.',
                'Immutable audit logs for anti-corruption compliance.',
                'Milestone-based payouts for complex infrastructure projects.',
              ],
            },
          ].map(({ icon: Icon, title, points }) => (
            <div key={title} className="p-8 bg-white rounded-2xl border border-gray-200">
              <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center mb-5">
                <Icon size={20} className="text-gray-600" />
              </div>
              <h3 className="font-semibold text-lg mb-4 text-gray-900">{title}</h3>
              <ul className="space-y-2">
                {points.map((p) => (
                  <li key={p} className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle size={14} className="text-blue-500 mt-0.5 flex-shrink-0" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gray-900 text-white">
        <div className="max-w-2xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold mb-3">Stop praying. Start verifying.</h2>
          <p className="text-gray-400 mb-8">
            Modernize your procurement workflow with Nigeria's most secure escrow engine.
            Built on the resilience of Squad.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-white text-gray-900 px-8 py-3 rounded-lg font-semibold text-sm hover:bg-gray-100 transition-colors"
          >
            Request demo access
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="flex flex-col md:flex-row gap-10">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 bg-blue-600 rounded-md flex items-center justify-center">
                  <Shield size={12} className="text-white" />
                </div>
                <span className="font-bold text-sm">Eri</span>
              </div>
              <div className="inline-flex items-center gap-1.5 bg-pink-500 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">
                <span className="w-1.5 h-1.5 bg-white rounded-full" />
                BUILT ON SQUAD
              </div>
            </div>
            {[
              { heading: 'PLATFORM', links: ['How it works', 'Verification APIs', 'Pricing'] },
              { heading: 'SECTORS', links: ['Healthcare', 'Government', 'Construction'] },
              { heading: 'LEGAL', links: ['Terms of Service', 'Privacy Policy', 'Security Compliance'] },
            ].map(({ heading, links }) => (
              <div key={heading}>
                <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-4">{heading}</p>
                <ul className="space-y-2">
                  {links.map((l) => (
                    <li key={l}>
                      <a href="#" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">{l}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-10 pt-6 border-t border-gray-100 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-gray-400">© 2026 Eri. All rights reserved.</p>
            <div className="flex items-center gap-4">
              <Share2 size={14} className="text-gray-400 cursor-pointer hover:text-gray-600 transition-colors" />
              <Globe size={14} className="text-gray-400 cursor-pointer hover:text-gray-600 transition-colors" />
            </div>
          </div>
        </div>
      </footer>

    </div>
  )
}
