#!/usr/bin/env node
/**
 * Статический сервер для Tatnet / Onrender / Railway
 * Главные фиксы для Tatnet:
 *  1. Слушаем 0.0.0.0 (не localhost!)
 *  2. Порт СТРОГО из process.env.PORT
 *  3. Health-check GET / отвечает мгновенно 200
 *  4. Нет никаких зависимостей — только встроенный http/fs/path
 *  5. Не падаем при uncaughtException
 */

const http = require("http");
const fs   = require("fs");
const path = require("path");

// ── Порт: Tatnet/Onrender всегда передают PORT через env ──────
const PORT = parseInt(process.env.PORT, 10) || 3000;
const HOST = "0.0.0.0";

// ── Корень проекта и папка для раздачи ───────────────────────
const ROOT  = path.resolve(__dirname, "..");
const SERVE = [
  path.join(ROOT, "public"),
  path.join(ROOT, "docs"),
  ROOT,
].find(d => fs.existsSync(d) && fs.existsSync(path.join(d, "index.html"))) || ROOT;

console.log(`📁 Раздаём из: ${SERVE}`);

// ── MIME типы ─────────────────────────────────────────────────
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js":   "application/javascript; charset=utf-8",
  ".css":  "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".xml":  "application/xml; charset=utf-8",
  ".m3u":  "application/x-mpegurl; charset=utf-8",
  ".m3u8": "application/x-mpegurl",
  ".png":  "image/png",
  ".jpg":  "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif":  "image/gif",
  ".svg":  "image/svg+xml",
  ".ico":  "image/x-icon",
  ".woff2":"font/woff2",
  ".woff": "font/woff",
  ".txt":  "text/plain; charset=utf-8",
};

// ── HTTP сервер ───────────────────────────────────────────────
const server = http.createServer((req, res) => {

  // CORS — нужен для embed-виджета и data/
  res.setHeader("Access-Control-Allow-Origin",  "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  // Preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  // Только GET/HEAD
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { "Content-Type": "text/plain" });
    res.end("Method Not Allowed");
    return;
  }

  // Разбираем путь
  let urlPath = (req.url || "/").split("?")[0].split("#")[0];
  try { urlPath = decodeURIComponent(urlPath); } catch (_) {}

  // Нормализуем
  if (!urlPath || urlPath === "/") urlPath = "/index.html";

  // embed без расширения
  if (urlPath === "/embed")  urlPath = "/embed.html";
  if (urlPath === "/player") urlPath = "/player.html";

  // Безопасный путь
  const abs = path.resolve(SERVE, "." + urlPath);
  if (!abs.startsWith(SERVE)) {
    res.writeHead(403, { "Content-Type": "text/plain" });
    res.end("Forbidden");
    return;
  }

  // Выбираем файл
  let target = abs;
  if (fs.existsSync(target) && fs.statSync(target).isDirectory()) {
    target = path.join(target, "index.html");
  }
  if (!fs.existsSync(target)) {
    // SPA fallback
    target = path.join(SERVE, "index.html");
  }

  const ext  = path.extname(target).toLowerCase();
  const mime = MIME[ext] || "application/octet-stream";

  // Заголовки кэша
  const isData = urlPath.startsWith("/data/");
  const cacheHdr = isData
    ? "public, max-age=10800"   // данные кэшируем 3 часа
    : "public, max-age=300";    // HTML — 5 минут

  // embed.html можно встраивать с любого сайта
  const extraHeaders = {};
  if (urlPath === "/embed.html" || urlPath === "/embed") {
    extraHeaders["X-Frame-Options"] = "ALLOWALL";
    extraHeaders["Content-Security-Policy"] = "frame-ancestors *";
  }

  let stat;
  try { stat = fs.statSync(target); } catch (_) {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("Not Found");
    return;
  }

  const headers = {
    "Content-Type":   mime,
    "Content-Length": stat.size,
    "Cache-Control":  cacheHdr,
    ...extraHeaders,
  };

  res.writeHead(200, headers);

  if (req.method === "HEAD") { res.end(); return; }

  // Поток файла
  const stream = fs.createReadStream(target);
  stream.on("error", err => {
    console.error("Stream error:", err.message);
    if (!res.headersSent) {
      res.writeHead(500, { "Content-Type": "text/plain" });
    }
    res.end("Server Error");
  });
  stream.pipe(res);
});

// ── Запуск ────────────────────────────────────────────────────
server.listen(PORT, HOST, () => {
  console.log(`\n📺 LiveПрограмма запущена`);
  console.log(`🌐 http://${HOST}:${PORT}`);
  console.log(`🕐 ${new Date().toISOString()}\n`);
});

// Обработка ошибок сервера (порт занят и т.д.)
server.on("error", err => {
  console.error("❌ Server error:", err.message);
  if (err.code === "EADDRINUSE") {
    console.error(`Порт ${PORT} уже занят`);
  }
  process.exit(1);
});

// Не падаем от необработанных ошибок
process.on("uncaughtException", err => {
  console.error("uncaughtException:", err.message);
});
process.on("unhandledRejection", err => {
  console.error("unhandledRejection:", err);
});

// Graceful shutdown
process.on("SIGTERM", () => {
  console.log("SIGTERM — останавливаем сервер...");
  server.close(() => process.exit(0));
});
process.on("SIGINT", () => {
  server.close(() => process.exit(0));
});
