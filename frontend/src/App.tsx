import { LayoutDashboard, PackageSearch } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

const routes = [
  { to: "/", label: "Dashboard" },
  { to: "/products", label: "Products" },
  { to: "/aplus", label: "A+ Content Studio" },
  { to: "/inventory", label: "Inventory" },
  { to: "/notifications", label: "Notifications" },
  { to: "/settings", label: "Settings" },
];

export function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-amber-400/15 p-2 text-amber-300">
              <LayoutDashboard className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Admin</p>
              <h1 className="text-lg font-semibold">Amazon Seller Ops</h1>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-slate-800 px-3 py-2 text-sm text-slate-300">
            <PackageSearch className="h-4 w-4" />
            Phase 1 scaffold
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-8 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <nav className="space-y-2">
            {routes.map((route) => (
              <Link
                key={route.to}
                to={route.to}
                className="block rounded-2xl px-4 py-3 text-sm text-slate-300 transition hover:bg-slate-800 hover:text-white"
              >
                {route.label}
              </Link>
            ))}
          </nav>
        </aside>

        <main className="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

