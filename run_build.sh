#!/bin/bash
set -e
cd /root/YGSTUDY
echo "=== STEP 1: gen_nav.py 미리보기 ==="
python3 tools/gen_nav.py
echo ""
echo "=== STEP 2: gen_nav.py --write ==="
python3 tools/gen_nav.py --write
echo ""
echo "=== STEP 3: mkdocs build ==="
python3 -m mkdocs build --strict 2>&1
echo ""
echo "=== DONE ==="
