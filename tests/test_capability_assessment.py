from indestructibleautoops.capability_assessment import (
    AssessmentResult,
    CapabilityClaim,
    CapabilityEvidence,
    EVIDENCE_REQUIREMENTS,
    UnverifiedCapability,
    evaluate_capabilities,
)


def test_fully_evidenced_claim_is_implemented():
    claim = CapabilityClaim(
        name="config validation",
        evidence=CapabilityEvidence(
            inputs=["pipeline.yaml"],
            outputs=["validation report"],
            process="jsonschema validation via schemas/pipeline.schema.json",
        ),
    )

    result = evaluate_capabilities([claim])

    assert isinstance(result, AssessmentResult)
    assert result.implemented == [claim]
    assert result.unverified == []


def test_missing_outputs_and_proof_are_reported():
    claim = CapabilityClaim(
        name="multi-agent orchestration",
        evidence=CapabilityEvidence(
            inputs=["project root"],
            outputs=[],
            process=None,
            observable=None,
        ),
    )

    result = evaluate_capabilities([claim])

    assert result.implemented == []
    assert len(result.unverified) == 1
    unverified: UnverifiedCapability = result.unverified[0]
    assert unverified.claim.name == "multi-agent orchestration"
    assert unverified.missing_fields == ["outputs", "process", "observable"]
    assert unverified.evidence_needed == [
        EVIDENCE_REQUIREMENTS["outputs"],
        EVIDENCE_REQUIREMENTS["process"],
        EVIDENCE_REQUIREMENTS["observable"],
    ]


def test_observable_proof_satisfies_process_gate():
    claim = CapabilityClaim(
        name="telemetry capture",
        evidence=CapabilityEvidence(
            inputs=["webhook event"],
            outputs=["event written to store"],
            observable="integration test coverage and audit log",
        ),
    )

    result = evaluate_capabilities([claim])

    assert result.implemented == [claim]
    assert result.unverified == []
