#!/usr/bin/env bash
# Pack submission ZIP for Adobe University Hackathon 2026 Round 3
set -euo pipefail

OUTPUT_ZIP="brand-ai-readiness-audit.zip"
echo "Packaging submission into ${OUTPUT_ZIP}..."

rm -f "${OUTPUT_ZIP}"

zip -r "${OUTPUT_ZIP}" \
    marketplace.json \
    skills/ \
    src/ \
    config/ \
    docs/ \
    gui/ \
    tests/ \
    LICENSE \
    README.md \
    requirements.txt \
    pyproject.toml \
    -x "*.git*" \
    -x "*node_modules*" \
    -x "*__pycache__*" \
    -x "*.pytest_cache*" \
    -x "*tests/fixtures*" \
    -x "*report.json" \
    -x "*.zip"

ZIP_SIZE_MB=$(du -m "${OUTPUT_ZIP}" | cut -f1)
echo "Package created: ${OUTPUT_ZIP} (${ZIP_SIZE_MB} MB)"

if [ "${ZIP_SIZE_MB}" -gt 45 ]; then
    echo "ERROR: Package size exceeds 45 MB limit!"
    exit 1
else
    echo "SUCCESS: Package size is well within the 45 MB limit."
fi
