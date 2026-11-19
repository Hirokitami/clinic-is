"use client";

import { useParams, useSearchParams } from "next/navigation";
import { HistoryView } from "@/components/HistoryView";
import { Alert, LinkButton, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { age, dmy } from "@/lib/format";
import type { PatientHistory } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Окно 3 «История пациента» (СРО 13, С8, Т9). */
export default function HistoryPageView() {
  const { iin } = useParams<{ iin: string }>();
  const appt = useSearchParams().get("appt");
  const { data: h, loading, error } = useLoad(() => api.get<PatientHistory>(`/doctor/patients/${iin}/history`), [iin]);

  if (loading) return <Spinner />;
  if (error || !h) return <Alert kind="error">{error?.message ?? "Нет данных"}</Alert>;
  const p = h.patient;

  return (
    <>
      <PageHeader
        title={p.fio}
        subtitle={`${dmy(p.birth_date)} (${age(p.birth_date)} лет) · ИИН ${p.iin} · ${p.mobile_phone}`}
        actions={
          <>
            <LinkButton href="/doctor">К списку пациентов</LinkButton>
            {appt && (
              <LinkButton href={`/doctor/visit/${appt}`} variant="primary">
                Перейти к приёму
              </LinkButton>
            )}
          </>
        }
      />
      <HistoryView h={h} />
    </>
  );
}
