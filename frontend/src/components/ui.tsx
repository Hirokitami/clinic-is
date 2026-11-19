"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import type { StatusCode } from "@/lib/types";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

// ------------------------------------------------------------------ кнопки
type BtnVariant = "primary" | "secondary" | "danger" | "ghost";
const BTN: Record<BtnVariant, string> = {
  primary: "bg-teal-700 text-white hover:bg-teal-800 disabled:bg-teal-700/50",
  secondary: "bg-white text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50 disabled:text-slate-400",
  danger: "bg-white text-red-700 ring-1 ring-red-300 hover:bg-red-50 disabled:opacity-50",
  ghost: "text-teal-800 hover:bg-teal-50 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: "sm" | "md" }) {
  return (
    <button
      type="button"
      {...props}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:cursor-not-allowed",
        size === "sm" ? "px-2.5 py-1 text-sm" : "px-4 py-2 text-sm",
        BTN[variant],
        className,
      )}
    />
  );
}

export function LinkButton({
  href,
  variant = "secondary",
  size = "md",
  className,
  children,
}: {
  href: string;
  variant?: BtnVariant;
  size?: "sm" | "md";
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors",
        size === "sm" ? "px-2.5 py-1 text-sm" : "px-4 py-2 text-sm",
        BTN[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}

// ------------------------------------------------------------------ поля
export function Field({
  label,
  required,
  error,
  hint,
  children,
  className,
}: {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cx("block", className)}>
      <span className="mb-1 block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="text-red-600"> *</span>}
      </span>
      {children}
      {error ? (
        <span className="mt-1 block text-sm text-red-700">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-slate-500">{hint}</span>
      ) : null}
    </label>
  );
}

const INPUT =
  "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 disabled:bg-slate-100";

export function Input({ invalid, className, ...p }: React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return <input {...p} className={cx(INPUT, invalid && "border-red-500 ring-2 ring-red-500/20", className)} />;
}

export function Select({
  invalid,
  className,
  ...p
}: React.SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }) {
  return <select {...p} className={cx(INPUT, invalid && "border-red-500 ring-2 ring-red-500/20", className)} />;
}

export function Textarea({
  invalid,
  className,
  ...p
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }) {
  return <textarea {...p} className={cx(INPUT, invalid && "border-red-500 ring-2 ring-red-500/20", className)} />;
}

// ------------------------------------------------------------------ блоки
export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

type AlertKind = "ok" | "error" | "warn" | "info";
const ALERT: Record<AlertKind, string> = {
  ok: "border-emerald-200 bg-emerald-50 text-emerald-900",
  error: "border-red-200 bg-red-50 text-red-900",
  warn: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-sky-200 bg-sky-50 text-sky-900",
};

export function Alert({
  kind = "info",
  children,
  className,
}: {
  kind?: AlertKind;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div role={kind === "error" ? "alert" : "status"} className={cx("rounded-lg border px-4 py-3 text-sm", ALERT[kind], className)}>
      {children}
    </div>
  );
}

export type Message = { kind: AlertKind; text: React.ReactNode } | null;

export function Msg({ m, className }: { m: Message; className?: string }) {
  if (!m) return null;
  return (
    <Alert kind={m.kind} className={className}>
      {m.text}
    </Alert>
  );
}

const STATUS_STYLE: Record<StatusCode, string> = {
  PLANNED: "bg-sky-100 text-sky-800",
  DONE: "bg-emerald-100 text-emerald-800",
  CANCELLED: "bg-slate-200 text-slate-700",
  NO_SHOW: "bg-amber-100 text-amber-900",
};

export function StatusBadge({ code, name }: { code: StatusCode; name: string }) {
  return <Badge className={STATUS_STYLE[code]}>{name}</Badge>;
}

export function Badge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", className ?? "bg-slate-100 text-slate-700")}>
      {children}
    </span>
  );
}

export function Spinner({ label = "Загрузка…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-teal-700" />
      {label}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-6 text-center text-sm text-slate-500">{children}</p>;
}

export function Table({ head, children }: { head: React.ReactNode[]; children: React.ReactNode }) {
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            {head.map((h, i) => (
              <th key={i} className="px-5 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}

export function Td({ children, className, colSpan }: { children?: React.ReactNode; className?: string; colSpan?: number }) {
  return (
    <td colSpan={colSpan} className={cx("px-5 py-2.5 align-top", className)}>
      {children}
    </td>
  );
}

export function Dl({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
      {items.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-slate-500">{k}</dt>
          <dd className="text-slate-900">{v || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

// ------------------------------------------------------------------ диалог подтверждения
export function Dialog({
  open,
  title,
  children,
  actions,
  onClose,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  actions: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className="m-auto w-[min(92vw,480px)] rounded-xl p-0 shadow-xl backdrop:bg-slate-900/40"
    >
      <div className="p-5">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <div className="mt-3 text-sm text-slate-700">{children}</div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">{actions}</div>
      </div>
    </dialog>
  );
}

export function Denied({ text = "Раздел недоступен для вашей роли." }: { text?: string }) {
  return (
    <div className="mx-auto max-w-lg py-16 text-center">
      <p className="text-5xl">🔒</p>
      <h1 className="mt-4 text-xl font-semibold text-slate-900">Доступ запрещён</h1>
      <p className="mt-2 text-slate-600">{text}</p>
      <LinkButton href="/" className="mt-6">
        На главную
      </LinkButton>
    </div>
  );
}
