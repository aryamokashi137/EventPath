import { useState, useEffect, useRef } from "react";
import { Bell, CheckCheck, Trash2, X, Activity, AlertTriangle, Layers, Calendar, Zap } from "lucide-react";

export default function NotificationCenter({ projectId }) {
  const [notifications, setNotifications] = useState(() => {
    try {
      const saved = localStorage.getItem("eventpath_notifications");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [isOpen, setIsOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState("ALL"); // ALL | ACTIVITIES | SYSTEM
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  // Persist notifications
  useEffect(() => {
    try {
      localStorage.setItem("eventpath_notifications", JSON.stringify(notifications.slice(0, 50)));
    } catch (err) {
      console.error("Failed to save notifications:", err);
    }
  }, [notifications]);

  // Establish WebSocket connection
  useEffect(() => {
    const wsUrl = `ws://${window.location.host}/api/v1/projects/${projectId || "all"}/ws`;
    
    // Determine backend host/port (default FastAPI port 8000 if dev server runs on 5173)
    const backendWsUrl = window.location.port === "5173" || window.location.port === "3000"
      ? `ws://localhost:8000/api/v1/projects/${projectId || "all"}/ws`
      : `ws://${window.location.host}/api/v1/projects/${projectId || "all"}/ws`;

    let socket;
    try {
      socket = new WebSocket(backendWsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "pong") return;

          const newNotif = {
            id: Date.now() + Math.random().toString(36).substring(2, 9),
            type: data.type || "ACTIVITY_MUTATION",
            event: data.event || data.type || "System Update",
            message: data.message || data.details?.name || "Workspace update received",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
            read: false,
            category: data.event?.includes("ACTIVITY") ? "ACTIVITIES" : "SYSTEM",
          };

          setNotifications((prev) => [newNotif, ...prev]);
        } catch (err) {
          console.error("WebSocket message parse error:", err);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
      };

      socket.onerror = () => {
        setIsConnected(false);
      };
    } catch {
      setIsConnected(false);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [projectId]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  const filteredNotifications = notifications.filter((n) => {
    if (activeFilter === "ALL") return true;
    return n.category === activeFilter;
  });

  const getEventIcon = (eventStr = "") => {
    if (eventStr.includes("CRASH") || eventStr.includes("CRASHED")) return <Zap size={16} color="#f59e0b" />;
    if (eventStr.includes("CONFLICT") || eventStr.includes("ALERT")) return <AlertTriangle size={16} color="#ef4444" />;
    if (eventStr.includes("ACTIVITY")) return <Activity size={16} color="#6366f1" />;
    return <Calendar size={16} color="#10b981" />;
  };

  return (
    <div style={{ position: "relative" }}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        title="Live Activity & Notification Log"
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "8px",
          borderRadius: "8px",
          border: "1px solid var(--border-color, #cbd5e1)",
          background: "var(--bg-card, #ffffff)",
          color: "var(--text-primary, #0f172a)",
          cursor: "pointer",
          boxShadow: "var(--shadow-sm)",
          transition: "all 0.2s ease",
        }}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: "-4px",
              right: "-4px",
              background: "#ef4444",
              color: "#ffffff",
              fontSize: "0.65rem",
              fontWeight: 800,
              width: "18px",
              height: "18px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 8px rgba(239, 68, 68, 0.5)",
            }}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Notification Dropdown Drawer */}
      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "46px",
            right: 0,
            width: "380px",
            maxHeight: "520px",
            background: "var(--bg-card, #ffffff)",
            borderRadius: "14px",
            boxShadow: "0 14px 35px rgba(0, 0, 0, 0.2)",
            border: "1px solid var(--border-color, #cbd5e1)",
            zIndex: 99999,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            color: "var(--text-primary)",
          }}
        >
          {/* Drawer Header */}
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid var(--border-color, #e2e8f0)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: "var(--bg-main, #f8fafc)",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: isConnected ? "#10b981" : "#f59e0b",
                  }}
                  title={isConnected ? "WebSocket Connected" : "Connecting..."}
                />
                <strong style={{ fontSize: "0.95rem" }}>Activity Log & Alerts</strong>
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                {isConnected ? "Live WebSocket Stream Active" : "Polling Mode"}
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Action Toolbar */}
          <div
            style={{
              padding: "8px 14px",
              borderBottom: "1px solid var(--border-color)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "0.75rem",
              background: "var(--bg-card)",
            }}
          >
            {/* Category Tabs */}
            <div style={{ display: "flex", gap: "6px" }}>
              {["ALL", "ACTIVITIES", "SYSTEM"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveFilter(cat)}
                  style={{
                    padding: "3px 8px",
                    borderRadius: "4px",
                    border: "none",
                    background: activeFilter === cat ? "var(--accent, #6366f1)" : "var(--bg-main)",
                    color: activeFilter === cat ? "#fff" : "var(--text-secondary)",
                    cursor: "pointer",
                    fontSize: "0.7rem",
                    fontWeight: 700,
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--accent, #6366f1)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    fontWeight: 600,
                  }}
                >
                  <CheckCheck size={14} /> Read
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={clearAll}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#ef4444",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Trash2 size={14} /> Clear
                </button>
              )}
            </div>
          </div>

          {/* Notification List */}
          <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
            {filteredNotifications.length === 0 ? (
              <div style={{ padding: "30px 16px", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                <Layers size={28} style={{ opacity: 0.4, marginBottom: "8px" }} />
                <p style={{ margin: 0 }}>No recent activity events.</p>
              </div>
            ) : (
              filteredNotifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => setNotifications((prev) => prev.map((item) => (item.id === n.id ? { ...item, read: true } : item)))}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    marginBottom: "6px",
                    background: n.read ? "var(--bg-main, #f8fafc)" : "rgba(99, 102, 241, 0.08)",
                    border: n.read ? "1px solid var(--border-color)" : "1px solid rgba(99, 102, 241, 0.3)",
                    display: "flex",
                    gap: "10px",
                    alignItems: "flex-start",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ marginTop: "2px" }}>{getEventIcon(n.event)}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "0.8rem", color: "var(--text-primary)" }}>{n.event}</strong>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{n.timestamp}</span>
                    </div>
                    <p style={{ margin: "2px 0 0 0", fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.3 }}>
                      {n.message}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
