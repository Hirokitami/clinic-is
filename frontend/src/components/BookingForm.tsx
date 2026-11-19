"use client";

import Link from "next/link";
import { useState } from "react";
import { SlotPicker, type Picked } from "@/components/SlotPicker";
import { Alert, Button, Card, Dialog, Dl, Field, LinkButton, Textarea } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { dmy, ruDate } from "@/lib/format";
import type { AppointmentResult, Patient } from "@/lib/types";

type Existing = { appt_no: string; date: string; time_start: string; doctor: string };

/**
 * Регистрация записи на приём – алгоритм СРО 11 (блоки 1–12) на стороне формы:
 * И5 – пустая причина, И6 – интервал заняли, А4 – уже есть запись к врачу (вопрос «Создать новую?»),
 * И7 – нет связи (данные остаются в форме), блок 12 – «Пациент записан» + талон и SMS.
 */
export function BookingForm({
  patient,
  mode,
  rescheduleBase,
}: {
  patient: Patient | null;
  mode: "operator" | "patient";
  rescheduleBase: string;
}) {
  const [picked, setPicked] = useState<Picked | null>(null);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [existing, setExisting] = useState<Existing | null>(null);
  const [result, setResult] = useState<AppointmentResult | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [blocked, setBlocked] = useState<Existing | null>(null);

  async function submit(confirm?: boolean) {
    setError("");
    setReasonError("");
    setBlocked(null);
    if (!picked) {
      setError("Выберите свободный интервал в расписании врача");
      return;
    }
    if (!reason.trim()) {
      setReasonError("Укажите причину обращения");
      return;
    }
    setBusy(true);
    try {
      const r = await api.post<AppointmentResult>("/appointments", {
        iin: patient?.iin,
        slot_id: picked.slot.slot_id,
        reason,
        confirm_existing: confirm,
      });
      setResult(r);
      setExisting(null);
      setRefresh((x) => x + 1);
    } catch (e) {
      const err = e as ApiError;
      const ex = err.detail.existing as Existing | undefined;
      if (err.code === "EXISTING_APPOINTMENT" && ex) {
        setExisting(ex);
      } else if (err.code === "TRANSFER_REQUIRED" && ex) {
        setExisting(null);
        setBlocked(ex);
      } else {
        setExisting(null);
        if (err.fields.reason) setReasonError(err.fields.reason);
        else setError(err.message);
        if (err.code === "SLOT_BUSY") {
          setPicked(null);
          setRefresh((x) => x + 1);
        }
      }
    } finally {
      setBusy(false);
    }
  }

  function again() {
    setResult(null);
    setPicked(null);
    setReason("");
  }

  if (result) {
    const a = result.appointment;
    return (
      <Card title={<span className="text-emerald-800">✓ {result.message}</span>}>
        <div className="grid gap-6 md:grid-cols-2">
          <Dl
            items={[
              ["Номер записи", a.appt_no],
              ["Пациент", a.patient_fio],
              ["Врач", `${a.doctor.fio} (${a.doctor.specialty_name})`],
              ["Дата и время", `${ruDate(a.date, true)}, ${a.time_start}–${a.time_end}`],
              ["Кабинет", `${a.cabinet_no}, ${a.floor_no} этаж`],
              ["Статус", a.status_name],
            ]}
          />
          {result.sms && (
            <div className="rounded-lg bg-slate-50 p-4 text-sm">
              <div className="mb-1 font-medium text-slate-700">SMS на номер {result.sms.phone}</div>
              <p className="text-slate-800">{result.sms.text}</p>
              <p className="mt-2 text-xs text-slate-500">Статус: {result.sms.status}</p>
            </div>
          )}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <LinkButton href={`/ticket/${a.appt_no}`} variant="primary">
            Печать талона
          </LinkButton>
          <Button variant="secondary" onClick={again}>
            {mode === "operator" ? "Новая запись этого пациента" : "Записаться ещё"}
          </Button>
          {mode === "patient" && <LinkButton href="/cabinet">Мои записи</LinkButton>}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card title="Врач и дата приёма">
        <SlotPicker selected={picked?.slot ?? null} onSelect={setPicked} refreshKey={refresh} />
      </Card>

      <Card title="Запись">
        {picked ? (
          <div className="mb-4 rounded-lg bg-teal-50 px-4 py-3 text-sm text-teal-900">
            {patient && <div><b>{patient.fio}</b>, ИИН {patient.iin}, {dmy(patient.birth_date)}</div>}
            <div>
              {picked.doctor.fio} ({picked.doctor.specialty_name}) · {ruDate(picked.slot.date, true)},{" "}
              {picked.slot.time_start}–{picked.slot.time_end} · каб. {picked.slot.cabinet_no}
            </div>
          </div>
        ) : (
          <p className="mb-4 text-sm text-slate-500">Выберите свободный интервал в расписании врача.</p>
        )}
        <Field label="Причина обращения" required error={reasonError}>
          <Textarea rows={2} value={reason} invalid={!!reasonError} onChange={(e) => setReason(e.target.value)} />
        </Field>
        {error && <Alert kind="error" className="mt-3">{error}</Alert>}
        {blocked && (
          <Alert kind="warn" className="mt-3">
            Запись не создана, выполните перенос записи.{" "}
            <Link className="font-medium underline" href={`${rescheduleBase}/${blocked.appt_no}`}>
              Перенести запись {blocked.appt_no}
            </Link>
          </Alert>
        )}
        <div className="mt-4">
          <Button onClick={() => submit()} disabled={busy || !picked}>
            {busy ? "Сохранение…" : "Записать"}
          </Button>
        </div>
      </Card>

      <Dialog
        open={!!existing}
        title="Уже есть запись к этому врачу"
        onClose={() => setExisting(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => submit(false)} disabled={busy}>
              Нет, перенести существующую
            </Button>
            <Button onClick={() => submit(true)} disabled={busy}>
              Да, создать новую
            </Button>
          </>
        }
      >
        {existing && (
          <p>
            {mode === "operator" ? "У пациента" : "У вас"} уже есть запись {existing.appt_no} к врачу {existing.doctor} на{" "}
            <b>
              {ruDate(existing.date, true)} в {existing.time_start}
            </b>
            . Создать ещё одну запись (нужен повторный приём)?
          </p>
        )}
      </Dialog>
    </div>
  );
}
