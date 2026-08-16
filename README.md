# 🏟️ Personal AI Sports Producer

> **NVIDIA Spark Hack Series — Seattle**
> **Track: See + Do** (Perception + Autonomous Multi-Agent Action)
> **Hardware: Acer Veriton GN100 (DGX Spark)** — Grace Blackwell GB10 • 128GB Unified Memory

---

## 🎯 The Problem

Every sports fan, coach, and media team watches the **same broadcast** — but they each care about completely different things:

| Audience | What They Care About |
|---|---|
| **A fan of Neymar** | Every touch, shot, foul drawn, and celebration by their favorite player |
| **A tactical coach** | Defensive breakdowns, pressing triggers, offside traps, set-piece execution |
| **A social media team** | The most viral, emotionally explosive moments — ready to post instantly |

Today, producing personalized broadcast outputs requires **separate human production crews** watching the same match. No tool exists that autonomously generates multiple tailored broadcast streams from a single video source.

---

## 🚀 The Solution

**One Acer GN100 DGX Spark continuously understands a soccer match and empowers three autonomous AI producer agents to concurrently generate personalized broadcast outputs — entirely on-device.**

```
                     ┌─────────────────────────────────────┐
                     │   SoccerNet Match Video (.mkv)      │
                     │   + Annotations + ASR Commentary     │
                     └───────────────┬─────────────────────┘
                                     │
                     ┌───────────────▼─────────────────────┐
                     │      NVIDIA VSS Pipeline            │
                     │   Dense Captioning • Video Q&A      │
                     │   Cosmos Reason VLM • Search         │
                     └───────────────┬─────────────────────┘
                                     │
                     ┌───────────────▼─────────────────────┐
                     │      Multi-Modal Event Fusion       │
                     │  Actions + Cameras + ASR + VLM      │
                     │  → Unified FusedEvent stream        │
                     └───┬───────────┬─────────────┬───────┘
                         │           │             │
              ┌──────────▼──┐ ┌─────▼──────┐ ┌────▼─────────┐
              │ 👤 FAN      │ │ 📋 COACH   │ │ 📱 SOCIAL    │
              │ PRODUCER    │ │ PRODUCER   │ │ PRODUCER     │
              │             │ │            │ │              │
              │ NemoClaw    │ │ NemoClaw   │ │ NemoClaw     │
              │ + OpenShell │ │ + OpenShell│ │ + OpenShell  │
              │ Sandbox     │ │ Sandbox    │ │ Sandbox      │
              └──────┬──────┘ └─────┬──────┘ └──────┬───────┘
                     │              │               │
                     ▼              ▼               ▼
              ┌──────────────────────────────────────────────┐
              │  FFmpeg Clip Extraction + LLM Captioning     │
              └──────────────────┬───────────────────────────┘
                                 │
              ┌──────────────────▼───────────────────────────┐
              │         FastAPI + SSE Live Dashboard         │
              │        http://localhost:8088                  │
              └──────────────────────────────────────────────┘
```

---

## 👥 The Three Autonomous Producer Agents

Each agent is an autonomous long-running NemoClaw agent with its own persona, reasoning strategy, and output style. All three run concurrently on the same fused event stream but produce completely different results.

| Agent | Focus | Live Input (User-Configurable) | Output |
|---|---|---|---|
| 👤 **Fan Producer** | Tracks a designated star player across all match events | Player name text prompt (e.g., `Neymar`, `Messi`, `Cavani`) — changeable mid-match | Personalized highlight clips of key touches, fouls drawn, shots, goals, and emotional reactions with energetic fan commentary |
| 📋 **Tactical Coach Producer** | Analyzes structural & tactical moments in the match | Tactical concept prompt (e.g., `Defensive breakdowns`, `Offside traps`, `Set pieces`) | Clinical analytical clips dissecting formation shape, pressing triggers, transitional play, and set-piece execution |
| 📱 **Social Media Producer** | Curates the most viral, high-engagement moments | Curation goal prompt (e.g., `Top goals`, `Red cards & VAR`, `Celebrations`) | Short-form highlight packages with ready-to-post social copy, emojis, and hashtags |

