import { BarChart3, Boxes, LogOut, ScrollText, Settings } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

const navItems = [
  { to: "/dashboard", label: "儀表盤", icon: BarChart3 },
  { to: "/detection", label: "識別任務", icon: Boxes },
  { to: "/system", label: "系統配置", icon: Settings },
  { to: "/audit", label: "操作審計", icon: ScrollText },
];

export function AppShell() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  function handleLogout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-haze text-foreground">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-[280px_1fr]">
        <aside className="flex flex-col rounded-3xl border border-white/60 bg-white/80 p-6 shadow-soft backdrop-blur">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-sky-700">RainFog Admin</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-900">YOLOv13 後台系統</h1>
            <p className="mt-2 text-sm text-slate-600">管理圖片、識別任務、結果與系統配置。</p>
          </div>
          <nav className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-sky-900 text-white"
                        : "text-slate-700 hover:bg-sky-50 hover:text-sky-900",
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <div className="mt-auto border-t border-slate-100 pt-5">
            <p className="truncate text-sm font-medium text-slate-800">
              {user?.display_name ?? user?.username ?? "未登入"}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">{user?.roles[0] ?? ""}</p>
            <button
              onClick={handleLogout}
              className="mt-3 flex w-full items-center gap-2 rounded-2xl px-4 py-2.5 text-sm text-slate-600 transition-colors hover:bg-rose-50 hover:text-rose-700"
            >
              <LogOut className="h-4 w-4" />
              登出
            </button>
          </div>
        </aside>

        <main className="rounded-3xl border border-white/60 bg-white/75 p-6 shadow-soft backdrop-blur">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
