import type { ExtensionAPI, Theme } from "@earendil-works/pi-coding-agent";
import { VERSION } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";
import { basename } from "node:path";

/** Kitsune ASCII art, provided as-is by the user. */
const KITSUNE_ART = [" \\    /\\", "  )  ( ')", " (  /  )", "  \\(__)|"];

/** "kyubi" block-font wordmark, provided as-is by the user. */
const KYUBI_WORDMARK = [
	"▌     ▌ ▘     ▌  ",
	"▙▘▌▌▌▌▛▌▌▛▘▛▌▛▌█▌",
	"▛▖▙▌▙▌▙▌▌▙▖▙▌▙▌▙▖",
	"  ▄▌",
];
const WORDMARK_WIDTH = Math.max(...KYUBI_WORDMARK.map((line) => line.length));

/**
 * Colorize the "kyubi" wordmark next to the kitsune art (wordmark on the
 * left, kitsune on the right), both with the theme's accent token.
 */
function getKitsuneLogo(theme: Theme): string[] {
	return KITSUNE_ART.map((line, i) => {
		const wordmarkLine = (KYUBI_WORDMARK[i] ?? "").padEnd(WORDMARK_WIDTH, " ");
		return theme.fg("accent", `${wordmarkLine}  ${line}`);
	});
}

/**
 * Center a block of lines as a single unit: every line gets the same left
 * padding, computed from the widest line, so the art's internal alignment
 * (e.g. the kitsune's shape) is preserved instead of wobbling row by row.
 */
function centerBlock(lines: string[], width: number): string[] {
	const maxVisible = Math.max(...lines.map((line) => visibleWidth(line)));
	const leftPad = " ".repeat(Math.max(0, Math.floor((width - maxVisible) / 2)));
	return lines.map((line) => leftPad + line);
}

export default function (pi: ExtensionAPI) {
	pi.on("session_start", async (_event, ctx) => {
		if (ctx.mode !== "tui") return;

		ctx.ui.setHeader((_tui, theme) => {
			return {
				invalidate() {},
				render(width: number): string[] {
					const logoLines = centerBlock(getKitsuneLogo(theme), width);
					const folder = basename(ctx.cwd);
					const subtitle =
						theme.fg("muted", folder) +
						theme.fg("dim", ` · pi v${VERSION}`);
					const [centeredSubtitle] = centerBlock([subtitle], width);

					return [...logoLines, "", centeredSubtitle].map((line) =>
						truncateToWidth(line, width),
					);
				},
			};
		});
	});

	pi.registerCommand("builtin-header", {
		description: "Restore built-in pi header with keybinding hints",
		handler: async (_args, ctx) => {
			ctx.ui.setHeader(undefined);
			ctx.ui.notify("Built-in header restored", "info");
		},
	});
}
