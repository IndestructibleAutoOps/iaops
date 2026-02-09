from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

# Standardized evidence prompts to request concrete, verifiable proof.
EVIDENCE_REQUIREMENTS: dict[str, str] = {
    "inputs": "List the concrete inputs that the capability consumes.",
    "outputs": "List the tangible outputs the capability produces.",
    "process": "Describe the deterministic process or algorithm that produces the outputs.",
    "observable": "Provide observable proof such as logs, traces, tests, or runbooks.",
}


@dataclass
class CapabilityEvidence:
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    process: str | None = None
    observable: str | None = None


@dataclass
class CapabilityClaim:
    name: str
    evidence: CapabilityEvidence


class UnverifiedCapability(NamedTuple):
    claim: CapabilityClaim
    missing_fields: list[str]
    evidence_needed: list[str]


class AssessmentResult(NamedTuple):
    implemented: list[CapabilityClaim]
    unverified: list[UnverifiedCapability]


def _missing_evidence(evidence: CapabilityEvidence) -> list[str]:
    missing: list[str] = []
    if not evidence.inputs:
        missing.append("inputs")
    if not evidence.outputs:
        missing.append("outputs")

    has_process = bool(evidence.process)
    has_observable = bool(evidence.observable)
    if not has_process and not has_observable:
        missing.extend(["process", "observable"])

    return missing


def evaluate_capabilities(claims: list[CapabilityClaim]) -> AssessmentResult:
    """Partition capability claims into implemented vs unverified based on evidence completeness."""
    implemented: list[CapabilityClaim] = []
    unverified: list[UnverifiedCapability] = []

    for claim in claims:
        missing_fields = _missing_evidence(claim.evidence)
        if missing_fields:
            evidence_needed = [EVIDENCE_REQUIREMENTS[field] for field in missing_fields]
            unverified.append(UnverifiedCapability(claim, missing_fields, evidence_needed))
        else:
            implemented.append(claim)

    return AssessmentResult(implemented=implemented, unverified=unverified)
