import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  ShieldCheck,
  ShoppingCart,
  Building2,
  Settings,
  HelpCircle,
  LogOut,
  Bell,
  RefreshCw,
  Search,
} from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/verify-supplier', icon: ShieldCheck, label: 'Verify Supplier' },
  { to: '/orders', icon: ShoppingCart, label: 'Orders' },
  { to: '/suppliers', icon: Building2, label: 'Suppliers' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const navigate = useNavigate()

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col bg-[#0f1117] text-white overflow-y-auto">
        {/* Brand */}
        <div className="px-5 pt-6 pb-4">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center">
              <ShieldCheck size={15} className="text-white" />
            </div>
            <span className="font-bold text-base tracking-tight">TrustLock</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-1">Enterprise Tier</p>
          <p className="text-[10px] text-gray-500">1626 Free unlocks</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-2 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-[#1e2a4a] text-white font-medium'
                    : 'text-gray-400 hover:bg-[#1a1d27] hover:text-gray-200'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Bottom */}
        <div className="px-2 pb-4 space-y-0.5">
          <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#1a1d27] hover:text-gray-200 transition-colors">
            <HelpCircle size={16} />
            Support
          </button>
          <button
            onClick={() => navigate('/login')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#1a1d27] hover:text-gray-200 transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>

          {/* User info */}
          <div className="mt-3 px-3 pt-3 border-t border-gray-800">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center text-xs font-bold text-white">
                A
              </div>
              <div>
                <p className="text-xs font-medium text-white leading-tight">Adaeze Okonkwo</p>
                <p className="text-[10px] text-gray-500">Buyer Manager</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top nav */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6 gap-4 flex-shrink-0">
          <div className="flex-1 relative max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search orders, suppliers..."
              className="w-full pl-9 pr-4 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            />
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors">
              <Bell size={16} className="text-gray-500" />
            </button>
            <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors">
              <RefreshCw size={16} className="text-gray-500" />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-xs font-bold text-white">
                A
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-semibold text-gray-800 leading-tight">Adaeze O.</p>
                <p className="text-[10px] text-gray-500">Buyer Manager</p>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
