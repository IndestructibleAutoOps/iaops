# Supply Chain v1.0 Deliverables

This repository now includes a minimal, working supply-chain baseline built around Cosign, Syft, and OPA.

## Components
- Build & Sign: `scripts/ci/build_sign_show.py` builds images, generates SBOMs, and signs with Cosign.
- Policy Verification: `policy/rego/supplychain.rego` can be executed with `conftest test`.
- Verification Gate: `scripts/ci/verify_gate.py` checks signatures, attestations, and SBOM presence.
- Dependency Management: `scripts/ci/dependericy_check.py` evaluates CycloneDX SBOM data for vulnerabilities and license policy.
- Audit Logging: `scripts/monitoring/audit_logger.py` writes JSONL audit events.
- Monitoring & Alerting: `scripts/monitoring/anomaly_detector.py` flags high-priority Falco-style events.

## Workflows
- GitHub Actions: `.github/workflows/_build_sign_sbom.yml` builds, generates SBOM, signs, verifies, and uploads artifacts.
- Kubernetes: `k8s/supplychain/deployment.yaml` deploys the service with config provided by ConfigMap and service account isolation.
- Docker: `Dockerfile` packages the IaOps engine with defaults set to run the pipeline.

## Usage
1. Build & Sign locally:
   ```bash
   python scripts/ci/build_sign_show.py --image ghcr.io/org/iaops:dev --sbom-path sbom.json --dry-run
   ```
2. Verify gate:
   ```bash
   python scripts/ci/verify_gate.py --image ghcr.io/org/iaops:dev --sbom sbom.json --dry-run
   ```
3. Dependency gate:
   ```bash
   python scripts/ci/dependericy_check.py --sbom sbom.json --allowed-licenses Apache-2.0,MIT
   ```
4. Audit logging:
   ```bash
   python -c "from scripts.monitoring.audit_logger import AuditLogger; AuditLogger().log('deploy', subject='release')"
   ```
5. Anomaly detection:
   ```bash
   python scripts/monitoring/anomaly_detector.py --events-file falco.jsonl --min-priority critical
   ```
