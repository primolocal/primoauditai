import { Finding, NormalizedDocument, PhotoEvidence, EvidenceRef } from "@/types/claim";
import { AuditorVerdict } from "@/components/workspace/InspectorRail/SupportVerdictBar";

export type SupportQuality = 'STRONG' | 'WEAK' | 'INVALID' | 'UNSCORED';

export type SupportType = "photo" | "document";

export type SupportExpectation = {
  primary: SupportType[];
  secondary: SupportType[];
};

export const SUPPORT_TYPE_MAP: Record<string, SupportExpectation> = {
  // Physical damage / condition
  exterior_damage: { primary: ["photo"], secondary: ["document"] },
  panel_damage: { primary: ["photo"], secondary: ["document"] },
  collision_damage: { primary: ["photo"], secondary: ["document"] },
  structural_damage: { primary: ["photo"], secondary: ["document"] },
  hail_damage: { primary: ["photo"], secondary: ["document"] },
  mechanical_damage_visible: { primary: ["photo"], secondary: ["document"] },
  paint_damage: { primary: ["photo"], secondary: ["document"] },
  glass_damage: { primary: ["photo"], secondary: ["document"] },
  undercarriage_damage: { primary: ["photo"], secondary: ["document"] },
  frame_damage: { primary: ["photo"], secondary: ["document"] },

  // Documentation / estimate / financial
  estimate_accuracy: { primary: ["document"], secondary: ["photo"] },
  invoice: { primary: ["document"], secondary: ["photo"] },
  teardown: { primary: ["document"], secondary: ["photo"] },
  supplement: { primary: ["document"], secondary: ["photo"] },
  repair_procedure: { primary: ["document"], secondary: ["photo"] },
  labor_operations: { primary: ["document"], secondary: ["photo"] },
  parts_pricing: { primary: ["document"], secondary: ["photo"] },
  pdr_invoice: { primary: ["document"], secondary: ["photo"] },
  sublet: { primary: ["document"], secondary: ["photo"] },
  other_charges: { primary: ["document"], secondary: ["photo"] },
  valuation: { primary: ["document"], secondary: ["photo"] },
  acv: { primary: ["document"], secondary: ["photo"] },
  total_loss_documentation: { primary: ["document"], secondary: ["photo"] },

  // Validation / compliance / admin
  vin_verification: { primary: ["photo", "document"], secondary: [] },
  production_date: { primary: ["photo", "document"], secondary: [] },
  mileage: { primary: ["photo", "document"], secondary: [] },
  ownership: { primary: ["photo", "document"], secondary: [] },
  vehicle_identification: { primary: ["photo", "document"], secondary: [] },
  loss_details: { primary: ["photo", "document"], secondary: [] },
  coverage_verification: { primary: ["photo", "document"], secondary: [] },

  // Photo completeness
  missing_photos: { primary: ["photo"], secondary: [] },
  insufficient_photos: { primary: ["photo"], secondary: [] },
  angle_missing: { primary: ["photo"], secondary: [] },
  required_photo_missing: { primary: ["photo"], secondary: [] },
  photo_quality_issue: { primary: ["photo"], secondary: [] },

  // Process / workflow / timing
  late_supplement: { primary: ["document"], secondary: [] },
  timeline_issue: { primary: ["document"], secondary: [] },
  inspection_delay: { primary: ["document"], secondary: [] },
  reinspection_required: { primary: ["document"], secondary: [] },
  process_violation: { primary: ["document"], secondary: [] },
};

export function getExpectedSupportTypes(category?: string): SupportExpectation {
  if (!category) {
    return { primary: ["photo", "document"], secondary: [] };
  }

  return SUPPORT_TYPE_MAP[category] ?? {
    primary: ["photo", "document"],
    secondary: []
  };
}

