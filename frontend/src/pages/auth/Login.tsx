import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, ArrowRight, Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex flex-1">
        {/* Left panel */}
        <div className="flex-1 bg-white flex flex-col">
          {/* Brand */}
          <div className="p-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-blue-600 rounded-md flex items-center justify-center">
                <Shield size={12} className="text-white" />
              </div>
              <span className="font-bold text-sm text-gray-900">TrustLock</span>
            </div>
          </div>

          {/* Form */}
          <div className="flex-1 flex items-center justify-center px-10">
            <div className="w-full max-w-sm">
              <h1 className="text-2xl font-bold text-gray-900 mb-1.5">Welcome back</h1>
              <p className="text-sm text-gray-500 mb-8">
                Sign in to verify suppliers, manage escrows, and release payments.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.ng"
                    required
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-50 transition-all"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-sm font-medium text-gray-700">Password</label>
                    <a href="#" className="text-sm text-blue-600 hover:text-blue-700 transition-colors">
                      Forgot password?
                    </a>
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="w-full px-3 py-2.5 pr-10 text-sm border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-50 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors mt-2"
                >
                  Sign in <ArrowRight size={15} />
                </button>
              </form>

              <p className="text-center text-sm text-gray-500 mt-6">
                Don't have an account?{' '}
                <a href="#" className="text-blue-600 font-medium hover:text-blue-700 transition-colors">
                  Sign up
                </a>
              </p>
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="hidden lg:flex w-[45%] bg-[#0a0a0f] flex-col items-center justify-center px-16 relative">
          <div className="max-w-sm">
            <p className="text-gray-600 text-5xl font-serif mb-6 leading-none">"</p>
            <blockquote className="text-gray-200 text-lg font-medium leading-relaxed mb-8">
              "TrustLock caught a fake NAFDAC number we would have paid for. The system saved us ₦2 million in one transaction."
            </blockquote>
            <div>
              <p className="text-white text-sm font-semibold">Adaeze O.</p>
              <p className="text-gray-500 text-xs mt-0.5">
                Procurement Lead, [Anonymous Pharmacy Chain]
              </p>
            </div>
          </div>

          {/* Bottom badges */}
          <div className="absolute bottom-6 left-6 right-6 flex items-center gap-3">
            <div className="inline-flex items-center gap-2 bg-[#1a1a2e] text-gray-400 text-[10px] font-bold px-3 py-1.5 rounded-full border border-gray-800">
              <Shield size={10} className="text-blue-400" />
              CITBANK SECURITY
            </div>
            <div className="inline-flex items-center gap-2 bg-[#1a1a2e] text-gray-400 text-[10px] font-bold px-3 py-1.5 rounded-full border border-gray-800">
              <Shield size={10} className="text-green-400" />
              NDPR COMPLIANT
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 px-10 py-3 flex items-center justify-between">
        <div className="inline-flex items-center gap-1.5 bg-pink-500 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">
          <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
          BUILT ON SQUAD
        </div>
        <nav className="flex items-center gap-5">
          {['Privacy Policy', 'Terms of Service', 'Cookie Settings', 'Compliance'].map((l) => (
            <a key={l} href="#" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
              {l}
            </a>
          ))}
        </nav>
        <p className="text-xs text-gray-400">v1.6.1-beta</p>
      </footer>
    </div>
  )
}
