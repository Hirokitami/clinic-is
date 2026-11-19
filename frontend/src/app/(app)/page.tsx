"use client";

import Link from "next/link";
import { NAV } from "@/components/AppShell";
import { Card, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ruDate } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";

type Stats = {
  today: string;
  appointments_today?: number;
  patients?: number;
  free_slots_today?: number;
  done_today?: number;
  active_prescriptions?: number;
  referrals_open?: number;
  next_appointment?: {
    appt_no: string;
    date: string;
    time: string;
    doctor: string;
    specialty: string;
    cabinet_no: string;
  } | null;
};

function Stat({ label, value, href }: { label: string; value: number | string | undefined; href?: string }) {
  const body = (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-300">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">{value ?? "—"}</div>
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export default function Dashboard() {
  const { user } = useAuth();
  const { data } = useLoad(() => api.get<Stats>("/dashboard"), []);
  if (!user) return null;
  const tiles = NAV.filter((n) => n.href !== "/" && n.roles.includes(user.role_code));
  const role = user.role_code;

  return (
    <>
      <PageHeader title={`Здравствуйте, ${user.display_name.split(" (")[0]}`} subtitle={data ? ruDate(data.today, true) : ""} />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(role === "OPERATOR" || role === "ADMIN") && (
          <>
            <Stat label="Записей на сегодня" value={data?.appointments_today} href={role === "OPERATOR" ? "/registry/appointments" : undefined} />
            <Stat label="Свободных интервалов сегодня" value={data?.free_slots_today} />
            <Stat label="Карт пациентов" value={data?.patients} href={role === "OPERATOR" ? "/registry/patients" : undefined} />
          </>
        )}
        {role === "DOCTOR" && (
          <>
            <Stat label="Пациентов на приём сегодня" value={data?.appointments_today} href="/doctor" />
            <Stat label="Проведено приёмов сегодня" value={data?.done_today} href="/doctor" />
          </>
        )}
        {role === "NURSE" && <Stat label="Действующих назначений" value={data?.active_prescriptions} href="/nurse" />}
        {role === "LAB" && <Stat label="Направлений ожидает результата" value={data?.referrals_open} href="/lab" />}
      </div>

      {role === "PATIENT" && (
        <Card title="Ближайший приём" className="mb-6">
          {data?.next_appointment ? (
            <Link href={`/cabinet/appointments/${data.next_appointment.appt_no}`} className="block text-sm">
              <div className="text-lg font-semibold text-slate-900">
                {ruDate(data.next_appointment.date, true)}, {data.next_appointment.time}
              </div>
              <div className="text-slate-700">
                {data.next_appointment.specialty} {data.next_appointment.doctor} · каб. {data.next_appointment.cabinet_no}
              </div>
            </Link>
          ) : (
            <p className="text-sm text-slate-600">
              Запланированных приёмов нет.{" "}
              <Link href="/cabinet/book" className="font-medium text-teal-800 underline">
                Записаться к врачу
              </Link>
            </p>
          )}
        </Card>
      )}

      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">Разделы</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-300 hover:shadow"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-xl text-teal-700">{t.icon}</span>
            <span className="font-medium text-slate-900">{t.label}</span>
          </Link>
        ))}
      </div>
    </>
  );
}
