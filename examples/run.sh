set -euo pipefail
python -m pip install -e . >/dev/null
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode plan
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode verify || true
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode seal