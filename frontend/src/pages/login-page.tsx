import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { apiPost } from "@/services/api";
import { type AuthUser, useAuthStore } from "@/stores/auth-store";

type LoginResponse = {
  token: string;
  user: AuthUser;
};

export function LoginPage() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);
  const setAuth = useAuthStore((s) => s.setAuth);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (token) {
      navigate("/dashboard", { replace: true });
    }
  }, [token, navigate]);

  const loginMutation = useMutation({
    mutationFn: () =>
      apiPost<LoginResponse, { username: string; password: string }>("/auth/login", {
        username,
        password,
      }),
    onSuccess: (data) => {
      setAuth(data.token, data.user);
      navigate("/dashboard", { replace: true });
    },
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    loginMutation.mutate();
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="hidden w-96 shrink-0 flex-col justify-between bg-[hsl(var(--sidebar-bg))] p-10 lg:flex">
        <div>
          <p className="text-[10px] uppercase tracking-[0.3em] text-sky-400">RainFog Detection</p>
          <h1 className="mt-4 text-3xl font-bold text-white leading-snug">
            YOLOv13<br />後台管理系統
          </h1>
          <p className="mt-4 text-sm text-slate-400 leading-relaxed">
            雨霧天氣下的智能目標識別與分析平台，支援預處理、模型訓練與任務管理。
          </p>
        </div>
        <p className="text-xs text-slate-600">© 2025 YOLOv13 RainFog System · v0.1.0</p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 items-center justify-center bg-slate-50 px-6">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-sky-600">Administrator Login</p>
            <h2 className="mt-3 text-2xl font-semibold text-slate-900">登入系統</h2>
            <p className="mt-2 text-sm text-slate-500">請輸入您的管理員帳號與密碼。</p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">帳號</label>
              <input
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100 disabled:opacity-60"
                placeholder="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loginMutation.isPending}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">密碼</label>
              <input
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100 disabled:opacity-60"
                placeholder="••••••••"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loginMutation.isPending}
              />
            </div>
            {loginMutation.error instanceof Error ? (
              <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {loginMutation.error.message}
              </p>
            ) : null}
            <Button className="mt-2 w-full" type="submit" disabled={loginMutation.isPending}>
              {loginMutation.isPending ? "驗證中…" : "登入"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
