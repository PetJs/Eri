import { useState } from "react";
import {
  LayoutDashboard,
  ClipboardCheck,
  ShoppingCart,
  Users,
  Settings,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";

type NavItem = {
  id: string;
  label: string;
  icon: LucideIcon;
};

const navItems: NavItem[] = [
  { id: "dashboard",  label: "Dashboard",       icon: LayoutDashboard },
  { id: "verify",     label: "Verify Supplier",  icon: ClipboardCheck  },
  { id: "orders",     label: "Orders",           icon: ShoppingCart    },
  { id: "suppliers",  label: "Suppliers",        icon: Users           },
  { id: "settings",   label: "Settings",         icon: Settings        },
];

export default function TrustLockSidebar() {
  const [active, setActive] = useState("verify");

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900">
      <aside
        className="relative flex flex-col w-64 h-screen bg-black overflow-hidden"
        style={{
          background: "linear-gradient(160deg, #0a0a0f 0%, #080c14 60%, #060810 100%)",
          borderRight: "1px solid rgba(30,80,160,0.18)",
          boxShadow: "4px 0 40px 0 rgba(0,100,255,0.06)",
        }}
      >
        {/* Subtle top glow */}
        <div
          className="absolute top-0 left-0 right-0 h-1 rounded-b"
          style={{
            background: "linear-gradient(90deg, transparent 0%, rgba(59,130,246,0.6) 50%, transparent 100%)",
          }}
        />

        {/* Corner accent dots */}
        <div
          className="absolute top-3 left-3 w-1.5 h-1.5 rounded-full"
          style={{ background: "rgba(59,130,246,0.5)" }}
        />
        <div
          className="absolute bottom-3 left-3 w-1.5 h-1.5 rounded-full"
          style={{ background: "rgba(59,130,246,0.3)" }}
        />
        <div
          className="absolute bottom-3 right-3 w-1.5 h-1.5 rounded-full"
          style={{ background: "rgba(59,130,246,0.3)" }}
        />

        {/* Logo / Brand */}
        <div className="px-6 pt-10 pb-6">
          {/* Accent bar above logo */}
          <div
            className="w-8 h-0.5 mb-4 rounded-full"
            style={{ background: "linear-gradient(90deg, #3b82f6, #6366f1)" }}
          />
          <h1
            className="text-white font-bold tracking-tight leading-none"
            style={{
              fontSize: "1.85rem",
              fontFamily: "'Georgia', 'Times New Roman', serif",
              letterSpacing: "-0.02em",
            }}
          >
            TrustLock
          </h1>
          <p
            className="mt-1.5 text-xs font-medium tracking-widest uppercase"
            style={{ color: "rgba(148,163,184,0.55)", letterSpacing: "0.12em" }}
          >
            Institutional Grade Escrow
          </p>
        </div>

        {/* Divider */}
        <div
          className="mx-6 mb-6 h-px"
          style={{
            background: "linear-gradient(90deg, rgba(59,130,246,0.4) 0%, rgba(59,130,246,0.05) 100%)",
          }}
        />

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-1">
          {navItems.map((item) => {
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActive(item.id)}
                className="relative w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 group"
                style={{
                  background: isActive
                    ? "linear-gradient(90deg, rgba(37,99,235,0.85) 0%, rgba(29,78,216,0.7) 100%)"
                    : "transparent",
                  color: isActive ? "#fff" : "rgba(148,163,184,0.7)",
                  boxShadow: isActive
                    ? "0 0 20px rgba(37,99,235,0.25), inset 0 1px 0 rgba(255,255,255,0.08)"
                    : "none",
                  border: isActive
                    ? "1px solid rgba(59,130,246,0.35)"
                    : "1px solid transparent",
                  fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
                  letterSpacing: "0.01em",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLButtonElement).style.background =
                      "rgba(30,58,138,0.2)";
                    (e.currentTarget as HTMLButtonElement).style.color =
                      "rgba(203,213,225,0.9)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLButtonElement).style.background =
                      "transparent";
                    (e.currentTarget as HTMLButtonElement).style.color =
                      "rgba(148,163,184,0.7)";
                  }
                }}
              >
                {/* Active left-bar indicator */}
                {isActive && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r"
                    style={{
                      background: "linear-gradient(180deg, #60a5fa, #3b82f6)",
                      boxShadow: "0 0 8px #3b82f6",
                    }}
                  />
                )}

                <item.icon
                  size={18}
                  strokeWidth={1.8}
                  style={{ color: isActive ? "#93c5fd" : "inherit", flexShrink: 0 }}
                />

                <span>{item.label}</span>

                {isActive && (
                  <ChevronRight
                    size={14}
                    strokeWidth={2}
                    className="ml-auto opacity-50"
                    color="#93c5fd"
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom accent line */}
        <div
          className="absolute bottom-0 left-0 right-0 h-px"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(59,130,246,0.3), transparent)",
          }}
        />
      </aside>
    </div>
  );
}