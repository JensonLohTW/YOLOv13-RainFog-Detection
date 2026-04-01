import * as React from "react";
import {
  BarChart3,
  Boxes,
  BrainCircuit,
  ChevronLeft,
  ScanSearch,
  ScrollText,
  Settings,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type NavItem = {
  to: string;
  label: string;
  icon: React.ElementType;
  group?: string;
};

export const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "儀表盤", icon: BarChart3, group: "主要" },
  { to: "/detection", label: "識別任務", icon: Boxes, group: "主要" },
  { to: "/preprocess-detection", label: "預處理識別", icon: ScanSearch, group: "主要" },
  { to: "/training", label: "模型訓練", icon: BrainCircuit, group: "分析" },
  { to: "/system", label: "系統配置", icon: Settings, group: "設定" },
  { to: "/audit", label: "操作審計", icon: ScrollText, group: "設定" },
];

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
};

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const groups = Array.from(new Set(NAV_ITEMS.map((i) => i.group)));

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col bg-[hsl(var(--sidebar-bg))] transition-all duration-200",
        collapsed ? "w-16" : "w-60",
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-14 shrink-0 items-center border-b border-[hsl(var(--sidebar-border))]",
          collapsed ? "justify-center px-2" : "justify-between px-5",
        )}
      >
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-[10px] uppercase tracking-[0.3em] text-sky-400">RainFog Admin</p>
            <p className="truncate text-sm font-semibold text-white">YOLOv13 系統</p>
          </div>
        )}
        <button
          onClick={onToggle}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-[hsl(var(--sidebar-hover-bg))] hover:text-white"
          aria-label={collapsed ? "展開側邊欄" : "收合側邊欄"}
        >
          <ChevronLeft
            className={cn("h-4 w-4 transition-transform duration-200", collapsed && "rotate-180")}
          />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        {groups.map((group) => {
          const items = NAV_ITEMS.filter((i) => i.group === group);
          return (
            <div key={group} className="mb-4">
              {!collapsed && (
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  {group}
                </p>
              )}
              <div className="space-y-0.5">
                {items.map((item) => (
                  <NavItem key={item.to} item={item} collapsed={collapsed} />
                ))}
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}

function NavItem({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const Icon = item.icon;

  const link = (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          collapsed ? "justify-center" : "",
          isActive
            ? "bg-[hsl(var(--sidebar-active-bg))] text-white"
            : "text-[hsl(var(--sidebar-fg))] hover:bg-[hsl(var(--sidebar-hover-bg))] hover:text-white",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right">{item.label}</TooltipContent>
      </Tooltip>
    );
  }

  return link;
}
