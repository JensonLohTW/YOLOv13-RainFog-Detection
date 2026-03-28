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
    <div className="flex min-h-screen items-center justify-center bg-haze px-4">
      <div className="w-full max-w-md rounded-3xl border border-white/60 bg-white/85 p-8 shadow-soft backdrop-blur">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-700">RainFog Detection</p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-900">後台登入</h1>
        <p className="mt-3 text-sm text-slate-600">
          使用管理員帳號登入 YOLOv13 雨霧識別後台系統。
        </p>
        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <input
            className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none ring-0 transition focus:border-sky-400"
            placeholder="帳號"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loginMutation.isPending}
          />
          <input
            className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none ring-0 transition focus:border-sky-400"
            placeholder="密碼"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loginMutation.isPending}
          />
          {loginMutation.error instanceof Error ? (
            <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {loginMutation.error.message}
            </p>
          ) : null}
          <Button className="w-full" type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "登入中..." : "登入系統"}
          </Button>
        </form>
      </div>
    </div>
  );
}
