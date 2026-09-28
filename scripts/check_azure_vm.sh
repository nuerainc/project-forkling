#!/usr/bin/env bash
# Post-install verification for the Azure T4 llama.cpp server.
#
# Usage (on the VM, after running azure_setup_llamacpp.sh):
#   bash check_azure_vm.sh
#
# Exit code: 0 = all checks pass, 1 = one or more failed.
# Every failing check prints the exact next command to fix it.
#
# This is a read-only diagnostic. It does NOT start, stop, or modify
# the llama-server service. It only inspects state and pings HTTP.

set -uo pipefail   # NOT -e: we want all checks to run, then report.

LLAMACPP_HOME="${LLAMACPP_HOME:-/opt/llama.cpp}"
SERVER_HOST="${SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${SERVER_PORT:-11435}"
SERVICE="llama-server.service"

PASS=0
FAIL=0

green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
blue()  { printf '\033[1;36m%s\033[0m\n' "$1"; }

ok()   { green "  [PASS] $1"; PASS=$((PASS + 1)); }
bad()  { red   "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

blue "=== Azure VM llama.cpp verification ==="
blue "target: http://${SERVER_HOST}:${SERVER_PORT}"
echo

# --- Check 1: GPU present -------------------------------------------------
blue "[1/7] GPU presence"
if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi -L >/dev/null 2>&1 && [[ -n "$(nvidia-smi -L 2>/dev/null)" ]]; then
        ok "nvidia-smi sees: $(nvidia-smi -L | tr '\n' ' ')"
    else
        bad "nvidia-smi present but reports no GPU"
        echo "         fix: check the VM SKU actually has a GPU attached"
        echo "              az vm show -g forkling-rg -n forkling-t4-01"
    fi
else
    bad "nvidia-smi not found — CPU-only build?"
    echo "         fix: this may be fine for a smoke test, but slow."
    echo "              For GPU: sudo apt-get install -y nvidia-driver-535"
fi

# --- Check 2: VRAM headroom ----------------------------------------------
blue "[2/7] VRAM headroom"
if command -v nvidia-smi >/dev/null 2>&1; then
    # T4 = 16 GiB = 16384 MiB. Warn if under 12 GiB free.
    FREE_MIB=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1)
    if [[ -n "${FREE_MIB}" ]]; then
        if (( FREE_MIB >= 12000 )); then
            ok "free VRAM: ${FREE_MIB} MiB (plenty for --parallel 8 at ctx 4096)"
        elif (( FREE_MIB >= 6000 )); then
            ok "free VRAM: ${FREE_MIB} MiB (usable; consider --parallel 4)"
        else
            bad "free VRAM: ${FREE_MIB} MiB (too low)"
            echo "         fix: lower PARALLEL_SLOTS and CTX_SIZE, then re-run:"
            echo "              PARALLEL_SLOTS=2 CTX_SIZE=2048 bash ~/azure_setup_llamacpp.sh"
        fi
    else
        bad "could not read VRAM free via nvidia-smi"
    fi
fi

# --- Check 3: systemd unit active ----------------------------------------
blue "[3/7] systemd unit active"
if systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE}"; then
    ok "${SERVICE} is installed"
    if systemctl is-active --quiet "${SERVICE}"; then
        ok "${SERVICE} is active"
    else
        bad "${SERVICE} is NOT active (state: $(systemctl is-active ${SERVICE} 2>/dev/null || echo unknown))"
        echo "         fix: sudo systemctl restart ${SERVICE}"
    fi
else
    bad "${SERVICE} not found"
    echo "         fix: re-run the setup script: bash ~/azure_setup_llamacpp.sh"
fi

# --- Check 4: /health responds 200 ---------------------------------------
blue "[4/7] /health endpoint"
HEALTH_BODY=$(curl -fsS --max-time 5 "http://${SERVER_HOST}:${SERVER_PORT}/health" 2>/dev/null)
if [[ $? -eq 0 ]]; then
    ok "/health returned: ${HEALTH_BODY:-<empty>}"
else
    bad "/health did not return 200"
    echo "         fix 1: is the model still loading? wait 30s, retry."
    echo "         fix 2: sudo journalctl -u ${SERVICE} -n 50"
