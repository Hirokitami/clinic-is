"use client";

import { RoleGate } from "@/components/AppShell";
import { Alert, Badge, Card, Empty, PageHeader, Spinner, Table, Td } from "@/components/ui";
import { api } from "@/lib/api";
import { dmy } from "@/lib/format";
import type { Sms } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

export default function SmsPage() {
  const { data, loading, error } = useLoad(() => api.get<Sms[]>("/sms"), []);
  return (
    <RoleGate roles={["OPERATOR", "ADMIN"]}>
      <PageHeader
        title="Журнал SMS-подтверждений"
        subtitle="SMS-шлюз не подключён: сообщения формируются и сохраняются со статусом «имитация отправки» (Т8)"
      />
      <Card>
        {loading ? (
          <Spinner />
        ) : error ? (
          <Alert kind="error">{error.message}</Alert>
        ) : !data?.length ? (
          <Empty>Сообщений нет</Empty>
        ) : (
          <Table head={["Время", "Запись", "Телефон", "Текст", "Статус"]}>
            {data.map((m) => (
              <tr key={m.id}>
                <Td className="whitespace-nowrap">{dmy(m.created_at)}</Td>
                <Td className="whitespace-nowrap">{m.appt_no}</Td>
                <Td className="whitespace-nowrap">{m.phone}</Td>
                <Td>{m.text}</Td>
                <Td>
                  <Badge className={m.status === "не доставлено" ? "bg-red-100 text-red-800" : undefined}>{m.status}</Badge>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </RoleGate>
  );
}
