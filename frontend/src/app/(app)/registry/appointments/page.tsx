import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import AppointmentsView from "./AppointmentsView";

export const metadata = { title: "Список записей" };

export default function Page() {
  return (
    <RoleGate roles={["OPERATOR"]}>
      <Suspense fallback={<Spinner />}>
        <AppointmentsView />
      </Suspense>
    </RoleGate>
  );
}
