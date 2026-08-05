/**
 * /persona — OpenCode-style "personality" switcher for the main pi session.
 *
 * Define personas as markdown files with YAML-ish frontmatter:
 *
 *   ~/.pi/agent/personas/<name>.md   (global, all projects)
 *   .pi/personas/<name>.md           (project-local, overrides global of same name)
 *
 * Frontmatter fields (all optional):
 *   name: display name shown in the footer and user-facing messages; defaults
 *         to the markdown filename (the stable id used by /persona)
 *   description: shown in the /persona picker
 *   tools: comma list of built-in tool names to restrict to (e.g. "read, bash, grep")
 *          omit to leave the current tool set untouched
 *   model: provider/modelId or fuzzy name ("sonnet", "haiku")
 *   thinking: off|minimal|low|medium|high|xhigh|max
 *   color: footer badge color — either a pi theme token ("success", "warning",
 *          "accent", "syntaxKeyword", ...) or a raw hex color ("#ff8800")
 *   permission: per-tool gating, two forms:
 *
 *          Flat (defaults only): "bash=ask, edit=deny, write=deny"
 *
 *          Nested block (defaults + fine-grained Claude-Code-style rules):
 *            permission:
 *              bash: ask
 *              edit: deny
 *              write: deny
 *              allow:
 *                - Bash(npm run *)
 *                - Bash(git commit *)
 *                - Bash(git * main)
 *                - Bash(* --version)
 *                - Bash(* --help *)
 *              deny:
 *                - Bash(git push *)
 *
 *          `Tool(pattern)` rules match `pattern` (glob, `*` wildcard) against
 *          the command (for bash) or path (for write/edit). The last matching
 *          rule wins over earlier ones and over the plain tool-level default,
 *          so put broad rules first and specific overrides after — same
 *          precedence convention as OpenCode's bash permission patterns.
 *          allow|ask|deny actions: allow passes through untouched, deny blocks
 *          the call with a reason, ask prompts via ctx.ui.confirm. This is
 *          what lets a persona keep a tool *callable* (e.g. bash) while still
 *          gating individual invocations, instead of hard-excluding it from
 *          the tool set via `tools`.
 *
 * Body = system prompt prepended ahead of pi's normal system prompt for every
 * turn while this persona is active — this is what makes the persona "stick"
 * as the main session's personality, not just a one-shot prompt template.
 *
 * Typical setup: personas describe *orchestrators* whose job is to break a
 * task down and delegate pieces to already-configured subagents (defined as
 * .pi/agents/<name>.md for @tintinweb/pi-subagents) via the `Agent` tool,
 * usually with run_in_background: true.
 */

