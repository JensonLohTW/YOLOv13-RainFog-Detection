import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { AuditPage } from "@/pages/audit-page";
import { DetectionDetailPage } from "@/pages/detection-detail-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { DetectionPage } from "@/pages/detection-page";
import { LoginPage } from "@/pages/login-page";
import { SystemPage } from "@/pages/system-page";
import { useAuthStore } from "@/stores/auth-store";

function AuthLayout() {
  const token = useAuthStore((s) => s.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <AppShell />;
}

function RootLayout() {
  return <Outlet />;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        path: "login",
        element: <LoginPage />,
      },
      {
        path: "",
        element: <AuthLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: "dashboard", element: <DashboardPage /> },
          { path: "detection", element: <DetectionPage /> },
          { path: "detection/:taskNo", element: <DetectionDetailPage /> },
          { path: "system", element: <SystemPage /> },
          { path: "audit", element: <AuditPage /> },
        ],
      },
    ],
  },
]);
