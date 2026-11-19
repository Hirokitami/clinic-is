"use client";

import { useState } from "react";
import { Alert, Button, Field, Input, LinkButton } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { dmy } from "@/lib/format";
import type { Patient } from "@/lib/types";

/** Поиск пациента: по ИИН (Т1, И2, И3) или по ФИО и дате рождения (А1). */
export function PatientFinder({
  onPick,
  pickLabel = "Выбрать",
  returnTo,
}: {
  onPick: (p: Patient) => void;
  pickLabel?: string;
  returnTo?: string;
}) {
  const [mode, setMode] = useState<"iin" | "fio">("iin");
  const [iin, setIin] = useState("");
  const [fio, setFio] = useState("");
  const [birth, setBirth] = useState("");
  const [found, setFound] = useState<Patient[] | null>(null);
  const [error, setError] = useState<{ text: string; notFound?: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFound(null);
    if (mode === "iin" && !/^\d{12}$/.test(iin.trim())) {
      setError({ text: "ИИН должен содержать 12 цифр" });
      return;
    }
    setBusy(true);
    try {
      const q = mode === "iin" ? { iin: iin.trim() } : { fio, birth_date: birth };
      setFound(await api.get<Patient[]>("/patients/search", q));
    } catch (err) {
      const e2 = err as ApiError;
      setError({ text: e2.message, notFound: e2.code === "PATIENT_NOT_FOUND" });
    } finally {
      setBusy(false);
    }
  }

  const regHref =
    `/registry/patients/new?iin=${encodeURIComponent(mode === "iin" ? iin.trim() : "")}` +
    (returnTo ? `&return=${encodeURIComponent(returnTo)}` : "");

  return (
    <div className="space-y-3">
      <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
        {(
          [
            ["iin", "По ИИН"],
            ["fio", "По ФИО и дате рождения"],
          ] as const
        ).map(([m, label]) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              setError(null);
              setFound(null);
            }}
            className={`rounded-md px-3 py-1 ${mode === m ? "bg-white font-medium shadow-sm" : "text-slate-600"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <form onSubmit={search} className="flex flex-wrap items-end gap-3">
        {mode === "iin" ? (
          <Field label="ИИН пациента" className="w-56">
            <Input
              value={iin}
              inputMode="numeric"
              maxLength={12}
              placeholder="12 цифр"
              onChange={(e) => setIin(e.target.value.replace(/\D/g, ""))}
              invalid={!!error && !error.notFound}
            />
          </Field>
        ) : (
          <>
            <Field label="ФИО" className="w-64">
              <Input value={fio} onChange={(e) => setFio(e.target.value)} placeholder="Фамилия Имя" />
            </Field>
            <Field label="Дата рождения" className="w-44">
              <Input type="date" value={birth} onChange={(e) => setBirth(e.target.value)} />
            </Field>
          </>
        )}
        <Button type="submit" disabled={busy}>
          Найти
        </Button>
      </form>

      {error && (
        <Alert kind={error.notFound ? "warn" : "error"}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error.text}</span>
            {error.notFound && (
              <LinkButton href={regHref} size="sm" variant="primary">
                Зарегистрировать пациента
              </LinkButton>
            )}
          </div>
        </Alert>
      )}

      {found && (
        <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
          {found.map((p) => (
            <li key={p.iin} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="text-sm">
                <div className="font-medium text-slate-900">{p.fio}</div>
                <div className="text-slate-600">
                  ИИН {p.iin} · {dmy(p.birth_date)} · {p.mobile_phone}
                </div>
              </div>
              <Button size="sm" onClick={() => onPick(p)}>
                {pickLabel}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
