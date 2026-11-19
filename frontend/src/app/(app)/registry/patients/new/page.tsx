import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import NewPatientView from "./NewPatientView";

export const metadata = { title: "Регистрация пациента" };

export default function Page() {
  return (
    <RoleGate roles={["OPERATOR"]}>
      <Suspense fallback={<Spinner />}>
        <NewPatientView />
      </Suspense>
    </RoleGate>
  );
}
