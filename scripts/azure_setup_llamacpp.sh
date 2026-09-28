#!/usr/bin/env bash
# Azure Ubuntu VM bootstrap: install llama.cpp server, download
# qwen2.5-coder:3b Q4_K_M GGUF, start a llama-server with our flags.
#
# Usage (on the VM, after SSH'ing in):
#   bash azure_setup_llamacpp.sh
#
# Idempotent: safe to re-run. Skips steps that already completed.
#
# After this completes:
#   - llama-server is running on 127.0.0.1:11435 with --parallel 8 --ctx 4096
#   - /health returns 200 OK
#   - systemd unit llama-server.service auto-restarts on crash
#   - HF_HOME / GGUF cache lives under /opt/llama.cpp/models/
#
# Then from your local Windows box, point forkling at this VM:
#   set FORKLING_BACKEND_URL=http://<VM-PUBLIC-IP>:11435
#   python scripts/run_llamacpp_remote.py --health-url http://<VM-PUBLIC-IP>:11435/health ...
#
# Tested against: Standard_NC4as_T4_v3 (Ubuntu 22.04 LTS Gen 2).
# Requires: sudo, ~3 GB free disk, ~5 minutes.

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration (override via env if needed)
# -----------------------------------------------------------------------------
LLAMACPP_HOME="${LLAMACPP_HOME:-/opt/llama.cpp}"
MODEL_REPO="${MODEL_REPO:-bartowski/Qwen2.5-Coder-3B-Instruct-GGUF}"
MODEL_FILE="${MODEL_FILE:-Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf}"
SERVER_HOST="${SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${SERVER_PORT:-11435}"
PARALLEL_SLOTS="${PARALLEL_SLOTS:-8}"
CTX_SIZE="${CTX_SIZE:-4096}"
GPU_LAYERS="${GPU_LAYERS:-99}"   # offload everything

echo "[azure-setup] target: ${LLAMACPP_HOME}"
echo "[azure-setup] model:  ${MODEL_REPO}/${MODEL_FILE}"
echo "[azure-setup] server: ${SERVER_HOST}:${SERVER_PORT} --parallel ${PARALLEL_SLOTS} -c ${CTX_SIZE}"

# -----------------------------------------------------------------------------
# 1. System deps
# -----------------------------------------------------------------------------
echo "[azure-setup] installing system deps (apt)..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential cmake git curl wget ca-certificates \
    libcurl4-openssl-dev

# Detect CUDA — NC-series VMs ship with NVIDIA drivers + CUDA toolkit
# already installed (Azure marketplace image). If not present, fall back
# to a CPU-only build.
HAS_CUDA=0
if command -v nvcc >/dev/null 2>&1; then
    HAS_CUDA=1
    echo "[azure-setup] nvcc found: $(nvcc --version | tail -1)"
elif [[ -d /usr/local/cuda ]]; then
    HAS_CUDA=1
    echo "[azure-setup] CUDA toolkit at /usr/local/cuda"
else
    echo "[azure-setup] WARNING: no CUDA detected. Building CPU-only llama.cpp."
    echo "[azure-setup]         This works but is ~10x slower than GPU build."
    echo "[azure-setup]         If you provisioned a GPU SKU, install CUDA drivers first:"
    echo "[azure-setup]           sudo apt-get install -y nvidia-driver-535 nvidia-cuda-toolkit"
fi

# -----------------------------------------------------------------------------
# 2. Clone + build llama.cpp
# -----------------------------------------------------------------------------
if [[ ! -d "${LLAMACPP_HOME}" ]]; then
    echo "[azure-setup] cloning llama.cpp..."
    sudo git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "${LLAMACPP_HOME}"
    sudo chown -R "$(whoami)" "${LLAMACPP_HOME}"
fi

cd "${LLAMACPP_HOME}"
if [[ ! -x ./build/bin/llama-server ]]; then
    echo "[azure-setup] building llama.cpp (this takes ~2 minutes)..."
    if [[ "${HAS_CUDA}" == "1" ]]; then
        cmake -B build -DGGML_CUDA=ON
    else
        cmake -B build
    fi
    cmake --build build --config Release -j"$(nproc)"
else
    echo "[azure-setup] llama.cpp already built at ./build/bin/llama-server"
fi

SERVER_BIN="${LLAMACPP_HOME}/build/bin/llama-server"
[[ -x "${SERVER_BIN}" ]] || { echo "[azure-setup] FATAL: ${SERVER_BIN} not built"; exit 1; }

# -----------------------------------------------------------------------------
# 3. Download the GGUF model
# -----------------------------------------------------------------------------
MODEL_DIR="${LLAMACPP_HOME}/models"
MODEL_PATH="${MODEL_DIR}/${MODEL_FILE}"
mkdir -p "${MODEL_DIR}"

