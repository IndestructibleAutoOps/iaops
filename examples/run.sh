set -euo pipefail
python -m pip install -e . >/dev/null
echo "=== PLAN ==="
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode plan
echo "=== REPAIR ==="
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode repair
echo "=== VERIFY ==="
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode verify
echo "=== SEAL ==="
indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project examples/dirty_project --mode seal