### Mid-Match Reconfiguration
Users can type a new player name, tactical concept, or curation goal into the live prompt box on the dashboard at any time — the agent pivots its reasoning immediately for the next event window.

---

## 🏗️ System Architecture

### End-to-End Pipeline (Per 5-Minute Game Window)

```
1. ANNOTATIONS          Load SoccerNet Labels-v2.json (17 action classes),
                        Labels-cameras.json (replays, camera types),
                        Whisper ASR transcripts (player name extraction)

2. NVIDIA VSS           Dense captioning via Cosmos Reason VLM (8B)
                        Video Q&A via vss-ask-video skill
                        Archive search via vss-search-archive skill

3. EVENT FUSION         Merge all sources into FusedEvent objects:
                        action + camera + ASR + VLM caption + importance score

4. AGENT DISPATCH       Fan-out fused events to all 3 NemoClaw agents (parallel)

5. LLM REASONING        Each agent sends persona-specific system prompt +
                        event context to Nemotron 35B MoE for selection & captioning

6. CLIP EXTRACTION      FFmpeg cuts ±5s broadcast clip around each selected event

7. SSE BROADCAST        Agent output (clip + caption + reasoning) streams
                        to the live dashboard in real-time
```

### FusedEvent Data Model
Each event flowing through the system carries multi-modal context:

```json
{
  "event_id": "evt_014",
  "half": 1,
  "game_time": "1 - 14:30",
  "timestamp_ms": 870000,
  "event_type": "Foul",
  "team": "away",
  "visibility": "visible",
  "camera_type": "Main camera center",
  "is_replay": false,
  "replay_count": 1,
  "commentary_text": "Neymar is brought down by the defender...",
  "players_mentioned": ["Neymar"],
  "vss_description": "Player tackled near midfield, referee signals free-kick",
  "importance_score": 0.6,
  "source_file": "data/SoccerNet/.../1_224p.mkv"
}
```

### Importance Scoring Algorithm
Events are ranked using a composite heuristic that reflects broadcast-level editorial judgment:

| Event Type | Base Score | Bonuses |
|---|---|---|
| Goal | 1.0 | — |
| Penalty | 0.95 | — |
| Red Card | 0.9 | — |
| Shot on Target | 0.7 | +0.1 per replay (max +0.3) |
| Foul / Free-kick | 0.35–0.40 | +0.1 if commentary contains excitement keywords |
| Corner / Offside | 0.30–0.35 | — |
| Throw-in / Kick-off | 0.05–0.15 | — |

---

## ⚡ NVIDIA Ecosystem Utilization

### The Stack

| Layer | Component | NVIDIA Technology | Purpose |
|---|---|---|---|
| **Vision (See)** | Dense Captioning | NVIDIA VSS `vss-deploy-dense-captioning` | Frame-level visual descriptions of match segments |
| **Vision (See)** | Video Q&A | NVIDIA VSS `vss-ask-video` | Agents ask questions about specific timestamps |
| **Vision (See)** | Video Search | NVIDIA VSS `vss-search-archive` | Natural language search over processed video |
| **Vision (See)** | VLM | Cosmos 3 Nano Reasoner (8B) via VSS | Multi-modal video understanding backbone |
| **Vision (See)** | Embeddings | Cosmos Embed via VSS | Semantic video embeddings for search |
| **Vision (See)** | Video IO | VIOS via VSS | Video ingestion and playback |
| **Agent LLM (Do)** | Reasoning | NVIDIA Qwen3.6-35B-A3B-NVFP4 (MoE) | All 3 producer agents: event selection, captioning, reasoning |
| **Agent Framework (Do)** | Orchestration | NVIDIA NemoClaw Blueprint | Multi-agent coordination and lifecycle |
| **Agent Security (Do)** | Sandboxing | NVIDIA OpenShell | Kernel-level Landlock + seccomp policies per agent |
| **Agent Security (Do)** | Privacy Routing | NemoClaw Privacy Router | Blocks all external network — local inference only |
| **Hardware** | Compute | Acer GN100 (DGX Spark GB10) | 128GB unified memory, zero CPU↔GPU copy overhead |