export function getSupportQuality(
    asset: NormalizedDocument | PhotoEvidence, 
    finding: Finding | null,
    refs: EvidenceRef[]
): SupportQuality {
    if (!finding) return 'UNSCORED';
    
    const isPhoto = 'type' in asset;
    const isDoc = !isPhoto;
    const assetType: SupportType = isPhoto ? 'photo' : 'document';
    
    const linkedRef = refs.find(r => r.source_id === asset.id);
    const category = finding.category || '';
    const hasMappedCategory = !!SUPPORT_TYPE_MAP[category];
    const expectations = getExpectedSupportTypes(category);
    
    const isPrimary = expectations.primary.includes(assetType);
    const isSecondary = expectations.secondary.includes(assetType);
    
    // Immediate overrides
    if (asset.processing_status === 'failed') return 'INVALID';
    if (asset.is_mock || asset.source_kind === 'generated_fixture') return 'INVALID';
    
    // Type mismatch is heavily penalized (neither primary nor secondary)
    if (linkedRef && !isPrimary && !isSecondary) return 'INVALID';
    
    // Unlinked Assets
    if (!linkedRef) {
        if (!isPrimary && !isSecondary) return 'INVALID';
        
        // Claim-level relevant asset, but not explicitly linked. 
        if ((asset.confidence || 0) >= 0.8) return 'WEAK'; 
        return 'INVALID';
    }
    
    // Linked Assets logic (Has type match to some degree)
    
    if (!isPrimary && isSecondary) {
        // User explicitly dictates: "damage finding + document-only asset = Invalid"
        if (assetType === 'document' && expectations.primary.includes('photo') && !expectations.primary.includes('document')) {
            return 'INVALID';
        }
        // "Documentation finding + photo-only asset = Weak at best"
        return 'WEAK';
    }
    
    // Primary matches
    if (isPrimary) {
        // Evaluate Unmapped Categories (Weak at best, unless unusually strong)
        if (!hasMappedCategory) {
            // Unmapped is Weak unless explicit + very high confidence
            return 'WEAK';
        }

        // Mapped Primary Matches
        const conf = asset.confidence || 0;
        if (conf >= 0.8) return 'STRONG';
        if (conf >= 0.45) return 'WEAK';
        if (conf < 0.45 && conf > 0) return 'WEAK';
        
        if (linkedRef.support_status === 'full') return 'STRONG';
        return 'WEAK';
    }
    
    return 'INVALID';
}

export function buildLinkReasoning(
    asset: NormalizedDocument | PhotoEvidence, 
    finding: Finding | null,
    refs: EvidenceRef[]
): string[] {
    const reasons: string[] = [];
    if (!finding) {
        reasons.push("No finding selected. Viewing asset in claim-level evidence mode.");
        return reasons;
    }
    
    const isPhoto = 'type' in asset;
    const assetType: SupportType = isPhoto ? 'photo' : 'document';
    
    const category = finding.category || '';
    const hasMappedCategory = !!SUPPORT_TYPE_MAP[category];
    const expectations = getExpectedSupportTypes(category);
    
    const isPrimary = expectations.primary.includes(assetType);
    const isSecondary = expectations.secondary.includes(assetType);
    
    const linkedRef = refs.find(r => r.source_id === asset.id);
    const confidence = asset.confidence || 0;
    
    // Provenance
    if (asset.is_mock || asset.source_kind === 'generated_fixture') {
        reasons.push("Asset is marked as mock/fixture and should not be treated as production support.");
    }
    if (asset.processing_status === 'failed') {
        reasons.push("Asset is not in a usable processing state.");
    }
    
    // Type Checking logic
    if (linkedRef) {
        reasons.push(`Explicitly linked by backend finding map (${linkedRef.support_status} support).`);
        
        if (!hasMappedCategory) {
            reasons.push(`Category '${category}' is unmapped. Both evidence types evaluated as generalized fallback.`);
        }
        
        if (isPrimary) {
            reasons.push(`Asset type (${assetType}) is a primary matched format for this finding category.`);
        } else if (isSecondary) {
            // Tighten reasoning language for hard-invalid cases: Damage finding + document-only asset
            if (assetType === 'document' && expectations.primary.includes('photo') && !expectations.primary.includes('document')) {
                reasons.push(`A document cannot satisfy visible damage proof requirements (Primary expects: photo).`);
            } else {
                reasons.push(`Asset type (${assetType}) acts as secondary support for this finding (Primary expects: ${expectations.primary.join('/')}).`);
            }
        } else {
            const exp = [...expectations.primary, ...expectations.secondary].join(' or ');
            reasons.push(`Mismatch: Finding expected ${exp}, but asset is a ${assetType}.`);
        }
    } else {
        reasons.push("Asset is claim-level evidence only and not explicitly mapped to this finding.");
        if ((isPrimary || isSecondary) && confidence > 0.5) {
            reasons.push("Asset appears potentially relevant to finding category based on global scan.");
        }
    }
    
    // CV Labels & Thresholds
    if (confidence > 0) {
        const lbl = isPhoto ? (asset as PhotoEvidence).damage_area || asset.type : (asset as NormalizedDocument).doc_type;
        reasons.push(`CV detected '${lbl}' cluster with ${(confidence * 100).toFixed(0)}% confidence.`);
        
        if (linkedRef && confidence < 0.8 && confidence >= 0.45) {
            reasons.push("Linked context is moderate because CV confidence is below preferred validation threshold (0.80).");
        } else if (linkedRef && confidence < 0.45) {
            reasons.push("Linked context is weak because CV confidence is extremely low.");
        }
    } else if (linkedRef) {
        reasons.push("No deterministic CV classification available.");
    }
    
    return reasons;
}

