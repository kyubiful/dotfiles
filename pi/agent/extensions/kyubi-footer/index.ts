import type { AssistantMessage } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";
import { basename } from "node:path";

const formatNumber = (value: number) =>
	value < 1_000 ? `${value}` : `${(value / 1_000).toFixed(1)}k`;

/**
 * Color per thinking level, independent from the active pi theme's
 * thinkingOff/Minimal/.../Max tokens (those are neutralized to a single
 * flat border color so the editor border no longer changes with thinking).
 * These hex values mirror the palette solarized-osaka used to use for that
 * purpose, just relocated here so the footer keeps a colorized indicator.
 */
const THINKING_COLORS: Record<string, string> = {
	off: "#586e74",
	minimal: "#278bd3",
	low: "#2aa298",
	medium: "#6d72c5",
	high: "#d33682",
	xhigh: "#dc312e",
	max: "#ffbf00",
};

/** 24-bit ANSI foreground for a raw hex color, e.g. "#ff8800". */
function hexFg(hex: string, text: string): string {
	const clean = hex.replace("#", "");
	const r = Number.parseInt(clean.slice(0, 2), 16);
	const g = Number.parseInt(clean.slice(2, 4), 16);
	const b = Number.parseInt(clean.slice(4, 6), 16);
	return `\x1b[38;2;${r};${g};${b}m${text}\x1b[39m`;
}

/**
 * Colorize `text` with `color`, which is either a raw hex string ("#ff8800")
 * or a pi theme token name ("success", "accent", "syntaxKeyword", ...).
 * Falls back to the "accent" token when `color` is unset or an unknown token.
 */
function colorizePersona(
	theme: { fg: (color: string, text: string) => string },
	color: string | undefined,
	text: string,
): string {
	if (color?.startsWith("#")) return hexFg(color, text);
	if (color) {
		try {
			return theme.fg(color, text);
		} catch {
			// unknown token name — fall through to default accent
		}
	}
	return theme.fg("accent", text);
}

export default function (pi: ExtensionAPI) {
	pi.on("session_start", (_event, ctx) => {
		let personaName: string | undefined;
		let personaColor: string | undefined;
		for (const entry of ctx.sessionManager.getEntries()) {
			if (entry.type === "custom" && entry.customType === "persona-active") {
				const data = entry.data as
					| { name?: string; color?: string }
					| undefined;
				personaName = data?.name;
				personaColor = data?.color;
			}
		}

		ctx.ui.setFooter((tui, theme, footerData) => {
			const unsubscribe = footerData.onBranchChange(() => tui.requestRender());
			const unsubscribePersona = pi.events.on("persona:changed", (data) => {
				const payload = data as { name?: string; color?: string };
				personaName = payload.name;
				personaColor = payload.color;
				tui.requestRender();
			});

			return {
				dispose: () => {
					unsubscribe();
					unsubscribePersona();
				},
				invalidate() {},
				render(width: number) {
					const folder = basename(ctx.cwd);

					let inputTokens = 0;
					let outputTokens = 0;
					let totalCost = 0;

					for (const entry of ctx.sessionManager.getBranch()) {
						if (entry.type !== "message" || entry.message.role !== "assistant")
							continue;

						const message = entry.message as AssistantMessage;
						inputTokens += message.usage.input;
						outputTokens += message.usage.output;
						totalCost += message.usage.cost.total;
					}

					const context = ctx.getContextUsage();
					const contextTokens = context?.tokens ?? 0;
					const contextWindow = ctx.model?.contextWindow ?? 0;
					const contextPercent =
						contextWindow > 0
							? Math.round((contextTokens / contextWindow) * 100)
							: 0;

					const metrics = theme.fg(
						"accent",
						` ${formatNumber(inputTokens)}   ${formatNumber(outputTokens)}`,
					);
					const cost = theme.fg("success", `  $${totalCost.toFixed(3)}`);
					const usage = theme.fg(
						"warning",
						`󰍛 ${formatNumber(contextTokens)}/${formatNumber(contextWindow)} (${contextPercent}%)`,
					);
					const branch = footerData.getGitBranch();
					const project = theme.fg("dim", branch ? ` ${branch}` : "");
					const model = theme.fg("muted", `󰚩 ${ctx.model?.id ?? "sin modelo"}`);

					const thinkingLevel = pi.getThinkingLevel();
					const thinkingLabel =
						thinkingLevel === "off" ? "thinking off" : thinkingLevel;
					const thinkingPart = ctx.model?.reasoning
						? hexFg(
								THINKING_COLORS[thinkingLevel] ?? THINKING_COLORS.off,
								`󰧑 ${thinkingLabel}`,
							)
						: "";

					const folderPart = ` ${folder}`;
					const personaPart = personaName
						? colorizePersona(theme, personaColor, ` ${personaName}`)
						: "";
					const firstLinePadding = personaName
						? " ".repeat(
								Math.max(
									1,
									width - visibleWidth(folderPart) - visibleWidth(personaPart),
								),
							)
						: "";
					const firstLine = `${folderPart}${firstLinePadding}${personaPart}`;

					const secondLineLeft = `${metrics}  ${cost}  ${usage}`;
					const secondLinePadding = thinkingPart
						? " ".repeat(
								Math.max(
									1,
									width -
										visibleWidth(secondLineLeft) -
										visibleWidth(thinkingPart),
								),
							)
						: "";
					const secondLine = `${secondLineLeft}${secondLinePadding}${thinkingPart}`;

					const padding = " ".repeat(
						Math.max(1, width - visibleWidth(project) - visibleWidth(model)),
					);
					const thirdLine = `${project}${padding}${model}`;

					return [
						truncateToWidth(firstLine, width),
						truncateToWidth(secondLine, width),
						truncateToWidth(thirdLine, width),
					];
				},
			};
		});
	});
}
