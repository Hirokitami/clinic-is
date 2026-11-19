"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cx, Denied, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";

type NavItem = { href: string; label: string; icon: string; roles: Role[] };

// Разделы по подсистемам ПР 5; показываются только разделы роли пользователя (Т13).
export const NAV: NavItem[] = [
  { href: "/", label: "Главная", icon: "⌂", roles: ["OPERATOR", "DOCTOR", "NURSE", "PATIENT", "LAB", "ADMIN"] },
  { href: "/registry/booking", label: "Запись на приём", icon: "＋", roles: ["OPERATOR"] },
  { href: "/registry/patients", label: "Пациенты", icon: "☰", roles: ["OPERATOR"] },
  { href: "/registry/appointments", label: "Список записей", icon: "▤", roles: ["OPERATOR"] },
  { href: "/doctor", label: "Пациенты на приём", icon: "✚", roles: ["DOCTOR"] },
  { href: "/nurse", label: "Процедуры", icon: "✓", roles: ["NURSE"] },
  { href: "/lab", label: "Направления", icon: "⚗", roles: ["LAB"] },
  { href: "/cabinet", label: "Мои записи и здоровье", icon: "♥", roles: ["PATIENT"] },
  { href: "/cabinet/book", label: "Записаться к врачу", icon: "＋", roles: ["PATIENT"] },
  { href: "/admin/schedule", label: "Расписание врачей", icon: "▦", roles: ["ADMIN"] },
  { href: "/admin/reports", label: "Отчёты", icon: "▮", roles: ["ADMIN"] },
  { href: "/registry/sms", label: "Журнал SMS", icon: "✉", roles: ["OPERATOR", "ADMIN"] },
];

function isActive(path: string, href: string) {
  if (href === "/") return path === "/";
  if (href === "/cabinet") return path === "/cabinet" || path.startsWith("/cabinet/appointments");
  return path === href || path.startsWith(href + "/");
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const path = usePathname();
  const [open, setOpen] = useState(false);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }
  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Переход на страницу входа…" />
      </div>
    );
  }

  const items = NAV.filter((n) => n.roles.includes(user.role_code));

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[256px_1fr]">
      <aside
        className={cx(
          "no-print fixed inset-y-0 left-0 z-30 w-64 border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center gap-2 border-b border-slate-100 px-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700 font-bold text-white">+</span>
          <span className="font-semibold leading-tight text-slate-900">ИС клиники</span>
        </div>
        <nav className="space-y-0.5 p-3">
          {items.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              onClick={() => setOpen(false)}
              className={cx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                isActive(path, n.href) ? "bg-teal-50 text-teal-900" : "text-slate-700 hover:bg-slate-50",
              )}
            >
              <span className="w-5 text-center text-base text-teal-700" aria-hidden>
                {n.icon}
              </span>
              {n.label}
            </Link>
          ))}
        </nav>
      </aside>
      {open && <div className="fixed inset-0 z-20 bg-slate-900/30 lg:hidden" onClick={() => setOpen(false)} />}

      <div className="min-w-0">
        <header className="no-print sticky top-0 z-10 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-8">
          <button className="rounded-lg p-2 text-slate-700 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Меню">
            ☰
          </button>
          <div className="ml-auto flex items-center gap-4">
            <div className="text-right leading-tight">
              <div className="text-sm font-medium text-slate-900">{user.display_name}</div>
              <div className="text-xs text-slate-500">{user.role_name}</div>
            </div>
            <button onClick={logout} className="rounded-lg px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50">
              Выход
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-8">{children}</main>
      </div>
    </div>
  );
}

/** Показывает содержимое только указанным ролям (И1). */
export function RoleGate({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return null;
  if (!roles.includes(user.role_code)) return <Denied />;
  return <>{children}</>;
}
