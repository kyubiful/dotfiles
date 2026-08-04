/**
 * /persona — OpenCode-style "personality" switcher for the main pi session.
 *
 * Define personas as markdown files with YAML-ish frontmatter:
 *
 *   ~/.pi/agent/personas/<name>.md   (global, all projects)
 *   .pi/personas/<name>.md           (project-local, overrides global of same name)
 *
 * Frontmatter fields (all optional):
 *   description: shown in the /persona picker
 *   tools: comma list of built-in tool names to restrict to (e.g. "read, bash, grep")
 *          omit to leave the current tool set untouched
 *   model: provider/modelId or fuzzy name ("sonnet", "haiku")
 *   thinking: off|minimal|low|medium|high|xhigh|max
 *   color: footer badge color — either a pi theme token ("success", "warning",
 *          "accent", "syntaxKeyword", ...) or a raw hex color ("#ff8800")
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

interface Persona {
	name: string;
	description: string;
	tools?: string[];
	model?: string;
	thinking?: string;
	color?: string;
	systemPrompt: string;
	source: "global" | "project";
	path: string;
}

const PERSONA_ENTRY_TYPE = "persona-active";

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
} {
	const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
	if (!match) return { attrs: {}, body: raw.trim() };
	const [, fm, body] = match;
	const attrs: Record<string, string> = {};
	for (const line of fm.split(/\r?\n/)) {
		const kv = line.match(/^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$/);
		if (!kv) continue;
		const [, key, value] = kv;
		attrs[key.trim()] = value.trim().replace(/^["']|["']$/g, "");
	}
	return { attrs, body: body.trim() };
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
		const name = entry.name.slice(0, -3);
		try {
			const raw = readFileSync(path, "utf8");
			const { attrs, body } = parseFrontmatter(raw);
			personas.push({
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
	const byName = new Map<string, Persona>();
	for (const p of global) byName.set(p.name, p);
	for (const p of project) byName.set(p.name, p); // project overrides global
	return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
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
			name: persona?.name,
			color: persona?.color,
		});
	}

	/** Apply + persist + notify — the single path every persona change should go through. */
	function choosePersona(persona: Persona | undefined, ctx: ExtensionContext) {
		applyPersona(persona, ctx);
		pi.appendEntry(PERSONA_ENTRY_TYPE, {
			name: persona?.name,
			color: persona?.color,
		});
		ctx.ui.notify(
			persona ? `Persona activa: ${persona.name}` : "Persona desactivada",
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
		const names: Array<string | undefined> = [
			undefined,
			...personas.map((p) => p.name),
		];
		const currentIndex = names.findIndex((n) => n === active?.name);
		const nextName = names[(currentIndex + 1) % names.length];
		const next = nextName
			? personas.find((p) => p.name === nextName)
			: undefined;
		choosePersona(next, ctx);
	}

	pi.on("session_start", async (_event, ctx) => {
		for (const entry of ctx.sessionManager.getEntries()) {
			if (entry.type === "custom" && entry.customType === PERSONA_ENTRY_TYPE) {
				const name = (entry.data as { name?: string } | undefined)?.name;
				if (name) {
					const persona = discoverPersonas(ctx.cwd).find(
						(p) => p.name === name,
					);
					if (persona) applyPersona(persona, ctx);
				}
			}
		}
	});

	pi.on("before_agent_start", (event) => {
		if (!active) return;
		return {
			systemPrompt: `${active.systemPrompt}\n\n---\n\n${event.systemPrompt}`,
		};
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
					value: p.name,
					label: `${p.name} — ${p.description}`,
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
				const persona = personas.find((p) => p.name === arg);
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
						`${p.name} — ${p.description}${p.source === "project" ? " [proyecto]" : ""}`,
				),
			];
			const choice = await ctx.ui.select("Elige una persona:", options);
			if (!choice) return;

			if (choice.startsWith("none")) {
				choosePersona(undefined, ctx);
				return;
			}
			const name = choice.split(" — ")[0];
			const persona = personas.find((p) => p.name === name);
			if (persona) choosePersona(persona, ctx);
		},
	});
}