**NVIDIA Components: 11 out of 19 total stack elements** ✅

### The "Spark Story"

> *"We use the GN100's 128GB unified memory to simultaneously run the NVIDIA VSS video understanding pipeline (Cosmos VLM + embeddings), three autonomous NemoClaw producer agents powered by the Nemotron 35B MoE LLM, and real-time FFmpeg clip extraction — all locally with zero cloud dependency.*
>
> *No game footage leaves the device, ensuring broadcast content rights protection. The unified memory architecture eliminates GPU↔CPU transfers, enabling sub-second latency from event detection to personalized clip delivery.*
>
> *This is a use case that ONLY works on the Spark — traditional hardware cannot fit this many models in memory simultaneously while maintaining real-time multi-agent orchestration."*

### Memory Budget

| Component | Estimated Memory |
|---|---|
| Nemotron 35B MoE (NVFP4 quantized) | ~20 GB |
| Cosmos Reason VLM (8B) via VSS | ~12 GB |
| Cosmos Embed + Search Indexes | ~6 GB |
| NemoClaw + OpenShell Containers | ~3 GB |
| Video Buffer + FFmpeg | ~10 GB |
| OS + System | ~8 GB |
| **Total** | **~59 GB** |
| **Available** | **128 GB** |
| **Headroom** | **69 GB (54%)** ✅ |

---

## 🔒 Security Architecture (OpenShell)

Each producer agent runs inside an **NVIDIA OpenShell** sandbox with strict kernel-level policies:

```yaml
# Applied to all 3 producer agents
sandbox:
  filesystem:
    read_allow:  ["/data/SoccerNet/**", "/app/**"]
    write_allow: ["/output/{agent_id}/**"]
    deny:        ["/etc/**", "/root/**"]
  network:
    allow:       ["localhost:8000", "localhost:8010"]
    deny:        ["*"]  # Block ALL external network
  process:
    allow:       ["python3", "ffmpeg"]
    deny:        ["bash", "curl"]
```

**Why this matters for judges:** No game footage can leave the device. Each agent can only write to its own output directory. Agents can only call the local LLM — no cloud API leakage. This ensures content rights protection — critical for real-world sports broadcasting.

---

## 📦 Dataset: SoccerNet

