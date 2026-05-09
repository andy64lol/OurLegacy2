/**
 * Our Legacy 2 — Node.js API Gateway
 *
 * Architecture:
 *   Client → Node.js (port 5000) → Python internal API (port 8000) → Node.js → Client
 *
 * Responsibilities:
 *   - HTTP reverse proxy to Python backend
 *   - WebSocket / Socket.IO proxy to Python Socket.IO
 *   - CORS headers
 *   - Rate limiting (60 req/min per IP on /api/*)
 */

const express = require("express");
const http = require("http");
const { createProxyMiddleware } = require("http-proxy-middleware");
const { Server: SocketIOServer } = require("socket.io");
const { io: ioClient } = require("socket.io-client");
const cors = require("cors");
const rateLimit = require("express-rate-limit");

const PYTHON_BASE = process.env.PYTHON_INTERNAL_URL || "http://127.0.0.1:8000";
const PORT = parseInt(process.env.PORT || "5000", 10);

const app = express();
const server = http.createServer(app);

// ── Trust proxy (Replit sits behind a proxy) ─────────────────────────────────
app.set("trust proxy", 1);

// ── CORS ──────────────────────────────────────────────────────────────────────
app.use(
  cors({
    origin: (origin, cb) => cb(null, origin || "*"),
    credentials: true,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: [
      "Content-Type",
      "Authorization",
      "X-Requested-With",
      "X-API-Key",
    ],
  })
);
app.options("*", cors());

// ── Rate limiting on /api/* ───────────────────────────────────────────────────
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 60,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    ok: false,
    message: "Rate limit exceeded: 60 requests/minute per IP.",
    retry_after: 60,
  },
  skip: (req) => !req.path.startsWith("/api/"),
});
app.use(apiLimiter);

// ── HTTP proxy — forward everything to Python ─────────────────────────────────
const pythonProxy = createProxyMiddleware({
  target: PYTHON_BASE,
  changeOrigin: true,
  ws: false, // WebSocket handled separately via Socket.IO bridge
  on: {
    error: (err, req, res) => {
      console.error("[proxy] Error:", err.message);
      if (res && !res.headersSent) {
        res.status(502).json({
          ok: false,
          message: "Backend unavailable. Please try again shortly.",
        });
      }
    },
    proxyReq: (proxyReq, req) => {
      // Forward real client IP so Flask rate-limiting works
      const ip =
        req.headers["x-forwarded-for"] ||
        req.socket?.remoteAddress ||
        "unknown";
      proxyReq.setHeader("X-Forwarded-For", ip);
      proxyReq.setHeader("X-Real-IP", ip);
    },
  },
});
app.use("/", pythonProxy);

// ── Socket.IO server (public-facing) ─────────────────────────────────────────
const publicSio = new SocketIOServer(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
    credentials: true,
  },
  // Allow the client to send cookies (session cookie) via auth or handshake
  allowRequest: (req, callback) => callback(null, true),
});

// Pool of connections to the Python Socket.IO server (one per public client)
// sid (public) → python socket.io-client instance
const bridges = new Map();

// Events to relay from client → Python
const CLIENT_TO_PYTHON_EVENTS = [
  "chat_send",
  "group_chat_send",
  "trade_request",
  "trade_accept",
  "trade_decline",
  "trade_add_item",
  "trade_remove_item",
  "trade_set_gold",
  "trade_confirm",
  "trade_cancel",
];

// Events to relay from Python → client
const PYTHON_TO_CLIENT_EVENTS = [
  "chat_message",
  "chat_history",
  "chat_error",
  "online_users",
  "mod_list",
  "owner_name",
  "user_flags",
  "group_chat_message",
  "group_chat_error",
  "trade_invite",
  "trade_invite_sent",
  "trade_update",
  "trade_approved",
  "trade_cancelled",
  "trade_error",
];

publicSio.on("connection", (clientSocket) => {
  const handshake = clientSocket.handshake;
  const cookieHeader = handshake.headers.cookie || "";

  // Connect a dedicated socket.io-client to the Python backend,
  // forwarding the browser's session cookie so Python can load the session.
  const pySocket = ioClient(PYTHON_BASE, {
    path: "/socket.io",
    transports: ["websocket", "polling"],
    extraHeaders: {
      cookie: cookieHeader,
    },
    reconnection: false,
  });

  bridges.set(clientSocket.id, pySocket);

  // ── Python → Client relay ───────────────────────────────────────────────
  for (const event of PYTHON_TO_CLIENT_EVENTS) {
    pySocket.on(event, (data) => {
      clientSocket.emit(event, data);
    });
  }

  // Forward any unlisted events from Python → client too
  pySocket.onAny((event, data) => {
    if (!PYTHON_TO_CLIENT_EVENTS.includes(event)) {
      clientSocket.emit(event, data);
    }
  });

  pySocket.on("connect_error", (err) => {
    console.error("[sio-bridge] Python connect error:", err.message);
    clientSocket.emit("chat_error", {
      message: "Real-time service temporarily unavailable.",
    });
  });

  pySocket.on("disconnect", (reason) => {
    if (reason !== "io client disconnect") {
      clientSocket.disconnect(true);
    }
  });

  // ── Client → Python relay ───────────────────────────────────────────────
  for (const event of CLIENT_TO_PYTHON_EVENTS) {
    clientSocket.on(event, (data) => {
      pySocket.emit(event, data);
    });
  }

  // ── Cleanup on client disconnect ────────────────────────────────────────
  clientSocket.on("disconnect", () => {
    pySocket.disconnect();
    bridges.delete(clientSocket.id);
  });
});

// ── Start ─────────────────────────────────────────────────────────────────────
server.listen(PORT, "0.0.0.0", () => {
  console.log(`[gateway] Node.js API gateway listening on port ${PORT}`);
  console.log(`[gateway] Proxying to Python backend at ${PYTHON_BASE}`);
});
