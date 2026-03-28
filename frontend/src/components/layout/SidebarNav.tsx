import {
  Bell,
  FilePenLine,
  LayoutDashboard,
  Package,
  Settings,
  ShieldCheck,
  Warehouse,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

type SidebarNavProps = {
  onNavigate?: () => void;
};

type NavItem = {
  to: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

const navItems: NavItem[] = [
  {
    to: "/",
    label: "Dashboard",
    description: "Live summary and alert posture",
    icon: LayoutDashboard,
  },
  {
    to: "/products",
    label: "Products",
    description: "Catalog actions and listing health",
    icon: Package,
  },
  {
    to: "/aplus",
    label: "A+ Content Studio",
    description: "Structured draft generation workflow",
    icon: FilePenLine,
  },
  {
    to: "/inventory",
    label: "Inventory",
    description: "Stock monitoring and sync visibility",
    icon: Warehouse,
  },
  {
    to: "/notifications",
    label: "Notifications",
    description: "Slack delivery and event history",
    icon: Bell,
  },
  {
    to: "/settings",
    label: "Settings",
    description: "Operational configuration and checks",
    icon: Settings,
  },
];

export function SidebarNav({ onNavigate }: SidebarNavProps) {
  return (
    <div className="flex h-full flex-col gap-8 px-5 py-6">
      <div className="rounded-[2rem] border border-amber-400/20 bg-gradient-to-br from-amber-300/15 via-slate-900 to-slate-950 p-5">
        <div className="mb-4 inline-flex rounded-2xl bg-amber-300/15 p-3 text-amber-200">
          <ShieldCheck className="h-6 w-6" />
        </div>
        <p className="text-xs uppercase tracking-[0.3em] text-amber-100/60">Seller Admin</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Amazon Seller Ops</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Operations cockpit for content, inventory, pricing, and seller alerts.
        </p>
      </div>

      <nav className="space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                [
                  "group flex items-start gap-4 rounded-[1.5rem] border px-4 py-4 transition",
                  isActive
                    ? "border-amber-300/30 bg-white/10 text-white shadow-lg shadow-black/20"
                    : "border-transparent bg-white/[0.03] text-slate-300 hover:border-white/10 hover:bg-white/[0.06]",
                ].join(" ")
              }
            >
              <div className="rounded-2xl bg-slate-900/80 p-3 text-amber-200 ring-1 ring-white/10 transition group-hover:bg-slate-900">
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium">{item.label}</p>
                <p className="mt-1 text-xs leading-5 text-slate-400">{item.description}</p>
              </div>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

