import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import VisitView from "./VisitView";

export const metadata = { title: "Приём пациента" };

export default function Page() {
  return (
    <RoleGate roles={["DOCTOR"]}>
      <Suspense fallback={<Spinner />}>
        <VisitView />
      </Suspense>
    </RoleGate>
  );
}
