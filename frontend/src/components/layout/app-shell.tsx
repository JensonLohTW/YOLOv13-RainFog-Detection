import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";

import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

export function AppShell() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [collapsed, setCollapsed] = useState(false);

  function handleLogout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  return (
    <TooltipProvider delayDuration={300}>
      <div className="min-h-screen bg-slate-50 text-foreground">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
        <Header user={user} onLogout={handleLogout} sidebarCollapsed={collapsed} />

        <main
          className={cn(
            "flex min-h-screen flex-col transition-all duration-200",
            collapsed ? "ml-16" : "ml-60",
          )}
        >
          <div className="flex-1 overflow-y-auto px-6 py-6" style={{ paddingTop: "calc(var(--header-height) + 1.5rem)", paddingBottom: "calc(var(--footer-height) + 1.5rem)" }}>
            <Outlet />
          </div>
        </main>

        <Footer sidebarCollapsed={collapsed} />
      </div>
    </TooltipProvider>
  );
}