import type {
	ExtensionAPI,
	ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

type PermissionAction = "allow" | "ask" | "deny";

interface PermissionRule {
	action: PermissionAction;
	tool: string; // lowercase tool name, e.g. "bash"
	pattern: string; // glob pattern (`*` wildcard), matched against the subject
}

interface PersonaPermission {
	defaults: Record<string, PermissionAction>;
	rules: PermissionRule[];
}

interface Persona {
	id: string;
	name: string;
	description: string;
	tools?: string[];
	model?: string;
	thinking?: string;
	color?: string;
	permission?: PersonaPermission;
	systemPrompt: string;
	source: "global" | "project";
	path: string;
}

const PERSONA_ENTRY_TYPE = "persona-active";

/** Parse "Bash(git push *)" -> { tool: "bash", pattern: "git push *" }. */
function parseToolPattern(
	item: string,
): { tool: string; pattern: string } | undefined {
	const m = item.match(/^([A-Za-z_][\w-]*)\((.*)\)\s*$/);
	if (!m) return undefined;
	return { tool: m[1].toLowerCase(), pattern: m[2] };
}

/**
 * Extract and parse the `permission:` field out of the *raw* frontmatter text
 * (not the flat attrs map, since this field can be a nested YAML-ish block).
 * Supports both the flat inline form and the nested block form documented in
 * the file header comment above.
 */
function parsePermissionBlock(fmText: string): PersonaPermission | undefined {
	const lines = fmText.split(/\r?\n/);
	const defaults: Record<string, PermissionAction> = {};
	const rules: PermissionRule[] = [];

	let inBlock = false;
	let currentList: PermissionAction | null = null;

	for (const rawLine of lines) {
		if (!inBlock) {
			const start = rawLine.match(/^permission:\s*(.*)$/);
			if (!start) continue;
			const inline = start[1].trim();
			if (inline) {
				// Flat inline form: "bash=ask, edit=deny, write=deny"
				for (const part of inline.split(",")) {
					const [tool, action] = part.split("=").map((s) => s.trim());
					if (
						tool &&
						(action === "allow" || action === "ask" || action === "deny")
					) {
						defaults[tool.toLowerCase()] = action;
					}
				}
				continue;
			}
			inBlock = true;
			continue;
		}

		if (rawLine.trim() === "") continue;
		const indent = rawLine.match(/^\s*/)?.[0].length ?? 0;
		if (indent === 0) break; // dedent back to a top-level key -> block ended

		const trimmed = rawLine.trim();

		const listItem = trimmed.match(/^-\s*(.+)$/);
		if (listItem && currentList) {
			const parsed = parseToolPattern(listItem[1].trim());
			if (parsed) {
				rules.push({
					action: currentList,
					tool: parsed.tool,
					pattern: parsed.pattern,
				});
			}
			continue;
		}

		const kv = trimmed.match(/^([A-Za-z_][\w-]*)\s*:\s*(.*)$/);
		if (!kv) continue;
		const [, key, value] = kv;
		const lowerKey = key.toLowerCase();
		const trimmedValue = value.trim();

		if (
			(lowerKey === "allow" || lowerKey === "deny" || lowerKey === "ask") &&
			!trimmedValue
		) {
			currentList = lowerKey as PermissionAction;
			continue;
		}

		currentList = null;
		if (
			trimmedValue === "allow" ||
			trimmedValue === "ask" ||
			trimmedValue === "deny"
		) {
			defaults[lowerKey] = trimmedValue;
		}
	}

	if (Object.keys(defaults).length === 0 && rules.length === 0) {
		return undefined;
	}
	return { defaults, rules };
}

/** Compile a `*`-glob pattern into an anchored, case-sensitive RegExp. */
function globToRegExp(pattern: string): RegExp {
	const escaped = pattern
		.replace(/[.+^${}()|[\]\\]/g, "\\$&")
		.replace(/\*/g, ".*");
	return new RegExp(`^${escaped}$`);
}

/**
 * Resolve the effective action for a tool call:
 * 1. Last matching allow/deny/ask rule for this tool wins.
 * 2. Else the explicit tool-level default (`bash: ask`), if set.
 * 3. Else, if this tool has *any* rules defined at all (just no default line),
 *    fall back to "ask" — declaring rules for a tool signals you care about
 *    gating it, so unmatched calls shouldn't silently run free. This is what
 *    lets a persona skip the redundant `bash: ask` boilerplate and just list
 *    allow/deny patterns.
 * 4. Else (tool has no rules and no default at all) -> undefined, meaning not
 *    gated by this persona.
 */
function resolvePermissionAction(
	permission: PersonaPermission,
	toolName: string,
	subject: string,
): PermissionAction | undefined {
	let matched: PermissionAction | undefined;
	let hasRuleForTool = false;
	for (const rule of permission.rules) {
		if (rule.tool !== toolName) continue;
		hasRuleForTool = true;
		if (globToRegExp(rule.pattern).test(subject)) matched = rule.action;
	}
	if (matched) return matched;
	if (permission.defaults[toolName]) return permission.defaults[toolName];
	return hasRuleForTool ? "ask" : undefined;
}

/** Human-readable one-liner for confirm dialogs / block reasons. */
function describeToolCall(toolName: string, input: unknown): string {
	const record = (input as Record<string, unknown>) ?? {};
	if (toolName === "bash" && typeof record.command === "string") {
		return record.command;
	}
	if (
		(toolName === "write" || toolName === "edit") &&
		typeof record.path === "string"
	) {
		return record.path;
	}
	try {
		return JSON.stringify(input);
	} catch {
		return "";
	}
}

function globalPersonaDir(): string {
	const base =
		process.env.PI_CODING_AGENT_DIR ?? join(homedir(), ".pi", "agent");
	return join(base, "personas");
}

function projectPersonaDir(cwd: string): string {
	return join(cwd, ".pi", "personas");
}

function parseFrontmatter(raw: string): {
	attrs: Record<string, string>;
	body: string;
	fmText: string;
} {
	const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
	if (!match) return { attrs: {}, body: raw.trim(), fmText: "" };
	const [, fm, body] = match;
	const attrs: Record<string, string> = {};
	for (const line of fm.split(/\r?\n/)) {
		const kv = line.match(/^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$/);
		if (!kv) continue;
		const [, key, value] = kv;
		attrs[key.trim()] = value.trim().replace(/^["']|["']$/g, "");
	}
	return { attrs, body: body.trim(), fmText: fm };
}

function loadPersonasFrom(
	dir: string,
	source: "global" | "project",
): Persona[] {
	if (!existsSync(dir)) return [];
	const personas: Persona[] = [];
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
		const path = join(dir, entry.name);
		const id = entry.name.slice(0, -3);
		try {
			const raw = readFileSync(path, "utf8");
			const { attrs, body, fmText } = parseFrontmatter(raw);
			const name = attrs.name?.trim() || id;
			personas.push({
				id,
				name,
				description: attrs.description ?? name,
				tools: attrs.tools
					? attrs.tools
							.split(",")
							.map((t) => t.trim())
							.filter(Boolean)
					: undefined,
				model: attrs.model,
				thinking: attrs.thinking,
				color: attrs.color,
				permission: parsePermissionBlock(fmText),
				systemPrompt: body,
				source,
				path,
			});
		} catch {
			// ignore unreadable file
		}
	}
	return personas;
}

function discoverPersonas(cwd: string): Persona[] {
	const global = loadPersonasFrom(globalPersonaDir(), "global");
	const project = loadPersonasFrom(projectPersonaDir(cwd), "project");
	const byId = new Map<string, Persona>();
	for (const p of global) byId.set(p.id, p);
	for (const p of project) byId.set(p.id, p); // project overrides global id
	return [...byId.values()].sort((a, b) => a.id.localeCompare(b.id));
}

export default function (pi: ExtensionAPI) {
	let active: Persona | undefined;
	let savedTools: string[] | undefined;

	function applyPersona(persona: Persona | undefined, ctx: ExtensionContext) {
		if (persona?.tools) {
			if (!savedTools) savedTools = pi.getActiveTools();
			pi.setActiveTools(persona.tools);
		} else if (!persona && savedTools) {
			pi.setActiveTools(savedTools);
			savedTools = undefined;
		}

		if (persona?.model) {
			const want = persona.model.toLowerCase();
			const [wantProvider, wantId] = want.includes("/")
				? want.split(/\/(.+)/)
				: [undefined, want];
			const available = ctx.modelRegistry.getAvailable();
			const model =
				available.find((m) => `${m.provider}/${m.id}`.toLowerCase() === want) ??
				available.find(
					(m) =>
						(!wantProvider || m.provider.toLowerCase() === wantProvider) &&
						m.id.toLowerCase().includes(wantId ?? want),
				);
			if (model) void pi.setModel(model);
			else
				ctx.ui.notify(
					`Persona: modelo no encontrado "${persona.model}"`,
					"warning",
				);
		}

		if (persona?.thinking) {
			pi.setThinkingLevel(persona.thinking as never);
		}

		active = persona;
		ctx.ui.setStatus("persona", persona ? ` ${persona.name}` : undefined);
		pi.events.emit("persona:changed", {
			id: persona?.id,
			name: persona?.name,
			color: persona?.color,
		});
	}

	/** Apply + persist + notify — the single path every persona change should go through. */
	function choosePersona(persona: Persona | undefined, ctx: ExtensionContext) {
		applyPersona(persona, ctx);
		pi.appendEntry(PERSONA_ENTRY_TYPE, {
			id: persona?.id,
			name: persona?.name,
			color: persona?.color,
		});
		ctx.ui.notify(
			persona
				? `Persona activa: ${persona.name}${persona.name === persona.id ? "" : ` (${persona.id})`}`
				: "Persona desactivada",
			"info",
		);
	}

	/** Cycle order: none -> persona1 -> persona2 -> ... -> none. */
	function cyclePersona(ctx: ExtensionContext) {
		const personas = discoverPersonas(ctx.cwd);
		if (personas.length === 0) {
			ctx.ui.notify(
				`Sin personas definidas. Crea .md en ${globalPersonaDir()} o ${projectPersonaDir(ctx.cwd)}`,
				"warning",
			);
			return;
		}
		const ids: Array<string | undefined> = [
			undefined,
			...personas.map((p) => p.id),
		];
		const currentIndex = ids.findIndex((id) => id === active?.id);
		const nextId = ids[(currentIndex + 1) % ids.length];
		const next = nextId
			? personas.find((p) => p.id === nextId)
			: undefined;
		choosePersona(next, ctx);
	}

	pi.on("session_start", async (_event, ctx) => {
		const lastEntry = [...ctx.sessionManager.getEntries()]
			.reverse()
			.find(
				(entry) =>
					entry.type === "custom" &&
					entry.customType === PERSONA_ENTRY_TYPE,
			);
		if (!lastEntry || lastEntry.type !== "custom") return;

		const data = lastEntry.data as
			| { id?: string; name?: string }
			| undefined;
		// Older entries stored the stable filename id in `name`. An entry with
		// neither field represents an explicitly deactivated persona.
		const id = data?.id ?? data?.name;
		if (!id) return;

		const persona = discoverPersonas(ctx.cwd).find((p) => p.id === id);
		if (!persona) return;

		if (!data?.id) {
			// Persist the unambiguous shape so kyubi-footer can restore the display
			// name even if its session_start handler runs after this one.
			pi.appendEntry(PERSONA_ENTRY_TYPE, {
				id: persona.id,
				name: persona.name,
				color: persona.color,
			});
		}
		applyPersona(persona, ctx);
	});

	pi.on("before_agent_start", (event) => {
		if (!active) return;
		return {
			systemPrompt: `${active.systemPrompt}\n\n---\n\n${event.systemPrompt}`,
		};
	});

	// OpenCode/Claude-Code-style per-tool gating: a persona can set
	// `permission` (flat defaults and/or nested allow/deny rule patterns) to
	// require confirmation or block specific tool calls outright, without
	// removing them from the tool set (so the model can still see/attempt them
	// and get a clear reason).
	pi.on("tool_call", async (event, ctx) => {
		const permission = active?.permission;
		if (!permission) return undefined;

		const toolName = event.toolName.toLowerCase();
		const subject = describeToolCall(event.toolName, event.input);
		const action = resolvePermissionAction(permission, toolName, subject);
		if (!action || action === "allow") return undefined;

		if (action === "deny") {
			return {
				block: true,
				reason: `Persona "${active!.name}": "${event.toolName}" con "${subject}" no permitido en este modo (deny).`,
			};
		}

		// action === "ask"
		if (!ctx.hasUI) {
			return {
				block: true,
				reason: `Persona "${active!.name}": "${event.toolName}" requiere confirmación (sin UI disponible).`,
			};
		}
		const allowed = await ctx.ui.confirm(
			`Persona "${active!.name}" pide confirmación`,
			`¿Permitir "${event.toolName}"?\n\n${subject}`,
		);
		if (!allowed) {
			return {
				block: true,
				reason: `Bloqueado por el usuario (persona "${active!.name}").`,
			};
		}
		return undefined;
	});

	// ctrl+space: cycle personas. Not in pi's reserved-keybinding list (unlike
	// shift+tab, which is app.thinking.cycle and gets silently dropped if an
	// extension tries to bind it), so this always fires regardless of what's
	// typed in the editor.
	pi.registerShortcut("ctrl+space", {
		description: "Cycle active persona",
		handler: async (ctx) => {
			cyclePersona(ctx);
		},
	});

	pi.registerCommand("persona", {
		description: "Switch the main session's persona/orchestrator personality",
		getArgumentCompletions: (prefix) => {
			const personas = discoverPersonas(process.cwd());
			const items = [
				{ value: "none", label: "none — clear active persona" },
				...personas.map((p) => ({
					value: p.id,
					label: `${p.id} — ${p.name}: ${p.description}`,
				})),
			];
			const filtered = items.filter((i) => i.value.startsWith(prefix));
			return filtered.length > 0 ? filtered : null;
		},
		handler: async (args, ctx) => {
			const personas = discoverPersonas(ctx.cwd);
			const arg = args.trim();

			if (arg) {
				if (arg === "none") {
					choosePersona(undefined, ctx);
					return;
				}
				const persona = personas.find((p) => p.id === arg);
				if (!persona) {
					ctx.ui.notify(`Persona no encontrada: ${arg}`, "error");
					return;
				}
				choosePersona(persona, ctx);
				return;
			}

			if (personas.length === 0) {
				ctx.ui.notify(
					`Sin personas definidas. Crea .md en ${globalPersonaDir()} o ${projectPersonaDir(ctx.cwd)}`,
					"warning",
				);
				return;
			}

			const options = [
				"none — clear active persona",
				...personas.map(
					(p) =>
						`${p.id} — ${p.name}: ${p.description}${p.source === "project" ? " [proyecto]" : ""}`,
				),
			];
			const choice = await ctx.ui.select("Elige una persona:", options);
			if (!choice) return;

			if (choice.startsWith("none")) {
				choosePersona(undefined, ctx);
				return;
			}
			const id = choice.split(" — ")[0];
			const persona = personas.find((p) => p.id === id);
			if (persona) choosePersona(persona, ctx);
		},
	});
}
