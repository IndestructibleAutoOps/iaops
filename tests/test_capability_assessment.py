from indestructibleautoops.capability_assessment import (
    CapabilityClaim,
    CapabilityEvidence,
    evaluate_capabilities,
)


def test_marks_capability_as_implemented_when_evidence_complete():
    claim = CapabilityClaim(
        name="config validation",
        description="Validates pipeline specs against the schema",
        evidence=CapabilityEvidence(
            inputs=["pipeline.yaml"],
            outputs=["validation report"],
            process="jsonschema validation through schemas/pipeline.schema.json",
            observable="validation log",
        ),
    )

    assessment = evaluate_capabilities([claim])

    assert len(assessment.implemented) == 1
    assert not assessment.unverified
    assert not assessment.missing_information

    implemented = assessment.implemented[0]
    assert implemented["name"] == "config validation"
    assert "Inputs/outputs" in implemented["reason"]
    assert implemented["evidence"]["inputs"] == ["pipeline.yaml"]
    assert implemented["evidence"]["outputs"] == ["validation report"]


def test_reports_missing_evidence_for_unverified_claims():
    claim = CapabilityClaim(
        name="multi-agent orchestration",
        description="Parallel DAG execution with approvals",
        evidence=CapabilityEvidence(inputs=["project root"]),
    )

    assessment = evaluate_capabilities([claim])

    assert not assessment.implemented
    assert len(assessment.unverified) == 1

    unverified = assessment.unverified[0]
    assert unverified["name"] == "multi-agent orchestration"
    assert "missing evidence fields" in unverified["reason"]
    assert "Provide concrete outputs or artifacts" in unverified["evidence_needed"]
    assert "Describe a reproducible process or steps" in unverified["evidence_needed"]

    # Missing information is aggregated and deduplicated
    assert set(assessment.missing_information) == {
        "Provide concrete outputs or artifacts",
        "Describe a reproducible process or steps",
        "Attach observable proof (logs, artifacts, command traces)",
    }
