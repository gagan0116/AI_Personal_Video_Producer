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
    this.presetSelect = this.container.querySelector(".agent-preset-select");
    this.inputEdit = this.container.querySelector(".agent-input-edit");
    this.btnToggleEdit = this.container.querySelector(".btn-toggle-edit");

    this.outputs = [];
    this.isCustomMode = false;

    this._bindEvents();
  }

  _bindEvents() {
    // Preset dropdown change
    if (this.presetSelect) {
      this.presetSelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val === "__custom__") {
          this._enableCustomInput(true);
        } else {
          this._updateConfig({ preset: val, custom_input: val });
        }
      });
    }

    // Toggle custom edit button
    if (this.btnToggleEdit) {
      this.btnToggleEdit.addEventListener("click", () => {
        this._enableCustomInput(!this.isCustomMode);
      });
    }

    // Custom input submit on Enter or blur
    if (this.inputEdit) {
      this.inputEdit.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          const val = this.inputEdit.value.trim();
          if (val) {
            this._updateConfig({ custom_input: val, preset: val });
            this._enableCustomInput(false);
          }
        }
      });
    }
  }

  _enableCustomInput(enable) {
    this.isCustomMode = enable;
    if (enable) {
      if (this.presetSelect) this.presetSelect.style.display = "none";
      if (this.inputEdit) {
        this.inputEdit.style.display = "block";
        this.inputEdit.focus();
        this.inputEdit.select();
      }
    } else {
      if (this.presetSelect) this.presetSelect.style.display = "block";
      if (this.inputEdit) this.inputEdit.style.display = "none";
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
    if (!this.presetSelect || !matchInfo) return;

    if (this.agentId === "fan") {
      const starPlayers = matchInfo.star_players || ["Neymar", "Messi", "Suarez"];
      this.presetSelect.innerHTML = "";
      starPlayers.forEach(player => {
        const opt = document.createElement("option");
        opt.value = player;
        opt.textContent = `⭐ Track ${player}`;
        this.presetSelect.appendChild(opt);
      });
      const customOpt = document.createElement("option");
      customOpt.value = "__custom__";
      customOpt.textContent = "✏️ Custom Player...";
      this.presetSelect.appendChild(customOpt);

      if (starPlayers.length > 0) {
        this.presetSelect.value = starPlayers[0];
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

    card.innerHTML = `
      <div class="card-top-row">
        <span class="card-time-badge">⏱ ${output.game_time}</span>
        <span class="card-type-tag">${output.event_type}</span>
      </div>
      <div class="card-caption">${this._escapeHtml(output.caption)}</div>
      <div class="card-actions-row">
        <button class="btn-play-clip" data-clip-url="${output.clip_url || ''}">
          <span>▶</span> Play Clip
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
        `${output.agent_type.toUpperCase()} PRODUCER — ${output.game_time}`,
        output.caption,
        output.event_type
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
    this.feedElement.innerHTML = `
      <div class="feed-empty-state">
        <div class="empty-icon">⚡</div>
        <p>Awaiting match events. Producer will generate custom clips as play unfolds.</p>
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
