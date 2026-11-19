"use client";

import { useParams } from "next/navigation";
import { AppointmentManage } from "@/components/AppointmentManage";

export default function ApptView() {
  const { no } = useParams<{ no: string }>();
  return <AppointmentManage apptNo={no} backHref="/registry/appointments" backLabel="К списку записей" />;
}
