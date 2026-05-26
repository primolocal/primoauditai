import { ClaimData } from '../types/claim';

export const mockClaims: ClaimData[] = [
  {
    run_id: "aud_a100_24x",
    timestamp: "2026-03-30T10:00:00Z",
    status: "not_started",
    blockers: [],
    activity_log: [],
    claim_package: {
      claim_number: "CLM-A100-24X",
      carrier: "National General",
      status: "New"
    },
    file_inventory: {
      files: [{ filename: "A100_24X_ADMIN.dbf", file_type: ".dbf", size_bytes: 4096 }],
      total_files: 1,
      parse_errors: []
    },
    vehicle_profile: {
      year: 2021,
      make: "Toyota",
      model: "Camry",
      vin: "4T1B11HK5MU123XXX",
      mileage: 48000
    },
    shop_profile: {
      name: "Main St Auto Body",
      drp_status: true
    },
    estimate_lines: {
      items: [
        {
          line_no: 1,
          operation: "Replace",
          description: "Frt Bumper Cover",
          part_type: "OEM",
          quantity: 1,
          price: 450.00,
          labor_hours: 2.5,
          paint_hours: 1.5,
          sublet_amount: 0
        },
        {
          line_no: 2,
          operation: "Replace",
          description: "Radiator Support Assembly",
          part_type: "OEM",
          quantity: 1,
          price: 620.00,
          labor_hours: 4.0,
          paint_hours: 0,
          sublet_amount: 0
        },
        {
          line_no: 3,
          operation: "Sublet",
          description: "Four Wheel Alignment",
          quantity: 1,
          price: 0,
          labor_hours: 0,
          paint_hours: 0,
          sublet_amount: 120.00
        }
      ],
      totals: {
        gross_total: 1530.00, // 450 + 620 + 120 + ((2.5 + 4) * ~50) -- just dummy
        net_total: 1530.00,
        total_labor: 340.00,
        total_parts: 1070.00,
        total_paint: 0
      },
      supplement_count: 0
    },
    evidence_matrix: {
      photos: [
        {
          id: "p_01",
          url: "https://images.unsplash.com/photo-1542281286-9e0a16bb7366",
          type: "interior",
          damage_area: "unknown",
          clarity: "high"
        }
      ],
      missing_required_photos: ["exterior_front", "vin"],
      photo_sufficiency_score: 45
    },
    findings: [
        {
            id: "f_audit_004",
            rule_id: "AUDIT_004",
            severity: "medium",
            category: "line_item_support",
            message: "Misc/Sublet charge >$50 requires invoice/review.",
            affected_lines: [3],
            evidence_refs: [],
            recommended_action: "Request Sublet Invoice.",
            status: "open"
        }
    ],
    rule_results: [],
    scorecard: {
      overall_score: 85,
      verdict: "Review",
      category_scores: {
        structural_integrity: 100,
        line_item_support: 80,
        parts_accuracy: 100,
        labor_reasonableness: 100,
        documentation_readiness: 90,
        carrier_compliance: 100
      },
      confidence: 0.92
    },
    narrative: {
      damage_summary: "Front end impact involving bumper cover and radiator support.",
      claim_summary: "Claim requires review for missing sublet invoice.",
      reviewer_notes: "",
      escalation_note: ""
    },
    reviewer_feedback: {
      actions: [],
      audit_duration_seconds: 0
    }
  }
];
