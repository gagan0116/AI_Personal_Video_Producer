/**
 * Server-Sent Events (SSE) Client
 * Connects to the GN100 DGX Spark backend and delivers live match ticks,
 * detected multi-modal events, and autonomous producer agent highlight cards.
 */

class SSEClient {
  constructor(endpoint = "/api/events/stream") {
    this.endpoint = endpoint;
    this.eventSource = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 8000;
  }

  connect() {
    if (this.eventSource) {
      this.eventSource.close();
    }

    try {
      this.eventSource = new EventSource(this.endpoint);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.emit("connection:open", { status: "connected" });
      };

      this.eventSource.onerror = (err) => {
        this.emit("connection:error", { error: err });
        this.eventSource.close();
        
        // Auto-reconnect with backoff
        const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts++), this.maxReconnectDelay);
        setTimeout(() => this.connect(), delay);
      };

      // General message receiver
      this.eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const eventType = payload.event || "message";
          let dataObj = payload.data;
          
          if (typeof dataObj === "string") {
            try {
              dataObj = JSON.parse(dataObj);
            } catch (e) {
              // String remains as is
            }
          }
          this.emit(eventType, dataObj);
        } catch (e) {
          console.warn("[SSEClient] Parse error:", e);
        }
      };

      // Native SSE named event listeners
      const knownEvents = [
        "system:init",
        "match:status",
        "match:tick",
        "match:events",
        "match:counts",
        "match:halftime",
        "match:complete",
        "agent:output",
        "agent:config_updated"
      ];

      knownEvents.forEach(evtName => {
        this.eventSource.addEventListener(evtName, (event) => {
          try {
            let dataObj = event.data;
            if (typeof dataObj === "string") {
              try {
                dataObj = JSON.parse(dataObj);
              } catch (e) {}
            }
            this.emit(evtName, dataObj);
          } catch (e) {
            console.warn(`[SSEClient] Error handling event ${evtName}:`, e);
          }
        });
      });

    } catch (e) {
      console.error("[SSEClient] Failed to initialize EventSource:", e);
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(cb => {
        try {
          cb(data);
        } catch (err) {
          console.error(`[SSEClient] Error in listener for ${event}:`, err);
        }
      });
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

window.SSEClient = SSEClient;
