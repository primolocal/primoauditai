import React from "react";
import { AuditProvider } from "@/components/workspace/AuditContext";
import { AuditWorkbench } from "@/components/workspace/AuditWorkbench";

export default function PrimoAuditAIWorkstation() {
  return (
    <AuditProvider>
      <AuditWorkbench />
    </AuditProvider>
  );
}