We use the [SoccerNet](https://www.soccer-net.org/) open research dataset with 5 pre-downloaded broadcast matches:

| # | Match | Score | League | Notes |
|---|---|---|---|---|
| 1 | **Barcelona 6 - 1 Paris SG** | 6-1 | UEFA Champions League | 🌟 **Hero Demo Match** (The Remontada) |
| 2 | Leicester City vs Arsenal | 2-5 | English Premier League | High-scoring EPL clash |
| 3 | Chelsea vs Swansea City | 2-2 | English Premier League | Balanced draw |
| 4 | Real Madrid vs Las Palmas | 3-3 | Spain La Liga | End-to-end drama |
| 5 | Real Madrid vs Getafe | 7-3 | Spain La Liga | Goal-fest |

Each match includes:
- **Video**: `1_224p.mkv` / `2_224p.mkv` (broadcast footage per half)
- **Action Annotations**: `Labels-v2.json` — 17 event classes with millisecond timestamps
- **Camera Annotations**: `Labels-cameras.json` — camera types, replay markers, original event links
- **ASR Commentary**: `echoes/whisper_v2_en/1_asr.json` — transcribed English broadcast commentary

---

## 🖥️ Frontend: Live Studio Dashboard

The dashboard is a dark-themed glassmorphic single-page application served directly from the GN100:

- **Match Control Deck**: Match selector, playback speed (4x–20x), Start/Pause/Stop controls
- **Broadcast Monitor**: Live score, match clock, progress bar, streaming commentary ticker
- **3-Column Producer Studio**: Each agent column shows:
  - 🎯 **Visible prompt input box** — type custom player names, tactical concepts, or social goals
  - ⚡ **Quick preset chips** — one-click presets for common configurations
  - 📋 **Live output feed** — highlight cards with captions, reasoning quotes, and `▶ Watch Clip` buttons
- **Interactive Video Player Modal**: Click any card to watch the 10s broadcast clip with AI-generated commentary
- **Multi-Modal Event Timeline**: Scrollable strip of live fused events with color-coded chips

### Technologies
- **HTML / CSS / JavaScript** — vanilla, no framework dependencies
- **SSE (Server-Sent Events)** via `EventSource` API for real-time streaming
- **Design**: Outfit + JetBrains Mono fonts, glassmorphism panels, NVIDIA green accents, agent-specific color identities, micro-animations

---

## 🚀 Getting Started on GN100 DGX Spark

### Prerequisites
- Acer Veriton GN100 (DGX OS 7.4+ / Ubuntu 22.04+)
- Docker & NVIDIA Container Toolkit
- SoccerNet dataset downloaded to `/home/acer01/personal-ai-sports-producer/data/SoccerNet`
- Nemotron 35B MoE model served via vLLM on port `8000`
- NVIDIA OpenShell container running

### Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/gagan0116/AI_Personal_Video_Producer.git
cd AI_Personal_Video_Producer

# 2. Run automated setup (creates venv, installs dependencies, creates output dirs)
chmod +x scripts/setup_gn100.sh scripts/start.sh
./scripts/setup_gn100.sh

# 3. Configure environment
cp .env.example .env
# Edit .env with your paths:
#   DATA_DIR=/home/acer01/personal-ai-sports-producer/data/SoccerNet
#   NEMOTRON_MODEL=nvidia/Qwen3.6-35B-A3B-NVFP4

# 4. Verify LLM connection
source venv/bin/activate
PYTHONPATH=. python scripts/test_nemotron.py

# 5. Run end-to-end pipeline test
PYTHONPATH=. python scripts/test_pipeline.py

# 6. Launch the Live Studio
./scripts/start.sh
```

Open your browser at **`http://localhost:8088`** to access the Live Studio Dashboard.

---

## 🧪 Verification & Automated Tests

```bash
# Unit test suite (8 tests)
pytest tests/

# End-to-end multi-agent pipeline verification
PYTHONPATH=. python scripts/test_pipeline.py

# LLM connection test
PYTHONPATH=. python scripts/test_nemotron.py
```

### Pipeline Test Output (Barcelona 6-1 PSG)
```
Loaded 288 action events, 1854 commentary segments.
Processing Window 1 (Minutes 0:00 - 5:00) with Producer Agents + Nemotron...
Processing Window 2 (Minutes 5:00 - 10:00)...

Total highlight clips produced by agents: 17

--- FAN PRODUCER (9 outputs) ---
  [1 - 02:27] Goal -> ⚽ GOAL! Neymar makes history with a stunning goal! 🔥

--- COACH PRODUCER (4 outputs) ---
  [1 - 02:27] Goal -> 📋 GOAL ANALYSIS: Defensive overload exploited in final third.

--- SOCIAL PRODUCER (4 outputs) ---
  [1 - 02:27] Goal -> 🚨 ABSOLUTE SCENES! UNREAL GOAL! The stadium is on fire! 💥⚽🔥
```

---

## 📁 Project Structure

```
AI_Video_Producer/
├── app/
│   ├── agents/               # Autonomous producer agents
│   │   ├── base_agent.py     # BaseAgent orchestration (LLM → VSS → Clip → SSE)
│   │   ├── fan_agent.py      # 👤 Personalized star player tracking
│   │   ├── coach_agent.py    # 📋 Tactical breakdown analysis
│   │   ├── social_agent.py   # 📱 Viral moment curation
│   │   └── llm_client.py     # Nemotron 35B MoE client (auto model discovery)
│   ├── api/                  # FastAPI REST + SSE endpoints
│   │   ├── routes.py         # Match control, agent config, clip streaming
│   │   └── sse.py            # SSE broadcast manager
│   ├── clips/
│   │   └── extractor.py      # Async FFmpeg clip extraction
│   ├── data/                 # Data ingestion layer
│   │   ├── annotation_loader.py  # SoccerNet JSON parsers
│   │   └── player_extractor.py   # ASR-based player identification
│   ├── engine/               # Match simulation engine
│   │   ├── match_engine.py   # Central orchestrator
│   │   ├── match_clock.py    # Accelerated game clock
│   │   ├── event_fusion.py   # Multi-modal event merger
│   │   └── importance.py     # Composite importance scoring
│   ├── models/               # Pydantic data models
│   │   ├── events.py         # FusedEvent, ActionEvent, CameraEvent
│   │   ├── agents.py         # AgentConfig, AgentOutput
│   │   └── match.py          # MatchInfo, MatchState
│   ├── vss/                  # NVIDIA VSS integration
│   │   ├── client.py         # VSS API client (dense captioning, Q&A, search)
│   │   └── mock_client.py    # Mock client for development
│   ├── config.py             # Pydantic settings (env vars)
│   └── main.py               # FastAPI lifespan + startup
├── frontend/
│   ├── index.html            # Studio dashboard
│   ├── css/styles.css        # Glassmorphic dark theme
│   └── js/                   # SSE client, agent panels, video player, app logic
├── config/
│   ├── nemoclaw-blueprint.yaml   # NemoClaw agent definitions
│   └── openshell-policy.yaml     # OpenShell security policies
├── scripts/
│   ├── setup_gn100.sh        # Automated GN100 setup
│   ├── start.sh              # Launch studio server
│   ├── test_nemotron.py      # LLM connection test
│   ├── test_pipeline.py      # End-to-end pipeline test
│   └── test_vss.py           # VSS integration test
├── tests/                    # Pytest unit tests (8 tests)
├── Dockerfile                # Container deployment
├── docker-compose.yml        # Multi-service orchestration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── README.md
```

---

## 🎬 Demo Script (3-5 Minutes)

1. **The Problem (30s):** *"Every viewer gets the same broadcast. But a Neymar fan, a defensive coach, and a social media editor care about completely different moments."*

2. **The Solution (15s):** *"We built an autonomous AI sports production studio that watches one match and produces three personalized broadcast streams — all running locally on the Acer GN100 DGX Spark."*

3. **Configure Agents (30s):**
   - Fan Producer → type `Neymar` in the prompt box
   - Tactical Coach → select `🛡️ Def Breakdown`
   - Social Producer → select `🔥 Top Goals`

4. **Start Live Production (15s):** Select Barcelona 6-1 PSG. Set speed to 6x. Click `▶ Produce Broadcast`.

5. **Watch Autonomous Output (90s):** As the match clock advances, all three columns autonomously populate with tailored clips, tactical analysis, and viral social posts — from the same video stream.

6. **Deep Dive (30s):** Click `▶ Watch Clip` on a Fan Producer card showing Neymar's goal. Show the inline broadcast clip, AI-generated caption, and LLM reasoning quote.

7. **Live Reconfiguration (15s):** Mid-match, type `Messi` in the Fan Producer prompt box and click Update. Show the agent pivoting immediately.

8. **Close (15s):** *"One match, three audiences, three personalized experiences — zero cloud dependency. All powered by NVIDIA on the Acer GN100 DGX Spark."*

---

## 🏆 Bounty Eligibility

| Bounty | Eligible | How |
|---|---|---|
| **Track Winner (See + Do)** | ✅ | VSS vision pipeline (See) + NemoClaw autonomous agents (Do) |
| **Best Use of NVIDIA Nemotron** | ✅ | Nemotron 35B MoE powers all 3 producer agents for structured JSON reasoning |
| **NVIDIA Developer Champions Choice** | ✅ | Novel sports AI application with deep ecosystem integration (11 NVIDIA components) |
| **Ascend Venture Potential** | ✅ | Real market problem (personalized sports broadcasting), scalable to any sport/league |

---

## 👨‍💻 Team

Built at the **NVIDIA Spark Hack Series — Seattle** (August 14–16, 2026)

---

## 📄 License

This project was built for the NVIDIA Spark Hack Series hackathon. SoccerNet data is used under research license.
