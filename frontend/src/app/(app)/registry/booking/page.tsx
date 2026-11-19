import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import BookingView from "./BookingView";

export const metadata = { title: "Запись на приём" };

export default function Page() {
  return (
    <RoleGate roles={["OPERATOR"]}>
      <Suspense fallback={<Spinner />}>
        <BookingView />
      </Suspense>
    </RoleGate>
  );
}
