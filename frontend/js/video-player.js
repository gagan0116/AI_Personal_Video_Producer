/**
 * Video Player Modal Component
 * Displays broadcast video clips rendered by FFmpeg on the GN100 DGX Spark.
 */

class VideoPlayerModal {
  constructor() {
    this.overlay = document.getElementById("videoModal");
    this.videoElem = document.getElementById("modalVideoPlayer");
    this.titleElem = document.getElementById("modalTitle");
    this.captionElem = document.getElementById("modalCaption");
    this.metaTimeElem = document.getElementById("modalMetaTime");
    this.metaAgentElem = document.getElementById("modalMetaAgent");
    this.closeBtn = document.getElementById("btnCloseModal");

    if (this.closeBtn) {
      this.closeBtn.addEventListener("click", () => this.close());
    }

    if (this.overlay) {
      this.overlay.addEventListener("click", (e) => {
        if (e.target === this.overlay) {
          this.close();
        }
      });
    }

    // Escape key listener
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.isOpen()) {
        this.close();
      }
    });
  }

  isOpen() {
    return this.overlay && this.overlay.classList.contains("open");
  }

  playClip(clipUrl, title, caption, eventType, gameTime, agentId) {
    if (!this.overlay || !this.videoElem) return;

    this.titleElem.textContent = title || `${eventType} Highlight`;
    this.captionElem.textContent = caption || "";
    if (this.metaTimeElem) this.metaTimeElem.textContent = `⏱ ${gameTime || ''}`;
    if (this.metaAgentElem) {
      const agentNames = {
        fan: "👤 Fan Producer Stream",
        coach: "📋 Tactical Breakdown Stream",
        social: "📱 Social Media Highlight"
      };
      this.metaAgentElem.textContent = agentNames[agentId] || `${agentId} Producer`;
    }
    
    this.videoElem.src = clipUrl;
    this.videoElem.load();
    this.overlay.classList.add("open");

    this.videoElem.play().catch(err => {
      console.log("[VideoPlayerModal] Autoplay prevented, user interaction required:", err);
    });
  }

  close() {
    if (!this.overlay) return;
    if (this.videoElem) {
      this.videoElem.pause();
      this.videoElem.src = "";
    }
    this.overlay.classList.remove("open");
  }
}

window.VideoPlayerModal = VideoPlayerModal;
