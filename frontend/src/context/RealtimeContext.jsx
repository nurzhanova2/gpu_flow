import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { buildWsProtocols, wsStreamUrl } from "../api/client";
import { useAuth } from "./AuthContext";

const RealtimeContext = createContext(null);

export function RealtimeProvider({ children }) {
  const { accessToken, isAuthenticated, logout } = useAuth();
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const heartbeatTimerRef = useRef(null);
  const listenersRef = useRef(new Set());
  const reconnectAttemptRef = useRef(0);
  const [connected, setConnected] = useState(false);

  const cleanupSocket = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.onopen = null;
      socketRef.current.onclose = null;
      socketRef.current.onmessage = null;
      socketRef.current.onerror = null;
      socketRef.current.close();
      socketRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      cleanupSocket();
      return;
    }

    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;

      const socket = new WebSocket(wsStreamUrl(), buildWsProtocols(accessToken));
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectAttemptRef.current = 0;
        setConnected(true);
        heartbeatTimerRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 15000);
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed?.type === "pong") return;
          listenersRef.current.forEach((listener) => listener(parsed));
        } catch {
          // noop: malformed event
        }
      };

      socket.onclose = (event) => {
        setConnected(false);
        if (heartbeatTimerRef.current) {
          clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }
        if (!isMounted) return;
        if (event.code === 1008) {
          logout("Realtime-сессия недействительна. Выполните вход снова.");
          return;
        }

        reconnectAttemptRef.current += 1;
        const timeout = Math.min(4000, 800 + reconnectAttemptRef.current * 500);
        reconnectTimerRef.current = setTimeout(connect, timeout);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      isMounted = false;
      cleanupSocket();
    };
  }, [accessToken, isAuthenticated, cleanupSocket, logout]);

  const subscribe = useCallback((listener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const value = useMemo(() => ({ connected, subscribe }), [connected, subscribe]);

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error("useRealtime must be used inside RealtimeProvider");
  }
  return context;
}
