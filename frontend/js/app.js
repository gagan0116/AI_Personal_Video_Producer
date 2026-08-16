/**
 * Main Application Orchestrator
 * Connects UI Controls, SSE real-time stream, Agent Panels, and Video Player.
 */

document.addEventListener("DOMContentLoaded", () => {
  const app = new SportsProducerApp();
  app.init();
});

class SportsProducerApp {
  constructor() {
    this.sseClient = new SSEClient("/api/events/stream");
    this.videoPlayer = new VideoPlayerModal();
    this.agentPanels = new Map();

    // DOM Elements
    this.matchSelect = document.getElementById("matchSelect");
    this.speedSelect = document.getElementById("speedSelect");
    this.btnStart = document.getElementById("btnStart");
    this.btnPause = document.getElementById("btnPause");
    this.btnStop = document.getElementById("btnStop");
    this.statusBadge = document.getElementById("statusBadge");
    this.statusText = document.getElementById("statusText");
    
    this.scoreTeams = document.getElementById("scoreTeams");
    this.scoreVal = document.getElementById("scoreVal");
    this.matchClock = document.getElementById("matchClock");
    this.progressBar = document.getElementById("progressBarFill");
    this.headlineTicker = document.getElementById("headlineTicker");
    this.timelineChips = document.getElementById("timelineChips");

    this.matches = [];
    this.currentMatchId = "barcelona_vs_paris_sg";
    this.matchState = { status: "idle", is_active: false };
  }

  async init() {
    this._initAgentPanels();
    this._bindControls();
    await this._loadMatches();
    this._initSSE();
  }

  _initAgentPanels() {
    const fanElem = document.getElementById("fanPanel");
    const coachElem = document.getElementById("coachPanel");
    const socialElem = document.getElementById("socialPanel");

    if (fanElem) this.agentPanels.set("fan", new AgentPanel("fan", fanElem, this.videoPlayer));
    if (coachElem) this.agentPanels.set("coach", new AgentPanel("coach", coachElem, this.videoPlayer));
    if (socialElem) this.agentPanels.set("social", new AgentPanel("social", socialElem, this.videoPlayer));
  }

  _bindControls() {
    // Start Match
    if (this.btnStart) {
      this.btnStart.addEventListener("click", async () => {
        const matchId = this.matchSelect.value;
        const speed = parseFloat(this.speedSelect.value) || 6.0;
        
        // Reset panels
        this.agentPanels.forEach(panel => panel.clearFeed());
        this.timelineChips.innerHTML = "";

        this.btnStart.disabled = true;
        try {
          const resp = await fetch("/api/match/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ match_id: matchId, speed_multiplier: speed })
          });
          const res = await resp.json();
          console.log("[App] Match started:", res);
        } catch (e) {
          console.error("[App] Start match error:", e);
        } finally {
          this.btnStart.disabled = false;
        }
      });
    }

    // Pause Match
    if (this.btnPause) {
      this.btnPause.addEventListener("click", async () => {
        const isPaused = this.matchState.status === "paused";
        const endpoint = isPaused ? "/api/match/resume" : "/api/match/pause";
        await fetch(endpoint, { method: "POST" });
      });
    }

    // Stop Match
    if (this.btnStop) {
      this.btnStop.addEventListener("click", async () => {
        await fetch("/api/match/stop", { method: "POST" });
      });
    }

