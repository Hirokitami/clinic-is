"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Field, Input } from "@/components/ui";
import { api, errorText } from "@/lib/api";

const DEMO = [
  ["operator.reg1", "oper123", "Оператор регистратуры"],
  ["doctor.akhmetov", "doc123", "Врач-кардиолог"],
  ["doctor.seitkali", "doc123", "Врач-терапевт"],
  ["nurse.omarova", "nurse123", "Медсестра"],
  ["lab.sadykova", "lab123", "Лаборатория"],
  ["admin.clinic", "admin123", "Администратор"],
  ["patient.dana", "pat123", "Пациент"],
];

export default function LoginForm() {
  const params = useSearchParams();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/login", { login, password });
      const next = params.get("next");
      location.href = next && next.startsWith("/") ? next : "/";
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  }

  return (
    <>
      <form onSubmit={submit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {error && <Alert kind="error">{error}</Alert>}
        <Field label="Логин">
          <Input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoFocus required />
        </Field>
        <Field label="Пароль">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </Field>
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? "Вход…" : "Войти"}
        </Button>
      </form>
      <details className="mt-4 rounded-xl border border-slate-200 bg-white/70 p-4 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">Демонстрационные учётные записи</summary>
        <ul className="mt-3 space-y-1">
          {DEMO.map(([l, p, r]) => (
            <li key={l}>
              <button
                type="button"
                className="w-full rounded-md px-2 py-1 text-left hover:bg-teal-50"
                onClick={() => {
                  setLogin(l);
                  setPassword(p);
                }}
              >
                <span className="font-mono text-teal-800">{l}</span> <span className="text-slate-500">· {r}</span>
              </button>
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
