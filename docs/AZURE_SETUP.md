# Azure setup for Forkland experiments

> How to provision an Ubuntu VM with a GPU on Azure (Free Trial or
> Azure for Students), install llama.cpp server, and point forkling at
> it from your local box. Read this before requesting quota or creating
> resources.

## TL;DR

1. Have an Azure subscription with GPU quota (Free Trial works after
   quota request; Azure for Students is hit-or-miss).
2. Create a `Standard_NC4as_T4_v3` spot VM in **East US** with Ubuntu
   22.04 LTS, SSH-key-only auth.
3. Lock down the NSG to your home IP only (22 + 11435).
4. SSH in, run `bash scripts/azure_setup_llamacpp.sh` — that installs
   llama.cpp server with our flags, downloads the model, and starts it
   as a systemd service.
5. From your local box, run experiments via
   `scripts/run_llamacpp_remote.py`, pointing at the VM's public IP.

## Subscription tiers

| Tier | Credits | Duration | GPU quota | Notes |
|---|---|---|---|---|
| **Free Trial** | $200 | 30 days from activation | 0 default — must request | Activated once per Azure tenant, ever |
| **Azure for Students** | $100 | 12 months | Often denied on Students offer | Verify via `*.edu` / Full Sail email |
| **Pay-as-you-go** | none | n/a | Depends on region/SKU | Bring your own payment method |

**Recommended:** pursue **Azure for Students first** (no card required,
12-month runway, even if GPU quota denied the $100 still works for
CPU VMs). Fall back to Free Trial if Students denies GPU. Free Trial is
a one-time activation — don't burn it on a hobby test.

## Quota request (the bottleneck)

Most subscriptions start with **0 GPU vCPUs**. Request it:

1. Portal → **Subscriptions** → click your sub.
2. Left rail → **Usage + quotas**.
3. Filter / search: `NCas T4` or `Standard NCSv3`.
4. Click the row → top toolbar → **Request quota increase**.
5. Region: **East US** (cheapest, most quota available).
6. New limit: **4 vCPUs** (one T4 VM).
7. Justification (paste verbatim):

   > Running local LLM inference experiments (llama.cpp server,
   > qwen2.5-coder:3b GGUF) for an open-source self-improving-agent
   > research project. Short-duration workloads, no production
   > deployment, no customer-facing traffic. Single VM at a time,
   > deallocated when idle.

8. Submit. Decision arrives in minutes to ~1 business day. If denied,
   try the next region (West US 2 → West Europe).

**Important:** request quota on BOTH the Students sub and the Free
Trial sub. Whichever approves first wins. The other request stays open
or can be cancelled.

## VM creation (portal path)

