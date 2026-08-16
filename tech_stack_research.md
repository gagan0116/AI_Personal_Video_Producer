# Tech Stack Research & Teammate Action Items

> **Priority: Have your teammate start executing Section 1 NOW while we finalize architecture**

---

## 🚨 IMMEDIATE: What Your Teammate Should Do NOW on GN100

Your teammate should start these in order. Each one takes time (downloading containers), so starting now saves hours:

### Step 1: Prerequisites (10 min)
```bash
# Verify NVIDIA driver and GPU
nvidia-smi

# Verify Docker and Docker Compose
docker --version
docker compose version

# Install NVIDIA Container Toolkit (if not present)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Install NGC CLI
wget -O ngc-cli.zip https://api.ngc.nvidia.com/v2/resources/nvidia/ngc-apps/ngc_cli/versions/4.10.0/files/ngccli_linux.zip
unzip ngc-cli.zip
sudo mv ngc-apps/ngc /usr/local/bin/
ngc config set
```

### Step 2: Get NGC API Key (5 min)
```bash
# Go to https://org.ngc.nvidia.com/setup/api-key and generate a key
# Then:
export NGC_API_KEY="<your-key>"
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
```

### Step 3: Pull Nemotron Lightning NIM (this takes 15-30 min to download)
```bash
export LOCAL_NIM_CACHE=~/.cache/nim
mkdir -p "$LOCAL_NIM_CACHE"

# Pull and start Nemotron 3.5 Lightning (our LLM backbone for agents)
docker run -d --gpus all \
  --name nemotron-lightning \
  -e NGC_API_KEY="$NGC_API_KEY" \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
  -p 8000:8000 \
  --shm-size=16GB \
  nvcr.io/nim/nvidia/nemotron-3.5-lightning-30b-a3b:latest
```

### Step 4: Install NemoClaw (10 min)
```bash
# Install NemoClaw CLI
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash

# Run onboarding wizard
nemoclaw onboard
# When prompted:
#   - Agent: OpenClaw
#   - Inference: point to local Nemotron Lightning (localhost:8000)
#   - Sandbox name: sports-producer
```

### Step 5: Install OpenShell (5 min)
```bash
# Install OpenShell
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh

# Verify
openshell --version
```

### Step 6: Clone VSS Blueprint (then we configure it after architecture is finalized)
```bash
git clone https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization.git
cd video-search-and-summarization
# DON'T start it yet — we need to configure it first
```

### Step 7: Install system dependencies
```bash
sudo apt-get install -y ffmpeg python3-pip nodejs npm
pip3 install fastapi uvicorn websockets httpx aiofiles python-multipart
```

---

## Research Findings

### 1. NVIDIA VSS (Video Search & Summarization)

#### What it provides:
| Service | Purpose | Model |
|---------|---------|-------|
| **VSS Agent** | Core orchestration, routes queries, manages tools | Nemotron Nano 9B |
| **VLM** | Video understanding, captioning, Q&A | Cosmos Reason (Cosmos3 Nano Reasoner) |
| **VIOS** | Video IO & Storage — manages RTSP streams, recording, playback | N/A (infra) |
| **Embeddings** | Semantic video embeddings for fusion search | cosmos-embed |
| **Dense Captioning** | Auto-generates text descriptions of video segments | VLM-powered |
| **Elasticsearch/Milvus** | Vector + text search over processed video | N/A (infra) |
| **Neo4j** | Graph database for entity relationships | N/A (infra) |
| **Phoenix** | Observability and monitoring | N/A (infra) |

#### Key Skills we'll use:
| Skill | How we use it |
|-------|--------------|
| `vss-deploy-dense-captioning` | Generate text descriptions of video segments as the match streams |
| `vss-ask-video` | Agents ask questions about specific moments ("What is player doing here?") |
| `vss-search-archive` | Agents search for specific types of moments via natural language |
| `vss-manage-alerts` | Set up real-time alerts for specific visual events (celebrations, fouls) |
| `vss-generate-video-report` | Generate summary reports per agent |

#### Deployment on GN100:
- **Supports DGX Spark** explicitly (GB10 Grace Blackwell)
- Docker Compose based — `docker compose up -d` in `deploy/docker/`
- Need to configure `.env` for local model deployment
- VLM: Cosmos Reason 2 (8B) — runs on Spark
- LLM: Nemotron Nano 9B — lightweight, for VSS's own agent routing
- Total VSS memory footprint: ~30-40GB estimated

#### Video Input:
- Supports **RTSP streams** (live/simulated) AND **stored video files**
- For our use case: **we can feed .mkv files directly to VIOS** — no need for RTSP simulation!
- VIOS handles ingestion, recording, and provides playback

> [!TIP]
> **Key finding**: VSS VIOS can ingest stored video files directly. We may not need to set up an RTSP server at all! This simplifies the architecture significantly.

---

### 2. NVIDIA NemoClaw

#### What it is:
NemoClaw is NOT an agent framework you code against — it's a **security and management wrapper** around the OpenClaw agent platform. It provides:
- Sandboxed execution environment
- Privacy routing for inference
- Policy-based security controls
- Agent lifecycle management

