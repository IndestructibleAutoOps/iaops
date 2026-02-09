from indestructibleautoops.capability_assessment import (
    CapabilityAssessment,
    CapabilityClaim,
    CapabilityEvidence,
    EVIDENCE_REQUIREMENTS,
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

    assert isinstance(assessment, CapabilityAssessment)
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

    assert set(assessment.missing_information) == {
        EVIDENCE_REQUIREMENTS["outputs"],
        EVIDENCE_REQUIREMENTS["process"],
        EVIDENCE_REQUIREMENTS["observable"],
    }


def test_observable_proof_is_sufficient_with_inputs_and_outputs():
    claim = CapabilityClaim(
        name="telemetry capture",
        evidence=CapabilityEvidence(
            inputs=["webhook event"],
            outputs=["event stored"],
            observable="integration test log and audit trail",
        ),
    )

    assessment = evaluate_capabilities([claim])

    assert len(assessment.implemented) == 1
    assert not assessment.unverified
