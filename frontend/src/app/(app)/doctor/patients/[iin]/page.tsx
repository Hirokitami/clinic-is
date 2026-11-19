import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import HistoryPageView from "./HistoryPageView";

export const metadata = { title: "История пациента" };

export default function Page() {
  return (
    <RoleGate roles={["DOCTOR"]}>
      <Suspense fallback={<Spinner />}>
        <HistoryPageView />
      </Suspense>
    </RoleGate>
  );
}
