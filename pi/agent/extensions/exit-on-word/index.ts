import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("input", async (event, ctx) => {
    if (event.text.trim().toLowerCase() !== "exit") {
      return { action: "continue" };
    }

    ctx.ui.notify("Good bye! 󱠡", "info");

    await new Promise((resolve) => setTimeout(resolve, 500));

    ctx.shutdown();
    return { action: "handled" };
  });
}