export type FindingEvidenceHealth = 
    | 'Strong Support' 
    | 'Weak Support' 
    | 'Invalid Support' 
    | 'Missing Required Evidence' 
    | 'Reviewer Overrode System' 
    | 'Pending Review';

export interface FindingHealthScore {
    status: FindingEvidenceHealth;
    explanation: string;
    isUnresolvedOverride: boolean;
}

export type ClaimReadiness = 'Not Ready' | 'Risky' | 'Ready';

export function getClaimReadiness(scores: FindingHealthScore[]): ClaimReadiness {
    // 1. Not Ready if ANY finding has Missing, Invalid, or Unresolved Override
    if (scores.some(s => 
        s.status === 'Missing Required Evidence' || 
        s.status === 'Invalid Support' || 
        s.isUnresolvedOverride
    )) {
        return 'Not Ready';
    }

    // 2. Risky if ANY finding is Weak or has a documented override
    if (scores.some(s => 
        s.status === 'Weak Support' || 
        (s.status === 'Reviewer Overrode System' && !s.isUnresolvedOverride)
    )) {
        return 'Risky';
    }

    // 3. Ready
    return 'Ready';
}

export interface PhotoConfirmationState {
    evidence_exists?: 'yes'|'no'|'unknown'|null;
    evidence_uploaded?: 'yes'|'no'|null;
    linked_asset_ids?: string[];
    missing_upload_reason?: string|null;
}

