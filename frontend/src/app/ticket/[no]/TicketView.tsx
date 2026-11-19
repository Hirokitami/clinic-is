"use client";

import { useParams } from "next/navigation";
import { Alert, Button, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { dmy, ruDate } from "@/lib/format";
import type { Appointment } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Талон на приём (А5): ФИО врача, дата, время, кабинет. */
export default function TicketView() {
  const { no } = useParams<{ no: string }>();
  const { data: a, loading, error } = useLoad(() => api.get<Appointment>(`/appointments/${no}`), [no]);

  if (loading) return <Spinner />;
  if (error || !a) return <Alert kind="error" className="m-8">{error?.message ?? "Запись не найдена"}</Alert>;

  return (
    <main className="mx-auto max-w-md p-6">
      <div className="no-print mb-4 flex gap-2">
        <Button onClick={() => window.print()}>Печать</Button>
        <Button variant="secondary" onClick={() => history.back()}>
          Назад
        </Button>
      </div>
      <article className="rounded-xl border-2 border-dashed border-slate-400 bg-white p-6">
        <header className="border-b border-slate-200 pb-3 text-center">
          <div className="text-xs uppercase tracking-widest text-slate-500">Медицинская клиника</div>
          <h1 className="mt-1 text-xl font-bold">ТАЛОН НА ПРИЁМ</h1>
          <div className="font-mono text-sm text-slate-600">№ {a.appt_no}</div>
        </header>
        <dl className="mt-4 space-y-3 text-sm">
          <Row k="Пациент" v={a.patient_fio} />
          <Row k="Врач" v={`${a.doctor.fio}`} sub={a.doctor.specialty_name} />
          <Row k="Дата" v={ruDate(a.date, true)} big />
          <Row k="Время" v={`${a.time_start} – ${a.time_end}`} big />
          <Row k="Кабинет" v={`${a.cabinet_no}`} sub={`${a.floor_no} этаж`} big />
          <Row k="Статус" v={a.status_name} />
        </dl>
        <footer className="mt-5 border-t border-slate-200 pt-3 text-xs text-slate-500">
          Оформлено {dmy(a.created_at)}. Пожалуйста, приходите за 10 минут до начала приёма. Для переноса или отмены
          обратитесь в регистратуру или в личный кабинет.
        </footer>
      </article>
    </main>
  );
}

function Row({ k, v, sub, big }: { k: string; v: string; sub?: string; big?: boolean }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{k}</dt>
      <dd className="text-right">
        <div className={big ? "text-lg font-semibold" : "font-medium"}>{v}</div>
        {sub && <div className="text-xs text-slate-500">{sub}</div>}
      </dd>
    </div>
  );
}
