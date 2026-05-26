"""
Auditor return comment templates from Tommy's Communication Playbook (AE-111 through AE-160).
Approved phrasing that stays on the estimating side of the adjusting/appraising boundary.
"""
from typing import Dict

# Safe-harbor templates for every common audit finding
RETURN_COMMENTS: Dict[str, str] = {
    # Parts & Repair/Replace
    "replace_not_supported": (
        "Please re-evaluate the {part} operation. "
        "Current photos do not clearly support non-repairability. "
        "Please provide supporting rationale or revise as appropriate."
    ),
    "oem_not_supported": (
        "Please confirm OEM part necessity for {part}. "
        "Vehicle is {year} with {mileage} miles. "
        "Please provide alternate part sourcing documentation or revise as appropriate."
    ),
    "blend_not_supported": (
        "Please confirm blend necessity on {panel}. "
        "Current documentation does not include color match support. "
        "Please provide rationale or revise as appropriate."
    ),

    # Documentation
    "sublet_invoice_missing": (
        "Please provide supporting invoice for {operation} on line {line}. "
        "NatGen requires documentation for all sublet charges."
    ),
    "scan_invoice_missing": (
        "Please provide pre-/post-scan documentation for line {line}. "
        "NatGen requires scan invoices for all scan charges."
    ),
    "dealer_invoice_lump": (
        "Please itemize the dealer invoice by operation. "
        "NatGen requires individual CCC labor lines — single-line invoice totals are not approved."
    ),
    "photos_insufficient": (
        "Current photos do not clearly support {operation} on line {line}. "
        "Please provide additional photos showing {requirement} or revise as appropriate."
    ),

    # Admin
    "shop_info_missing": (
        "Please complete repair facility information. "
        "NatGen requires shop name, address, and phone number on all estimates and supplements."
    ),
    "nada_missing": (
        "Please attach NADA Normal Trade-In valuation. "
        "NatGen requires NADA on ALL files — repairable and total loss."
    ),
    "deductible_missing": (
        "Please add deductible to estimate totals. "
        "{loss_type} claims require deductible listed even if $0."
    ),

    # Hail/PDR
    "hail_photos_no_board": (
        "Hail photos must include striped board or checker board. "
        "Please retake hail photos with board and resubmit."
    ),
    "pdr_markup_verify": (
        "Please verify PDR markup on line {line} is documented. "
        "NatGen requires scope sheet or hail matrix support for PDR increases."
    ),
    "hail_roof_at_residence": (
        "Roof replacement at residence requires extreme golf-ball sized indentations "
        "or entire roof peppered with hail. Please verify conditions are met or revise."
    ),

    # General
    "safe_harbor": (
        "It does not appear that {concern}. Please review and adjust."
    ),
    "general_review": (
        "Please review the estimate and make any adjustments that are needed based on review."
    ),
    "review_and_revise": (
        "Please review and revise as appropriate."
    ),
    "clarify_rationale": (
        "Please clarify the rationale for {operation}."
    ),
    "escalate_to_manager": (
        "This finding requires manager review. "
        "If the appraiser pushes back once and it isn't resolving, escalate — don't waste rounds."
    ),
}

# Prohibited phrases and their approved alternatives
PROHIBITED_ALTERNATIVES = {
    "Remove this / Delete operation": '"Please clarify the rationale for replacement."',
    "Do not pay / We're not paying that": '"Please re-evaluate this operation."',
    "Cap labor at X hours": '"Photos do not currently support replacement."',
    "Write it as a repair": '"Please provide supporting documentation."',
    "Carrier will not allow this": '"Please review the published P-page note."',
    "Take off the blend": '"Please confirm blend necessity per documentation."',
    "We don't pay for scans": '"Please provide pre-/post-scan documentation."',
    "Change estimate to": '"Please review and revise as appropriate."',
    "Too expensive / Reduce / Cut": "Avoid cost-driven phrasing entirely — request documentation instead.",
}
