import { LogOut, User } from "lucide-react";
import { useLocation } from "react-router-dom";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NAV_ITEMS } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";
import type { AuthUser } from "@/stores/auth-store";

type HeaderProps = {
  user: AuthUser | null;
  onLogout: () => void;
  sidebarCollapsed: boolean;
};

function getPageLabel(pathname: string): string {
  const match = NAV_ITEMS.find((item) => {
    if (item.to === "/dashboard") return pathname === "/dashboard" || pathname === "/";
    return pathname.startsWith(item.to);
  });
  return match?.label ?? "後台管理";
}

function getUserInitials(user: AuthUser | null): string {
  if (!user) return "?";
  const name = user.display_name || user.username;
  return name.slice(0, 2).toUpperCase();
}

export function Header({ user, onLogout, sidebarCollapsed }: HeaderProps) {
  const location = useLocation();
  const pageLabel = getPageLabel(location.pathname);

  return (
    <header
      className={cn(
        "fixed right-0 top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-sm transition-all duration-200",
        sidebarCollapsed ? "left-16" : "left-60",
      )}
    >
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-400">YOLOv13 後台</span>
        <span className="text-slate-300">/</span>
        <span className="font-medium text-slate-700">{pageLabel}</span>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-slate-100">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-[10px]">{getUserInitials(user)}</AvatarFallback>
              </Avatar>
              <span className="hidden font-medium text-slate-700 sm:block">
                {user?.display_name ?? user?.username ?? "未登入"}
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>
              <p className="font-medium">{user?.display_name ?? user?.username}</p>
              <p className="text-xs font-normal text-muted-foreground">{user?.roles[0] ?? ""}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer">
              <User className="mr-2 h-4 w-4" />
              個人資料
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer text-rose-600 focus:bg-rose-50 focus:text-rose-700"
              onClick={onLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              登出
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
