/**
 * Agent Panel Component
 * Manages an individual Producer Agent column (Fan, Coach, Social) on the dashboard.
 */

class AgentPanel {
  constructor(agentId, containerElement, videoPlayer) {
    this.agentId = agentId;
    this.container = containerElement;
    this.videoPlayer = videoPlayer;
    this.feedElement = this.container.querySelector(".panel-feed");
    this.counterElement = this.container.querySelector(".clip-counter-pill");
    this.textInput = this.container.querySelector(".agent-text-input");
    this.btnSetPrompt = this.container.querySelector(".btn-set-prompt");
    this.presetChipsContainer = this.container.querySelector(".preset-chips-row");

    this.outputs = [];
    this._bindEvents();
  }

  _bindEvents() {
    // 1. Submit prompt via Button
    if (this.btnSetPrompt) {
      this.btnSetPrompt.addEventListener("click", () => {
        this._submitPrompt();
      });
    }

    // 2. Submit prompt via Enter key in the visible input box
    if (this.textInput) {
      this.textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          this._submitPrompt();
        }
      });
    }

    // 3. Quick preset chips click
    if (this.presetChipsContainer) {
      this.presetChipsContainer.addEventListener("click", (e) => {
        const chip = e.target.closest(".preset-chip");
        if (!chip) return;

        const val = chip.getAttribute("data-val");
        if (val) {
          // Highlight active chip
          this.presetChipsContainer.querySelectorAll(".preset-chip").forEach(c => c.classList.remove("active"));
          chip.classList.add("active");

          // Update input field
          if (this.textInput) {
            this.textInput.value = val;
          }

          // Trigger backend update
          this._updateConfig({ custom_input: val, preset: val });
        }
      });
    }
  }

  _submitPrompt() {
    if (!this.textInput) return;
    const val = this.textInput.value.trim();
    if (val) {
      // Deactivate chips if custom text
      if (this.presetChipsContainer) {
        this.presetChipsContainer.querySelectorAll(".preset-chip").forEach(c => {
          if (c.getAttribute("data-val") === val) {
            c.classList.add("active");
          } else {
            c.classList.remove("active");
          }
        });
      }

      // Visual feedback on the button
      if (this.btnSetPrompt) {
        const originalText = this.btnSetPrompt.innerHTML;
        this.btnSetPrompt.innerHTML = "<span>✓ Saved</span>";
        setTimeout(() => {
          this.btnSetPrompt.innerHTML = originalText;
        }, 1200);
      }

      this._updateConfig({ custom_input: val, preset: val });
    }
  }

  async _updateConfig(payload) {
    try {
      const resp = await fetch(`/api/agents/${this.agentId}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      console.log(`[AgentPanel ${this.agentId}] Config updated:`, data);
    } catch (e) {
      console.error(`[AgentPanel ${this.agentId}] Error updating config:`, e);
    }
  }

  updatePresetsForMatch(matchInfo) {
    if (!this.presetChipsContainer || !matchInfo) return;

    if (this.agentId === "fan") {
      const starPlayers = matchInfo.star_players || ["Neymar", "Messi", "Suarez"];
      this.presetChipsContainer.innerHTML = '<span class="chip-label">Quick:</span>';

      starPlayers.slice(0, 4).forEach((player, idx) => {
        const chip = document.createElement("button");
        chip.className = `preset-chip ${idx === 0 ? "active" : ""}`;
        chip.setAttribute("data-val", player);
        chip.textContent = `⭐ ${player}`;
        this.presetChipsContainer.appendChild(chip);
      });

      if (starPlayers.length > 0 && this.textInput) {
        this.textInput.value = starPlayers[0];
      }
    }
  }

  addOutputCard(output, isPrepend = true) {
    // Avoid duplicates
    if (this.outputs.some(o => o.output_id === output.output_id)) {
      return;
    }

    this.outputs.push(output);
    this._updateCounter();

    // Remove empty placeholder state if present
    const emptyState = this.feedElement.querySelector(".feed-empty-state");
    if (emptyState) {
      emptyState.style.display = "none";
    }

    const card = document.createElement("div");
    card.className = "output-card";
    card.id = `card_${output.output_id}`;

    const playersStr = output.players && output.players.length > 0 
      ? `• ${output.players.join(", ")}`
      : "";

    const reasoningBlock = output.reasoning 
      ? `<div class="card-reasoning-quote">🧠 ${this._escapeHtml(output.reasoning)}</div>`
      : "";

    card.innerHTML = `
      <div class="card-top-row">
        <span class="card-time-badge">⏱ ${output.game_time}</span>
        <span class="card-type-tag">${output.event_type}</span>
      </div>
      <div class="card-caption">${this._escapeHtml(output.caption)}</div>
      ${reasoningBlock}
      <div class="card-actions-row">
        <button class="btn-play-clip" data-clip-url="${output.clip_url || ''}">
          <span>▶</span> Watch 10s Clip
        </button>
        <span class="card-intel-tag">${playersStr}</span>
      </div>
    `;

    // Bind Play Button
    const playBtn = card.querySelector(".btn-play-clip");
    playBtn.addEventListener("click", () => {
      const url = output.clip_url || `/api/clips/${output.agent_id}/clip_${output.event_id}.mp4`;
      this.videoPlayer.playClip(
        url,
        `${output.agent_type.toUpperCase()} PRODUCER • ${output.game_time}`,
        output.caption,
        output.event_type,
        output.game_time,
        this.agentId
      );
    });

    if (isPrepend && this.feedElement.firstChild) {
      this.feedElement.insertBefore(card, this.feedElement.firstChild);
    } else {
      this.feedElement.appendChild(card);
    }
  }

  clearFeed() {
    this.outputs = [];
    this._updateCounter();
    const icons = {
      fan: { icon: "👤", class: "fan-glow-icon", title: "Autonomous Fan Producer Ready", desc: "Scanning ASR commentary, visual detections & touches for your player." },
      coach: { icon: "📋", class: "coach-glow-icon", title: "Tactical Analyst Agent Armed", desc: "Isolating structural vulnerabilities, broadcast replays, and set-piece executions." },
      social: { icon: "📱", class: "social-glow-icon", title: "Social Media Producer Ready", desc: "Curating high-virality broadcast moments with auto-generated hashtags & captions." }
    };
    const agentMeta = icons[this.agentId] || icons.fan;

    this.feedElement.innerHTML = `
      <div class="feed-empty-state">
        <div class="empty-icon-glow ${agentMeta.class}">${agentMeta.icon}</div>
        <h4>${agentMeta.title}</h4>
        <p>${agentMeta.desc}</p>
      </div>
    `;
  }

  _updateCounter() {
    if (this.counterElement) {
      this.counterElement.textContent = `${this.outputs.length} Clips`;
    }
  }

  _escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

window.AgentPanel = AgentPanel;