    // Match Selector change
    if (this.matchSelect) {
      this.matchSelect.addEventListener("change", (e) => {
        this.currentMatchId = e.target.value;
        const matchObj = this.matches.find(m => m.match_id === this.currentMatchId);
        if (matchObj) {
          this._updateScoreboardHeader(matchObj);
          this.agentPanels.forEach(p => p.updatePresetsForMatch(matchObj));
        }
      });
    }
  }

  async _loadMatches() {
    try {
      const resp = await fetch("/api/matches");
      this.matches = await resp.json();
      
      if (this.matchSelect) {
        this.matchSelect.innerHTML = "";
        this.matches.forEach(m => {
          const opt = document.createElement("option");
          opt.value = m.match_id;
          opt.textContent = `${m.league} — ${m.display_title}`;
          this.matchSelect.appendChild(opt);
        });
      }

      const defaultMatch = this.matches[0];
      if (defaultMatch) {
        this._updateScoreboardHeader(defaultMatch);
        this.agentPanels.forEach(p => p.updatePresetsForMatch(defaultMatch));
      }
    } catch (e) {
      console.error("[App] Failed to load matches:", e);
    }
  }

  _updateScoreboardHeader(matchObj) {
    if (this.scoreTeams) {
      this.scoreTeams.textContent = `${matchObj.home_team} vs ${matchObj.away_team}`;
    }
    if (this.scoreVal) {
      this.scoreVal.textContent = matchObj.score || "0 - 0";
    }
  }

  _initSSE() {
    this.sseClient.connect();

    this.sseClient.on("connection:open", () => {
      this._updateStatusUI("connected", "DGX Spark Ready");
    });

    this.sseClient.on("system:init", (data) => {
      if (data && data.state) {
        this._handleStateUpdate(data.state);
      }
      if (data && data.existing_outputs) {
        data.existing_outputs.forEach(out => {
          const panel = this.agentPanels.get(out.agent_id);
          if (panel) panel.addOutputCard(out, false);
        });
      }
    });

    this.sseClient.on("match:status", (state) => {
      this._handleStateUpdate(state);
    });

    this.sseClient.on("match:tick", (tickData) => {
      if (this.matchClock) {
        this.matchClock.textContent = `⏱ ${tickData.game_time}`;
      }
      if (this.progressBar) {
        this.progressBar.style.width = `${tickData.progress || 0}%`;
      }
    });

    this.sseClient.on("match:events", (eventData) => {
      if (eventData && eventData.events) {
        eventData.events.forEach(evt => this._addTimelineChip(evt));
      }
    });

    this.sseClient.on("agent:output", (outputData) => {
      const panel = this.agentPanels.get(outputData.agent_id);
      if (panel) {
        panel.addOutputCard(outputData, true);
      }
      if (this.headlineTicker) {
        this.headlineTicker.textContent = `⚡ [${outputData.agent_type.toUpperCase()}] ${outputData.caption}`;
      }
    });

    this.sseClient.on("match:halftime", (data) => {
      if (this.headlineTicker) {
        this.headlineTicker.textContent = "⏸️ Halftime interval reached. Resuming second half shortly...";
      }
    });

    this.sseClient.on("match:complete", (data) => {
      this._updateStatusUI("completed", "Match Completed");
      if (this.headlineTicker) {
        this.headlineTicker.textContent = "🏁 Full Time! All personalized highlights generated.";
      }
    });
  }

  _handleStateUpdate(state) {
    this.matchState = state;
    const isRunning = state.status === "running";
    const isPaused = state.status === "paused";

    if (this.btnStart) this.btnStart.style.display = isRunning || isPaused ? "none" : "inline-flex";
    if (this.btnPause) {
      this.btnPause.style.display = isRunning || isPaused ? "inline-flex" : "none";
      this.btnPause.textContent = isPaused ? "▶ Resume" : "⏸ Pause";
    }
    if (this.btnStop) this.btnStop.style.display = isRunning || isPaused ? "inline-flex" : "none";

    if (this.matchClock && state.current_game_time_display) {
      this.matchClock.textContent = `⏱ ${state.current_game_time_display}`;
    }
    if (this.progressBar && state.progress_percentage !== undefined) {
      this.progressBar.style.width = `${state.progress_percentage}%`;
    }
    if (this.headlineTicker && state.latest_event_headline) {
      this.headlineTicker.textContent = state.latest_event_headline;
    }

    if (isRunning) {
      this._updateStatusUI("active", `Live • Half ${state.current_half}`);
    } else if (isPaused) {
      this._updateStatusUI("paused", "Paused");
    } else if (state.status === "completed") {
      this._updateStatusUI("completed", "Completed");
    } else {
      this._updateStatusUI("idle", "Standby");
    }
  }

  _updateStatusUI(type, text) {
    if (!this.statusBadge || !this.statusText) return;
    this.statusText.textContent = text;
    this.statusBadge.className = `status-badge ${type === "active" ? "active" : ""}`;
  }

  _addTimelineChip(event) {
    if (!this.timelineChips) return;
    const chip = document.createElement("div");
    chip.className = `event-chip ${event.event_type === "Goal" ? "goal" : ""}`;
    chip.innerHTML = `
      <span class="chip-time">${event.game_time}</span>
      <span class="chip-type">${event.event_type} (${event.team})</span>
    `;
    this.timelineChips.appendChild(chip);
    this.timelineChips.scrollLeft = this.timelineChips.scrollWidth;
  }
}