Portal: [portal.azure.com](https://portal.azure.com) → search bar →
**Virtual machines** → **+ Create** → **Azure virtual machine**.

| Field | Value |
|---|---|
| **Subscription** | Students or Free Trial (whichever has GPU quota) |
| **Resource group** | Create new → `forkling-rg` |
| **VM name** | `forkling-t4-01` |
| **Region** | **East US** |
| **Image** | **Ubuntu Server 22.04 LTS - x64 Gen 2** |
| **Size** | See all sizes → search "NC4as T4" → **Standard_NC4as_T4_v3** (4 vCPU, 16 GB VRAM, 28 GB RAM) |
| **Authentication** | **SSH public key** — paste your `~/.ssh/id_rsa.pub` content |
| **Public inbound ports** | **Allow selected ports** → 22 only |
| **OS disk** | Standard SSD 64 GB |
| **Spot instance** | ✅ Yes. Eviction policy: **Stop/Deallocate** (disk survives; you can re-attach on the next VM) |
| **Max price** | Leave default (-1 = pay up to on-demand) |

### NSG hardening (do this immediately after VM creates)

The default NSG is too permissive. Edit it:

1. Portal → your VM → **Networking** → click the NSG name.
2. **Inbound security rules** → delete any default "Allow 22 from Any".
3. **+ Add** two rules:

   | Priority | Name | Port | Source | Action |
   |---|---|---|---|---|
   | 100 | `allow-ssh-home` | 22 | `<your-home-IP>/32` | Allow |
   | 110 | `allow-llamacpp-home` | 11435 | `<your-home-IP>/32` | Allow |

   Get your home IP: `curl ifconfig.me` from your local PowerShell.

4. Save. From this point, the llama.cpp port is reachable only from
   your home network. Not from the open internet.

## VM creation (az CLI equivalent)

If you prefer one-line automation:

```powershell
# Find your home IP
$HOME_IP = (Invoke-WebRequest -UseBasicParsing ifconfig.me).Content.Trim()

az vm create `
  --resource-group forkling-rg `
  --name forkling-t4-01 `
  --image Ubuntu2204 `
  --size Standard_NC4as_T4_v3 `
  --ssh-key-values "$HOME\.ssh\id_rsa.pub" `
  --priority Spot `
  --eviction-policy Deallocate `
  --public-ip-sku Standard `
  --nsg-rule SSH `
  --admin-username azureuser `
  --os-disk-size-gb 64 `
  --location eastus

# Lock down NSG (replace NIC name with the one Azure assigned)
az network nsg rule create --nsg-name forkling-t4-01NSG `
  --resource-group forkling-rg `
  --name allow-llamacpp-home `
  --priority 110 --direction Inbound --access Allow `
  --protocol Tcp --destination-port-ranges 11435 `
  --source-address-prefixes "$HOME_IP/32"
```

## In-VM setup (the one-command install)

SSH into the VM:

```bash
ssh azureuser@<VM-PUBLIC-IP>
```

Then drop the setup script on the VM and run it. Easiest path: pull
from the forkling repo (after we push), or copy the file from your
local box via `scp`:

```bash
# From your local box:
scp scripts/azure_setup_llamacpp.sh azureuser@<VM-PUBLIC-IP>:~/azure_setup_llamacpp.sh

# On the VM:
bash ~/azure_setup_llamacpp.sh
```

The script will, in order:

1. Install build deps (cmake, build-essential, libcurl)
2. Clone llama.cpp to `/opt/llama.cpp`
3. Build with CUDA support (detected from `/usr/local/cuda` or `nvcc`)
4. Download `qwen2.5-coder:3b-instruct-q4_k_m.gguf` (~2.0 GB) from
   `bartowski/Qwen2.5-Coder-3B-Instruct-GGUF`
5. Write a systemd unit `llama-server.service`
6. Start the service, wait for `/health` to return 200
7. Send a tiny smoke-test chat completion ("Reply READY")

Total time: ~5 minutes (download is the slowest part). Re-running is
idempotent.

### What you should see when done

```
[azure-setup] /health returned 200 after ~25s
[azure-setup] smoke response: {"id":"...","choices":[{"message":{"role":"assistant","content":"READY"}, ...
[azure-setup] DONE.
```

## Connecting from your local box

Once the VM's `/health` returns 200:

```powershell
# Local sanity check
curl http://<VM-PUBLIC-IP>:11435/health

# Set the backend URL (Windows PowerShell)
$env:FORKLING_BACKEND_URL = "http://<VM-PUBLIC-IP>:11435"

# Run an experiment detached
python scripts/run_llamacpp_remote.py `
  --heartbeat results/exp012.heartbeat `
  --pid       results/exp012.pid `
  --log       results/exp012.log `
  --ckpt      results/exp012.ckpt.jsonl `
  --marker    results/exp012.json `
  --health-url "http://<VM-PUBLIC-IP>:11435/health" `
  --interval  10 `
  -- PYTHONHASHSEED=20261015 python -m forkling experiment run --bench ... --arms ... --k 10 --reps 5
```

The local runner writes a JSON heartbeat compatible with
`scripts/check_smart.py`. The `/health` ping confirms the llama.cpp
server is alive every 10s.

## Compute tiers for the methods paper

Per `docs/BACKENDS.md`, every pre-registration must declare the compute
tier. The four tiers we'll see in exp001–exp012:

| Tier tag | Hardware | Backend | Used by |
|---|---|---|---|
| `ollama-laptop` | 4 GB VRAM, local Windows box | Ollama | exp001–exp009 (existing) |
| `llamacpp-laptop` | 4 GB VRAM, local Windows box | llama.cpp server | exp011 (TODO pre-reg) |
| `azure-t4-spot` | 16 GB VRAM, Azure T4 NC4as_v3 | llama.cpp server | exp012 (TODO pre-reg) |
| `azure-t4-students` | 16 GB VRAM, Azure T4 on Students | llama.cpp server | fallback if quota on Students |

The pre-reg declares which tier. The runner writes it into the result
file. The methods paper §3 reports effect sizes by tier.

## Cost reality (T4 spot, ~$0.30/hr)

| Workload | T4 spot wall-clock | Cost |
|---|---|---|
| Smoke test (this setup script) | ~10 min | ~$0.05 |
| One experiment run (1200 cells) | ~10–15 min | ~$0.05–$0.08 |
| v10a main run (6000 cells, --parallel 8) | ~25 min | ~$0.13 |
| Idle VM overnight (auto-shutdown at 22:00) | 0 compute, ~$0.001/hr storage | pennies |

**Realistic total for the queued workload: $1–$2.** Even with
debugging, retries, and accidentally leaving a VM running, we won't
crack $20. Your $200 Free Trial is overkill; your $100 Students
budget is enough.

## Safety rails (set BEFORE running anything expensive)

**Spending alert:**
1. Cost Management + Billing → **Cost alerts** → **+ Add**.
2. Threshold: **$20** (we won't hit it; this is a tripwire).
3. Email: yours. Action: notify only.

**Auto-shutdown (per VM):**
1. VM → **Auto-shutdown** → enable.
2. Time: **22:00 your local timezone**.
3. Action: notify + stop.

A stopped VM bills $0 compute (storage still costs ~$0.001/hr, ~$7/mo
for our 64 GB disk). If you forget to deallocate, auto-shutdown caps
the damage.

## Reproducibility — what changes when you switch backends

- Sampling numerics are not bit-identical across backends. exp009
  already uses temp=0.8, so seed-replication is non-trivial.
- The judge (`passed = (canonical in response)`) is deterministic on
  the response text. The metric is identical; the distribution of
  responses is not.
- The methods paper §3 must tag every result with its compute tier
  (already specified above).
- Pre-registered replication: exp011 (llama.cpp local) and exp012
  (Azure T4) exist to test whether the exp006 mechanism result holds
  under backend change. Both must be authored as pre-registrations
  BEFORE running.

## Cleanup

When you're done with a session:

```powershell
# Stop the VM (deallocated = no compute billing, disk retained)
az vm deallocate --resource-group forkling-rg --name forkling-t4-01

# Resume later
az vm start --resource-group forkling-rg --name forkling-t4-01

# Delete everything when truly done
az group delete --name forkling-rg --yes --no-wait
```

A deallocated VM costs ~$7/month for storage. A deleted VM is gone.
For multi-week pauses, deallocate. For end-of-project, delete the
resource group.