if [[ ! -f "${MODEL_PATH}" ]]; then
    echo "[azure-setup] downloading ${MODEL_FILE} from ${MODEL_REPO}..."
    # hf CLI is the simplest way; fall back to direct URL if not installed
    if command -v hf >/dev/null 2>&1; then
        hf download "${MODEL_REPO}" "${MODEL_FILE}" --local-dir "${MODEL_DIR}"
    else
        pip install -q --user huggingface_hub
        python3 -m huggingface_hub.hf_download \
            --repo-id "${MODEL_REPO}" \
            --filename "${MODEL_FILE}" \
            --local-dir "${MODEL_DIR}"
    fi
else
    echo "[azure-setup] model already at ${MODEL_PATH}"
fi

[[ -f "${MODEL_PATH}" ]] || { echo "[azure-setup] FATAL: model download failed"; exit 1; }

# -----------------------------------------------------------------------------
# 4. systemd unit for llama-server (auto-restart on crash)
# -----------------------------------------------------------------------------
SERVICE_FILE="/etc/systemd/system/llama-server.service"
if [[ ! -f "${SERVICE_FILE}" ]]; then
    echo "[azure-setup] writing systemd unit..."
    sudo tee "${SERVICE_FILE}" >/dev/null <<EOF
[Unit]
Description=llama.cpp server (qwen2.5-coder:3b Q4_K_M)
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${LLAMACPP_HOME}
ExecStart=${SERVER_BIN} \\
    -m ${MODEL_PATH} \\
    -c ${CTX_SIZE} \\
    --parallel ${PARALLEL_SLOTS} \\
    -ngl ${GPU_LAYERS} \\
    --host ${SERVER_HOST} \\
    --port ${SERVER_PORT}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable llama-server.service
fi

# -----------------------------------------------------------------------------
# 5. Start (or restart) the service, wait for /health to return 200
# -----------------------------------------------------------------------------
echo "[azure-setup] starting llama-server.service..."
sudo systemctl restart llama-server.service

echo "[azure-setup] waiting for /health to return 200 (up to 120s while model loads)..."
for i in $(seq 1 60); do
    if curl -fsS --max-time 2 "http://${SERVER_HOST}:${SERVER_PORT}/health" >/dev/null 2>&1; then
        echo "[azure-setup] /health returned 200 after ~${i}s"
        break
    fi
    sleep 2
done

if ! curl -fsS --max-time 2 "http://${SERVER_HOST}:${SERVER_PORT}/health" >/dev/null 2>&1; then
    echo "[azure-setup] WARNING: /health did not return 200 within 120s."
    echo "[azure-setup]         Last 20 journal lines:"
    sudo journalctl -u llama-server.service --no-pager -n 20 || true
    exit 1
fi

# -----------------------------------------------------------------------------
# 6. Smoke test: send a tiny completion request
# -----------------------------------------------------------------------------
echo "[azure-setup] smoke test: tiny chat completion..."
SMOKE_RESP=$(curl -fsS --max-time 30 "http://${SERVER_HOST}:${SERVER_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5-coder:3b","messages":[{"role":"user","content":"Reply with the single word READY and nothing else."}],"max_tokens":8,"temperature":0}')
echo "[azure-setup] smoke response: ${SMOKE_RESP}"

if ! grep -q '"content":"READY"' <<<"${SMOKE_RESP}"; then
    echo "[azure-setup] WARNING: smoke test did not get READY. Check logs."
    sudo journalctl -u llama-server.service --no-pager -n 30 || true
    exit 1
fi

# -----------------------------------------------------------------------------
# 7. Done
# -----------------------------------------------------------------------------
echo ""
echo "[azure-setup] DONE."
echo "[azure-setup] llama-server is running at http://${SERVER_HOST}:${SERVER_PORT}"
echo "[azure-setup] OpenAI-compatible endpoint: /v1/chat/completions"
echo "[azure-setup] Health check:               /health"
echo ""
echo "[azure-setup] From your local box, test the public URL:"
echo "  curl http://<VM-PUBLIC-IP>:${SERVER_PORT}/health"
echo ""
echo "[azure-setup] Then point forkling at it:"
echo "  set FORKLING_BACKEND_URL=http://<VM-PUBLIC-IP>:${SERVER_PORT}"
echo "  python scripts/run_llamacpp_remote.py --health-url http://<VM-PUBLIC-IP>:${SERVER_PORT}/health -- ..."
echo ""
echo "[azure-setup] Useful commands:"
echo "  sudo systemctl status llama-server.service    # current state"
echo "  sudo journalctl -u llama-server.service -f   # follow logs"
echo "  sudo systemctl restart llama-server.service  # reload model"
