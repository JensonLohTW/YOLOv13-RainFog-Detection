import { cn } from "@/lib/utils";

type FooterProps = {
  sidebarCollapsed: boolean;
};

export function Footer({ sidebarCollapsed }: FooterProps) {
  return (
    <footer
      className={cn(
        "fixed bottom-0 right-0 z-30 flex h-10 items-center justify-between border-t border-slate-200 bg-white px-4 transition-all duration-200",
        sidebarCollapsed ? "left-16" : "left-60",
      )}
    >
      <span className="text-xs text-slate-400">
        © 2025 YOLOv13 RainFog Detection System
      </span>
      <span className="text-xs text-slate-400">v0.1.0</span>
    </footer>
  );
}