fi

# --- Check 5: model is resident ------------------------------------------
blue "[5/7] model resident in VRAM"
if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi --query-compute-apps=pid,used_memory --format=csv 2>/dev/null | grep -q "MiB"; then
        ok "compute app resident: $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ' ')"
    else
        bad "no compute app in nvidia-smi — model may be CPU-only"
        echo "         fix: confirm the binary was built with -DGGML_CUDA=ON"
        echo "              grep CUDA ${LLAMACPP_HOME}/build/CMakeCache.txt"
    fi
fi

# --- Check 6: parallel slots + per-slot ctx -------------------------------
blue "[6/7] parallel slots + per-slot context"
if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi 2>/dev/null | grep -q "Processes"; then
        ok "process table readable"
    else
        bad "nvidia-smi cannot read the process table"
        echo "         fix: echo \$? should be 0. If not, driver/container issue."
    fi
fi
# The real per-slot ctx is in the startup log (n_ctx_per_seq).
if [[ -x "${LLAMACPP_HOME}/build/bin/llama-server" ]]; then
    ok "llama-server binary present"
else
    bad "llama-server binary missing at ${LLAMACPP_HOME}/build/bin/llama-server"
    echo "         fix: bash ~/azure_setup_llamacpp.sh"
fi

# --- Check 7: smoke chat completion ---------------------------------------
blue "[7/7] smoke chat completion"
START=$(date +%s)
SMOKE=$(curl -fsS --max-time 60 "http://${SERVER_HOST}:${SERVER_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5-coder:3b","messages":[{"role":"user","content":"Reply with the single word READY and nothing else."}],"max_tokens":8,"temperature":0}' 2>/dev/null)
RC=$?
ELAPSED=$(( $(date +%s) - START ))

if [[ $RC -eq 0 && -n "$SMOKE" ]]; then
    if grep -q '"content":"READY"' <<<"$SMOKE"; then
        ok "smoke test returned READY in ${ELAPSED}s"
    else
        bad "smoke test responded but not with READY"
        echo "         got: ${SMOKE:0:200}"
        echo "         fix: this is a model-quality issue, not a server issue."
        echo "              Check: curl http://${SERVER_HOST}:${SERVER_PORT}/v1/models"
    fi
elif [[ $RC -eq 0 ]]; then
    bad "smoke test returned empty"
else
    bad "smoke test request failed (curl rc=${RC})"
    echo "         fix: check the service log — sudo journalctl -u ${SERVICE} -n 50"
fi

# --- Summary ---------------------------------------------------------------
echo
blue "=== Summary ==="
echo "  passed: ${PASS}"
echo "  failed: ${FAIL}"
echo

if [[ $FAIL -eq 0 ]]; then
    green "ALL CHECKS PASSED — the VM is ready to run experiments."
    echo
    echo "Next steps:"
    echo "  1. Get the public IP from Azure portal (or: az vm show -g forkling-rg -n forkling-t4-01 --query networkProfile.networkInterfaces[0].publicIpAddress.id -o tsv)"
    echo "  2. From your LOCAL box, test reachability:"
    echo "       curl http://<VM-PUBLIC-IP>:${SERVER_PORT}/health"
    echo "  3. Confirm the NSG allows ${SERVER_PORT} from your home IP only."
    echo "  4. Run an experiment (see docs/AZURE_SETUP.md §Connecting from your local box)."
    exit 0
else
    red "${FAIL} CHECK(S) FAILED — see the 'fix:' lines above."
    echo
    echo "Common causes, in order of likelihood:"
    echo "  a) Spot eviction deallocated the VM while you were away"
    echo "     fix: az vm start -g forkling-rg -n forkling-t4-01"
    echo "  b) The model is still loading on first boot (3B at 4 GB takes ~30s)"
    echo "     fix: wait, then re-run: bash ~/check_azure_vm.sh"
    echo "  c) CUDA build failed; fell back to CPU"
    echo "     fix: grep CUDA /opt/llama.cpp/build/CMakeCache.txt"
    exit 1
fi
