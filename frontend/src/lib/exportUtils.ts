import { AuditRun, Finding } from "@/types/claim";

/** Generate a full markdown export string for the audit summary */
export function generateMarkdownExport(auditRun: AuditRun): string {
  let t = `# PrimoAuditAI Audit Summary\n\n`;

  t += `## Claim Information\n`;
  t += `- Claim Number: ${auditRun.claim_package.claim_number}\n`;
  t += `- Carrier: ${auditRun.claim_package.carrier}\n`;
  t += `- Vehicle: ${auditRun.vehicle_profile?.year} ${auditRun.vehicle_profile?.make} ${auditRun.vehicle_profile?.model}\n\n`;

  t += `## Audit Status\n`;
  t += `- Lifecycle Status: ${auditRun.status.toUpperCase().replace('_', ' ')}\n`;
  t += `- Overall Score: ${auditRun.scorecard.overall_score}\n`;
  if (auditRun.active_supplement !== "E01") {
    t += `- Scope: ${auditRun.active_supplement} Supplement Only\n`;
  }
  t += `\n`;

  t += `## Blockers / Readiness\n`;
  if (auditRun.blockers && auditRun.blockers.length > 0) {
    auditRun.blockers.forEach(b => t += `- ⚠️ ${b}\n`);
  } else {
    t += `- Clean. No readiness blockers.\n`;
  }
  t += `\n`;

  t += `## Narrative Summary\n`;
  t += `${auditRun.narrative?.damage_summary || 'No damage summary.'}\n`;
  t += `${auditRun.narrative?.claim_summary || 'No claim summary.'}\n\n`;

  t += `## Reviewer Notes\n`;
  t += `${auditRun.narrative?.reviewer_notes || 'No manual notes appended.'}\n\n`;

  const open = auditRun.findings.filter(f => f.status === 'open' || f.status === 'needs_review');
  const confirmed = auditRun.findings.filter(f => f.status === 'confirmed');
  const overturned = auditRun.findings.filter(f => f.status === 'overturned');

  t += `## Findings\n\n`;

  t += `### Confirmed [${confirmed.length}]\n`;
  if (confirmed.length === 0) t += `- None\n`;
  confirmed.forEach(f => {
    t += `- [${f.rule_id}] $${f.financial_impact} | ${f.message}\n`;
  });
  t += `\n`;

  t += `### Overturned [${overturned.length}]\n`;
  if (overturned.length === 0) t += `- None\n`;
  overturned.forEach(f => {
    t += `- [${f.rule_id}] $${f.financial_impact} | ${f.message}\n`;
  });
  t += `\n`;

  t += `### Open / Needs Follow-Up [${open.length}]\n`;
  if (open.length === 0) t += `- None\n`;
  open.forEach(f => {
    t += `- [${f.rule_id}] $${f.financial_impact} | ${f.message}\n`;
  });

  return t;
}