export function getFindingEvidenceHealth(
    finding: Finding,
    allAssets: (NormalizedDocument | PhotoEvidence)[],
    auditorVerdicts: Record<string, AuditorVerdict>,
    reviewerNotes: Record<string, string>,
    photoConfirmations: Record<string, PhotoConfirmationState> = {}
): FindingHealthScore {
    const expectations = getExpectedSupportTypes(finding.category);
    const confirmation = photoConfirmations[finding.id];
    
    // Explicit Human Override logic for Photo Validation
    if (expectations.primary.includes('photo') && confirmation) {
        if (confirmation.evidence_exists === 'yes' && confirmation.evidence_uploaded === 'no') {
            return {
                status: 'Missing Required Evidence',
                explanation: 'Photos are stated to exist but are not included in the claim package.',
                isUnresolvedOverride: false
            };
        }
        if (confirmation.evidence_exists === 'no') {
            return {
                status: 'Invalid Support',
                explanation: 'No visual evidence exists for this damage.',
                isUnresolvedOverride: false
            };
        }
        if (confirmation.evidence_exists === 'unknown') {
            return {
                status: 'Weak Support',
                explanation: 'Photo evidence has not been confirmed by the auditor.',
                isUnresolvedOverride: false
            };
        }
        if (confirmation.evidence_exists === 'yes' && confirmation.evidence_uploaded === 'yes') {
            const linked = confirmation.linked_asset_ids || [];
            if (linked.length === 0) {
                return {
                    status: 'Missing Required Evidence',
                    explanation: 'Photos are stated to be uploaded but none have been explicitly linked to this finding.',
                    isUnresolvedOverride: false
                };
            }
        }
    }
    
    // Check missing expected primary evidence in entire claim pool
    const hasPrimaryEvidence = allAssets.some(a => {
        const t = 'type' in a ? 'photo' : 'document';
        return expectations.primary.includes(t);
    });

    const isSystemMissingPrimary = expectations.primary.length > 0 && !hasPrimaryEvidence;
    
    let hasOverride = false;
    let allInvalid = true;
    let hasWeak = false;
    let hasStrong = false;
    let hasRelevantContext = false;

    // Merge system refs with explicit human-linked assets
    const systemRefs = finding.evidence_refs || [];
    const linkedIds = (confirmation && confirmation.linked_asset_ids) || [];
    
    // De-duplicate references
    const refsMap = new Map();
    for (const r of systemRefs) {
        refsMap.set(r.source_id, r);
    }
    for (const lid of linkedIds) {
        if (!refsMap.has(lid)) {
            // Mock a reference for explicitly linked items that the AI missed
            refsMap.set(lid, { source_id: lid, support_status: 'full', bounding_boxes: [] });
        }
    }
    const refs = Array.from(refsMap.values());

    for (const ref of refs) {
        hasRelevantContext = true;
        const asset = allAssets.find(a => a.id === ref.source_id);
        if (!asset) continue;

        const quality = getSupportQuality(asset, finding, refs);
        const stateKey = `${finding.id}_${asset.id}`;
        const verdict = auditorVerdicts[stateKey] || null;

        // Treat any system-vs-auditor disagreement as an override
        if (verdict) {
            const isAligned = 
                (quality === 'STRONG' && verdict === 'valid') ||
                (quality === 'WEAK' && verdict === 'weak') ||
                (quality === 'INVALID' && verdict === 'invalid');
            
            if (!isAligned) {
                hasOverride = true;
            }
        }

        // Add explicit tracking for the strict priority logic
        if (quality === 'STRONG' || verdict === 'valid') hasStrong = true;
        if (quality === 'WEAK' || verdict === 'weak') hasWeak = true;
        // Invalid overrides to weak/valid skip allInvalid block
        if (quality !== 'INVALID' && verdict !== 'invalid') allInvalid = false;
        if (verdict === 'valid' || verdict === 'weak') allInvalid = false;
    }

    // Priority 1: Reviewer Overrode System
    if (hasOverride) {
        const note = reviewerNotes[finding.id] || '';
        const unresolved = note.trim().length === 0;
        return {
            status: 'Reviewer Overrode System',
            explanation: unresolved 
                ? 'Auditor modified the system verdict but did not provide a required note.' 
                : 'Auditor modified the system verdict and provided justification.',
            isUnresolvedOverride: unresolved
        };
    }

    // Priority 2: Missing Required Evidence
    if (isSystemMissingPrimary || (refs.length === 0 && expectations.primary.length > 0)) {
        return {
            status: 'Missing Required Evidence',
            explanation: `Required primary evidence (${expectations.primary.join('/')}) is absent or unusable.`,
            isUnresolvedOverride: false
        };
    }

    // Priority 3: Invalid Support
    if (hasRelevantContext && allInvalid) {
        return {
            status: 'Invalid Support',
            explanation: 'All linked assets are invalid or wrong context type.',
            isUnresolvedOverride: false
        };
    }

    // Priority 4: Weak Support
    if (!hasStrong && (hasWeak || (!hasRelevantContext && !isSystemMissingPrimary))) {
        return {
            status: 'Weak Support',
            explanation: 'Evidence exists but support is incomplete, indirect, low-confidence, or secondary.',
            isUnresolvedOverride: false
        };
    }

    // Priority 5: Strong Support
    if (hasStrong) {
        return {
            status: 'Strong Support',
            explanation: 'At least one linked asset provides strong primary support.',
            isUnresolvedOverride: false
        };
    }

    return {
        status: 'Pending Review',
        explanation: 'Finding is awaiting review.',
        isUnresolvedOverride: false
    };
}
