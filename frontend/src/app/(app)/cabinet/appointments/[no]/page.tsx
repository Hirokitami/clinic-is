import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import MyApptView from "./MyApptView";

export const metadata = { title: "Моя запись" };

export default function Page() {
  return (
    <RoleGate roles={["PATIENT"]}>
      <Suspense fallback={<Spinner />}>
        <MyApptView />
      </Suspense>
    </RoleGate>
  );
}