#### Architecture:
```
Your Agent Logic (OpenClaw)
        ↓
NemoClaw Blueprint (security policies, inference routing)
        ↓
OpenShell Runtime (kernel-level sandboxing)
        ↓
Local Nemotron NIM (inference)
```

#### How we use it:
1. **NemoClaw wraps our producer agents** — each agent runs in a secure sandbox
2. **OpenShell enforces policies** — e.g., agents can only access specific video files, can only call the local Nemotron endpoint
3. **Privacy Router** — all inference stays local (no data leaving the device)

#### Agent Development:
- Agents are built using **OpenClaw** (the agent framework)
- Custom skills defined via `SKILL.md` files (natural language instructions)
- Tools are Python functions exposed to the agent
- NemoClaw manages deployment and security

#### Setup:
- CLI-based: `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash`
- Guided onboarding: `nemoclaw onboard`
- Configure inference to point to local Nemotron Lightning NIM
- Lightweight: ~2.4GB sandbox image + Node.js 22+

---

### 3. NVIDIA OpenShell

#### What it is:
Kernel-level security runtime for AI agents. Uses:
- **seccomp** — restricts system calls
- **Landlock LSM** — restricts filesystem access
- **Network namespaces** — controls network egress

#### How we use it (for the bounty):
We define a security policy for each producer agent:

```yaml
# Example: Fan Producer Agent Policy
name: fan-producer-policy
filesystem:
  allow:
    - /data/SoccerNet/**  # Read-only access to match data
    - /output/fan/**      # Write access to output directory
  deny:
    - /data/SoccerNet/*/Labels-*  # Other matches (privacy)
network:
  allow:
    - localhost:8000  # Local Nemotron NIM only
  deny:
    - "*"  # Block all external network access
```

#### Why this matters for judging:
- Shows **responsible AI** — agents can't exfiltrate video data
- Shows **NVIDIA ecosystem depth** — VSS + NemoClaw + OpenShell
- Directly eligible for the **NemoClaw + OpenShell bounty** (Do track)

---

### 4. Nemotron 3.5 Lightning NIM

#### Specs:
- **Architecture**: 30B-A3B MoE (only 3B parameters active per token — FAST)
- **Context window**: 1M tokens
- **Memory**: ~20GB (4-bit quant) or ~33GB (8-bit quant)
- **API**: OpenAI-compatible (drop-in replacement)
- **Optimized for DGX Spark** specifically

#### Deployment:
```bash
docker run --gpus all \
  -e NGC_API_KEY="$NGC_API_KEY" \
  -v ~/.cache/nim:/opt/nim/.cache \
  -p 8000:8000 \
  --shm-size=16GB \
  nvcr.io/nim/nvidia/nemotron-3.5-lightning-30b-a3b:latest
```

#### Why Lightning:
- **Bounty eligible**: "Best Use of Nemotron Lightning" bounty
- **Fast**: 30% faster than comparable models at same accuracy
- **Efficient**: MoE means low compute per token
- **Agent-optimized**: Trained on agentic task traces

---

## Memory Budget on GN100 (128GB unified)

| Component | Estimated Memory |
|-----------|-----------------|
| Nemotron Lightning 3.5 (4-bit) | ~20 GB |
| VSS: Cosmos Reason VLM (8B) | ~12 GB |
| VSS: Nemotron Nano 9B (VSS agent) | ~10 GB |
| VSS: Embedding model | ~4 GB |
| VSS: Elasticsearch + Milvus | ~4 GB |
| NemoClaw + OpenShell | ~3 GB |
| Video buffer + processing | ~10 GB |
| OS + system overhead | ~8 GB |
| **Total estimated** | **~71 GB / 128 GB** |
| **Headroom** | **~57 GB** ✅ |

> [!NOTE]
> We have plenty of memory. The GN100's 128GB unified memory is more than enough to run the full stack simultaneously. This IS the "Spark Story."

---

## Key Architecture Decisions from Research

### Decision 1: VSS for video + Annotations for events ✅
VSS provides visual understanding; annotations provide reliable event detection. They complement each other.

### Decision 2: NemoClaw as agent wrapper, not agent framework
NemoClaw wraps our agents for security. The actual agent logic uses OpenClaw or can be custom Python calling Nemotron Lightning.

### Decision 3: OpenShell for security policies ✅
Adds security layer + bounty eligibility. Simple YAML policies.

### Decision 4: No RTSP needed!
VSS VIOS can ingest stored .mkv files directly. Simpler than setting up RTSP.

### Decision 5: Nemotron Lightning as primary LLM
Fast, efficient, bounty-eligible, agent-optimized, runs well on Spark.

---

## Open Questions After Research

> [!IMPORTANT]
> 1. **NGC API Key**: Does your team already have an NVIDIA NGC account? You need an API key for pulling containers. Check if hackathon organizers provided one.
> 2. **NVIDIA AI Enterprise License**: VSS requires this for local NIM deployment. Hackathon participants may have been given temporary access — check with organizers.
> 3. **DGX OS version**: The GN100 should be running DGX OS 7.4.0+. Can your teammate verify with `cat /etc/os-release`?
