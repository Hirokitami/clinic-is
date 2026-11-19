import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import PatientCardView from "./PatientCardView";

export const metadata = { title: "Карта пациента" };

export default function Page() {
  return (
    <RoleGate roles={["OPERATOR"]}>
      <Suspense fallback={<Spinner />}>
        <PatientCardView />
      </Suspense>
    </RoleGate>
  );
}
