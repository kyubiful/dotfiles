/**
 * /usage — shows remaining Codex (OpenAI) and GitHub Copilot subscription quota.
 *
 * Codex: tries a live JSON-RPC call to `codex app-server` (account/rateLimits/read).
 * Falls back to reading the newest local rollout session log
 * (~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl) for the last known rate_limits
 * snapshot when the live call is unavailable or times out.
 *
 * Copilot: uses `gh auth token` (GitHub CLI) or, as a fallback, the Copilot CLI's
 * own stored token (~/.copilot/config.json) to call the same internal entitlement
 * endpoint the official clients use (GET /copilot_internal/user). This endpoint is
 * undocumented/unofficial and could change without notice.
 *
 * Requires network access and one or both of: `codex` CLI logged in with ChatGPT,
 * `gh` CLI authenticated (or Copilot CLI logged in).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Box, Text } from "@earendil-works/pi-tui";
import { spawn } from "node:child_process";
import {
  closeSync,
  existsSync,
  fstatSync,
  openSync,
  readdirSync,
  readFileSync,
  readSync,
  statSync,
} from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

interface RateLimitWindow {
  usedPercent: number;
  windowMinutes?: number | null;
  resetsAt?: number | null; // unix seconds
}

function pickWeekly(
  primary?: RateLimitWindow | null,
  secondary?: RateLimitWindow | null,
): RateLimitWindow | null {
  const candidates = [primary, secondary].filter(
    (w): w is RateLimitWindow => !!w,
  );
  if (candidates.length === 0) return null;
  return candidates.reduce((a, b) =>
    (b.windowMinutes ?? 0) > (a.windowMinutes ?? 0) ? b : a,
  );
}

function fmtDuration(seconds: number): string {
  if (seconds <= 0) return "ahora";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function bar(usedPercent: number, width = 20): string {
  const clamped = Math.max(0, Math.min(100, usedPercent));
  const filled = Math.round((clamped / 100) * width);
  return "█".repeat(filled) + "░".repeat(Math.max(0, width - filled));
}

// ---------------------------------------------------------------------------
// Codex
// ---------------------------------------------------------------------------

interface CodexQuota {
  source: "live" | "session-log";
  planType?: string;
  primary?: RateLimitWindow | null; // ~5h window
  weekly?: RateLimitWindow | null; // largest window, typically weekly
}

function codexHome(): string {
  return process.env.CODEX_HOME && process.env.CODEX_HOME.length > 0
    ? process.env.CODEX_HOME
    : join(homedir(), ".codex");
}

function fetchCodexLive(timeoutMs = 6000): Promise<CodexQuota | null> {
  return new Promise((resolve) => {
    let settled = false;
    let child: ReturnType<typeof spawn> | undefined;

    const done = (value: CodexQuota | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        child?.kill();
      } catch {
        // ignore
      }
      resolve(value);
    };

    const timer = setTimeout(() => done(null), timeoutMs);

    try {
      child = spawn("codex", ["app-server"], {
        stdio: ["pipe", "pipe", "pipe"],
      });
    } catch {
      done(null);
      return;
    }

    child.on("error", () => done(null));

    let buffer = "";
    child.stdout?.on("data", (chunk: Buffer) => {
      buffer += chunk.toString("utf8");
      let idx = buffer.indexOf("\n");
      while (idx >= 0) {
        const line = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 1);
        idx = buffer.indexOf("\n");
        if (!line) continue;

        let msg: any;
        try {
          msg = JSON.parse(line);
        } catch {
          continue;
        }

        if (msg.id === 1) {
          // initialize response received; ack and request rate limits
          child?.stdin?.write(`${JSON.stringify({ method: "initialized" })}\n`);
          child?.stdin?.write(
            `${JSON.stringify({ method: "account/rateLimits/read", id: 2 })}\n`,
          );
        } else if (msg.id === 2) {
          const rl = msg.result?.rateLimits;
          if (!rl) {
            done(null);
            continue;
          }
          const primary = rl.primary
            ? {
                usedPercent: rl.primary.usedPercent,
                windowMinutes: rl.primary.windowDurationMins,
                resetsAt: rl.primary.resetsAt,
              }
            : null;
          const secondary = rl.secondary
            ? {
                usedPercent: rl.secondary.usedPercent,
                windowMinutes: rl.secondary.windowDurationMins,
                resetsAt: rl.secondary.resetsAt,
              }
            : null;
          done({
            source: "live",
            primary,
            weekly: pickWeekly(primary, secondary),
          });
        }
      }
    });

    child.stdin?.write(
      `${JSON.stringify({
        method: "initialize",
        id: 1,
        params: {
          clientInfo: {
            name: "pi_usage_extension",
            title: "pi /usage extension",
            version: "1.0.0",
          },
        },
      })}\n`,
    );
  });
}

function listSubdirsDesc(dir: string): string[] {
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .sort((a, b) => (a < b ? 1 : a > b ? -1 : 0));
  } catch {
    return [];
  }
}

function recentDayDirs(sessionsDir: string, limit = 14): string[] {
  const days: string[] = [];
  for (const y of listSubdirsDesc(sessionsDir)) {
    const yDir = join(sessionsDir, y);
    for (const m of listSubdirsDesc(yDir)) {
      const mDir = join(yDir, m);
      for (const d of listSubdirsDesc(mDir)) {
        days.push(join(mDir, d));
        if (days.length >= limit) return days;
      }
    }
  }
  return days;
}

function newestRolloutFiles(sessionsDir: string, maxFiles = 40): string[] {
  const files: { path: string; mtime: number }[] = [];
  for (const dayDir of recentDayDirs(sessionsDir)) {
    let entries: string[];
    try {
      entries = readdirSync(dayDir);
    } catch {
      continue;
    }
    for (const name of entries) {
      if (!name.startsWith("rollout-") || !name.endsWith(".jsonl")) continue;
      const path = join(dayDir, name);
      try {
        files.push({ path, mtime: statSync(path).mtimeMs });
      } catch {
        // ignore
      }
    }
  }
  files.sort((a, b) => b.mtime - a.mtime);
  return files.slice(0, maxFiles).map((f) => f.path);
}

function readTailLines(path: string, maxBytes = 2_000_000): string[] {
  let fd: number | undefined;
  try {
    fd = openSync(path, "r");
    const size = fstatSync(fd).size;
    const start = Math.max(0, size - maxBytes);
    const len = size - start;
    const buf = Buffer.alloc(len);
    readSync(fd, buf, 0, len, start);
    return buf.toString("utf8").split("\n");
  } catch {
    return [];
  } finally {
    if (fd !== undefined) {
      try {
        closeSync(fd);
      } catch {
        // ignore
      }
    }
  }
}

function extractRateLimitsFromLines(
  lines: string[],
  nowSec: number,
): CodexQuota | null {
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i]?.trim();
    if (!line) continue;

    let value: any;
    try {
      value = JSON.parse(line);
    } catch {
      continue;
    }

    const payload = value?.payload;
    if (!payload) continue;
    const rl = payload.rate_limits ?? payload.info?.rate_limits;
    if (!rl) continue;
    if (rl.limit_id && rl.limit_id !== "codex") continue;

    const mapWindow = (w: any): RateLimitWindow | null => {
      if (!w) return null;
      return {
        usedPercent: w.used_percent ?? 0,
        windowMinutes: w.window_minutes ?? null,
        resetsAt: w.resets_at ?? null,
      };
    };

    let primary = mapWindow(rl.primary);
    let secondary = mapWindow(rl.secondary);
    if (primary?.resetsAt != null && primary.resetsAt <= nowSec) primary = null;
    if (secondary?.resetsAt != null && secondary.resetsAt <= nowSec)
      secondary = null;
    if (!primary && !secondary) continue;

    return {
      source: "session-log",
      planType: rl.plan_type,
      primary,
      weekly: pickWeekly(primary, secondary),
    };
  }
  return null;
}

function fetchCodexFromSessionLogs(): CodexQuota | null {
  const sessionsDir = join(codexHome(), "sessions");
  if (!existsSync(sessionsDir)) return null;
  const nowSec = Math.floor(Date.now() / 1000);
  for (const file of newestRolloutFiles(sessionsDir)) {
    const quota = extractRateLimitsFromLines(readTailLines(file), nowSec);
    if (quota) return quota;
  }
  return null;
}

async function getCodexQuota(): Promise<CodexQuota | null> {
  const live = await fetchCodexLive().catch(() => null);
  if (live) return live;
  return fetchCodexFromSessionLogs();
}

// ---------------------------------------------------------------------------
// Copilot
// ---------------------------------------------------------------------------

interface CopilotQuota {
  planType?: string;
  resetsAt?: number | null;
  premium?: {
    usedPercent: number;
    remaining?: number;
    entitlement?: number;
    unlimited: boolean;
  } | null;
}

function stripJsonComments(input: string): string {
  let out = "";
  let inString = false;
  let escaped = false;
  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    if (inString) {
      out += c;
      if (escaped) escaped = false;
      else if (c === "\\") escaped = true;
      else if (c === '"') inString = false;
      continue;
    }
    if (c === '"') {
      inString = true;
      out += c;
      continue;
    }
    if (c === "/" && input[i + 1] === "/") {
      while (i < input.length && input[i] !== "\n") i++;
      out += "\n";
      continue;
    }
    if (c === "/" && input[i + 1] === "*") {
      i += 2;
      while (i < input.length && !(input[i] === "*" && input[i + 1] === "/"))
        i++;
      i++;
      continue;
    }
    out += c;
  }
  return out;
}

function readCopilotCliToken(): string | null {
  const path = join(homedir(), ".copilot", "config.json");
  if (!existsSync(path)) return null;
  try {
    const json = JSON.parse(stripJsonComments(readFileSync(path, "utf8")));
    const tokens = json.copilotTokens as Record<string, string> | undefined;
    if (!tokens) return null;
    const lastUser = json.lastLoggedInUser as
      { host?: string; login?: string } | undefined;
    if (lastUser?.host && lastUser?.login) {
      const key = `${lastUser.host}:${lastUser.login}`;
      if (tokens[key]) return tokens[key];
    }
    const entry = Object.entries(tokens).find(([k]) =>
      k.startsWith("https://github.com"),
    );
    return entry?.[1] ?? null;
  } catch {
    return null;
  }
}

async function getGhToken(pi: ExtensionAPI): Promise<string | null> {
  try {
    const result = await pi.exec("gh", ["auth", "token"], { timeout: 5000 });
    const token = result.stdout.trim();
    return result.code === 0 && token ? token : null;
  } catch {
    return null;
  }
}

async function getCopilotQuota(pi: ExtensionAPI): Promise<CopilotQuota | null> {
  const token = (await getGhToken(pi)) ?? readCopilotCliToken();
  if (!token) return null;

  let resp: Response | null = null;
  try {
    resp = await fetch("https://api.github.com/copilot_internal/user", {
      headers: {
        Authorization: `token ${token}`,
        Accept: "application/json",
        "User-Agent": "pi-usage-extension",
        "Copilot-Integration-Id": "copilot-cli",
        "X-GitHub-Api-Version": "2025-04-01",
      },
    });
  } catch {
    return null;
  }
  if (!resp?.ok) return null;

  let data: any;
  try {
    data = await resp.json();
  } catch {
    return null;
  }

  const premiumRaw = data.quota_snapshots?.premium_interactions;
  let premium: CopilotQuota["premium"] = null;
  if (premiumRaw) {
    if (premiumRaw.unlimited) {
      premium = { usedPercent: 0, unlimited: true };
    } else if (typeof premiumRaw.percent_remaining === "number") {
      premium = {
        usedPercent: Math.max(
          0,
          Math.min(100, 100 - premiumRaw.percent_remaining),
        ),
        remaining: premiumRaw.remaining,
        entitlement: premiumRaw.entitlement,
        unlimited: false,
      };
    } else if (
      typeof premiumRaw.remaining === "number" &&
      typeof premiumRaw.entitlement === "number" &&
      premiumRaw.entitlement > 0
    ) {
      premium = {
        usedPercent: Math.max(
          0,
          Math.min(
            100,
            (1 - premiumRaw.remaining / premiumRaw.entitlement) * 100,
          ),
        ),
        remaining: premiumRaw.remaining,
        entitlement: premiumRaw.entitlement,
        unlimited: false,
      };
    }
  }

  const resetIso =
    data.quota_reset_date_utc ??
    (data.quota_reset_date ? `${data.quota_reset_date}T00:00:00Z` : undefined);
  const resetsAt = resetIso
    ? Math.floor(new Date(resetIso).getTime() / 1000)
    : null;

  return { planType: data.copilot_plan, premium, resetsAt };
}

// ---------------------------------------------------------------------------
// Command + rendering
// ---------------------------------------------------------------------------

interface UsageReportData {
  fetchedAt: number;
  codex: CodexQuota | null;
  copilot: CopilotQuota | null;
}

function colorForUsage(theme: any, usedPercent: number, text: string): string {
  if (usedPercent >= 90) return theme.fg("error", text);
  if (usedPercent >= 70) return theme.fg("warning", text);
  return theme.fg("success", text);
}

export default function (pi: ExtensionAPI) {
  pi.registerEntryRenderer<UsageReportData>(
    "usage-report",
    (entry, { expanded }, theme) => {
      const data = entry.data;
      const box = new Box(1, 1, (text) => theme.bg("selectedBg", text));
      box.addChild(new Text(theme.bold("Usage"), 0, 0));

      if (data?.codex) {
        const w = data.codex.weekly;
        if (w) {
          const label = colorForUsage(
            theme,
            w.usedPercent,
            `${w.usedPercent.toFixed(0)}% used`,
          );
          box.addChild(
            new Text(
              `${theme.fg("warning", "Codex")} (weekly): ${label}  ${bar(w.usedPercent)}`,
              0,
              0,
            ),
          );
          if (w.resetsAt) {
            box.addChild(
              new Text(
                theme.fg(
                  "dim",
                  `  resets in ${fmtDuration(w.resetsAt - Math.floor(Date.now() / 1000))}`,
                ),
                0,
                0,
              ),
            );
          }
        } else {
          box.addChild(
            new Text(
              theme.fg("dim", "Codex: no weekly window data available yet"),
              0,
              0,
            ),
          );
        }
        if (data.codex.source === "session-log") {
          box.addChild(
            new Text(
              theme.fg("dim", "  (from last local session log, not live)"),
              0,
              0,
            ),
          );
        }
      } else {
        box.addChild(
          new Text(
            theme.fg(
              "dim",
              "Codex: no data (is the codex CLI installed and logged in?)",
            ),
            0,
            0,
          ),
        );
      }

      if (data?.copilot?.premium) {
        const p = data.copilot.premium;
        if (p.unlimited) {
          box.addChild(
            new Text(
              `${theme.fg("warning", "Copilot")} (premium requests): ${theme.fg("success", "unlimited")}`,
              0,
              0,
            ),
          );
        } else {
          const used =
            p.remaining != null && p.entitlement != null
              ? p.entitlement - p.remaining
              : null;
          const detail =
            used != null && p.entitlement != null
              ? ` (${used}/${p.entitlement})`
              : "";
          const label = colorForUsage(
            theme,
            p.usedPercent,
            `${p.usedPercent.toFixed(0)}% used`,
          );
          box.addChild(
            new Text(
              `${theme.fg("warning", "Copilot")} (premium requests): ${label}${detail}  ${bar(p.usedPercent)}`,
              0,
              0,
            ),
          );
          if (data.copilot.resetsAt) {
            box.addChild(
              new Text(
                theme.fg(
                  "dim",
                  `  resets in ${fmtDuration(data.copilot.resetsAt - Math.floor(Date.now() / 1000))}`,
                ),
                0,
                0,
              ),
            );
          }
        }
      } else {
        box.addChild(
          new Text(
            theme.fg(
              "dim",
              "Copilot: no data (try 'gh auth login' or 'copilot login')",
            ),
            0,
            0,
          ),
        );
      }

      if (expanded) {
        box.addChild(
          new Text(
            theme.fg(
              "dim",
              `Updated: ${new Date(data?.fetchedAt ?? Date.now()).toLocaleString()}`,
            ),
            0,
            0,
          ),
        );
      }

      return box;
    },
  );

  pi.registerCommand("usage", {
    description: "Show Codex and Copilot subscription usage used so far",
    handler: async (_args, ctx) => {
      ctx.ui.setStatus("usage-quota", "Fetching Codex/Copilot usage...");
      try {
        const [codex, copilot] = await Promise.all([
          getCodexQuota().catch(() => null),
          getCopilotQuota(pi).catch(() => null),
        ]);
        pi.appendEntry<UsageReportData>("usage-report", {
          fetchedAt: Date.now(),
          codex,
          copilot,
        });
      } finally {
        ctx.ui.setStatus("usage-quota", undefined);
      }
    },
  });
}
