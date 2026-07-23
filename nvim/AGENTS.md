# AGENTS.md — Neovim Configuration

This file is for agentic coding agents working in this repository. It documents
conventions, tooling, and patterns used in this Neovim configuration.

---

## Overview

This is a personal Neovim configuration built on top of **LazyVim** (the
distribution by folke). The user layer is intentionally minimal — all language
support and most defaults are delegated to LazyVim's curated "extras" system.
The codebase is 100% Lua with no VimScript.

**Plugin manager:** `lazy.nvim` (bootstrapped in `lua/config/lazy.lua`)
**Base distro:** `LazyVim/LazyVim` (loaded as a lazy.nvim plugin spec)

---

## Directory Layout

```
nvim/
├── init.lua                  # Entry point — only bootstraps lua/config/lazy.lua
├── lazy-lock.json            # Pinned plugin versions (do not edit manually)
├── lazyvim.json              # LazyVim extras enabled for this config
├── stylua.toml               # StyLua formatter settings
├── .neoconf.json             # lua_ls / neoconf project settings
└── lua/
    ├── config/
    │   ├── lazy.lua          # Plugin manager bootstrap + lazy.nvim setup
    │   ├── options.lua       # vim.opt overrides
    │   ├── keymaps.lua       # vim.keymap.set overrides
    │   └── autocmds.lua      # vim.api.nvim_create_autocmd overrides
    └── plugins/
        ├── example.lua       # LazyVim reference template (returns {} — no-op)
        ├── opacity.lua       # transparent.nvim config
        ├── themes.lua        # Colorscheme plugins and active scheme
        └── snacks.lua        # snacks.nvim picker / explorer config
```

Add new plugin customizations as separate files under `lua/plugins/`.
Each file must return a list (table) of lazy.nvim plugin specs.

---

## Build / Lint / Test Commands

This is a personal editor configuration — there is no build step, no test
suite, and no CI pipeline.

| Task | Command |
|------|---------|
| Format Lua files | `stylua lua/` |
| Format a single file | `stylua lua/plugins/snacks.lua` |
| Check formatting without writing | `stylua --check lua/` |
| Validate Lua syntax | `luac -p lua/plugins/snacks.lua` |

> There are no automated tests. Correctness is verified by launching Neovim.
> To run Neovim with a clean slate for debugging: `nvim --clean` or set up a
> `NVIM_APPNAME`-isolated profile.

---

## Code Formatter — StyLua

All Lua is formatted with **StyLua**. Settings are in `stylua.toml`:

```toml
indent_type = "Spaces"
indent_width = 2
column_width = 120
```

Key rules:
- **2 spaces** for indentation — never tabs.
- **120-character** line width — wider than the 80/100 common defaults.
- Use `-- stylua: ignore` on the line before a statement to suppress formatting
  for that statement only. This is used to keep short one-liner lambdas on a
  single line:

```lua
-- stylua: ignore
{ "<leader>fp", function() require("telescope.builtin").find_files() end, desc = "Find Plugin File" },
```

Always run `stylua lua/` before committing changes.

---

## Code Style Guidelines

### Lua Idioms

Use short local aliases for frequently accessed namespaces:

```lua
local opt = vim.opt
local g   = vim.g
local map = vim.keymap.set
```

Prefer explicit `local` scoping for every variable and function.

### Module Structure

Each file in `lua/plugins/` is a self-contained module that returns a flat list
of lazy.nvim plugin specs. Do not define a module table (`M = {}`), do not
`require` other internal modules.

```lua
-- lua/plugins/my-plugin.lua
return {
  {
    "author/plugin-name",
    -- spec fields here
  },
}
```

### Imports / Requires

- **Never `require` at the top level of a plugin file.** All `require` calls
  must be deferred inside `opts` functions, `init`, `config`, or `keys`
  callbacks. This preserves lazy-loading and avoids startup cost.

```lua
-- CORRECT — deferred inside callback
opts = function(_, opts)
  opts.sources = opts.sources or {}
  table.insert(opts.sources, { name = "emoji" })
end,

-- CORRECT — deferred inside keys
keys = {
  { "<leader>fp", function() require("telescope.builtin").find_files() end },
},

-- WRONG — eager, top-level require
local telescope = require("telescope.builtin")
```

### Plugin Configuration Patterns

Choose the appropriate lazy.nvim configuration style:

**1. Simple opts table** — merge/override plugin defaults:
```lua
opts = {
  picker = {
    layout = { preset = "default" },
  },
},
```

**2. opts as a function** — extend parent defaults without replacing them:
```lua
opts = function(_, opts)
  table.insert(opts.sources, { name = "emoji" })
end,
```

**3. `config = true`** — use the plugin's built-in setup with no extra options:
```lua
{ "tribela/transparent.nvim", event = "VimEnter", config = true }
```

**4. Override the LazyVim distro** — patch LazyVim's own settings:
```lua
{ "LazyVim/LazyVim", opts = { colorscheme = "catppuccin-mocha" } }
```

### Keymaps

Define keymaps via the `keys` table in a plugin spec (preferred — lazy-loaded):

```lua
keys = {
  { "<leader>xx", "<cmd>Trouble<cr>", desc = "Toggle Trouble" },
},
```

For keymaps not tied to a plugin, use `lua/config/keymaps.lua`:

```lua
vim.keymap.set("n", "<leader>co", "TypescriptOrganizeImports", { buffer = buffer, desc = "Organize Imports" })
```

Always include a `desc` string. This powers `which-key.nvim` documentation.

### Autocmds

Define autocmds in `lua/config/autocmds.lua` or inside a plugin's `init`
callback. To remove a LazyVim default autocmd:

```lua
vim.api.nvim_del_augroup_by_name("lazyvim_wrap_spell")
```

### Error Handling

The only place that requires explicit error handling is the lazy.nvim bootstrap
in `lua/config/lazy.lua`. Follow the existing pattern there:

```lua
if vim.v.shell_error ~= 0 then
  vim.api.nvim_echo({
    { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
    { out, "WarningMsg" },
    { "\nPress any key to exit..." },
  }, true, {})
  vim.fn.getchar()
  os.exit(1)
end
```

Plugin configuration code does not need defensive error handling — lazy.nvim
handles plugin load failures gracefully.

---

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Lua files | `snake_case` | `snacks.lua`, `opacity.lua` |
| Local variables | `snake_case` | `local my_var` |
| Local aliases | short, single letter or two | `opt`, `map`, `g` |
| Plugin spec keys | as documented by lazy.nvim | `opts`, `init`, `config`, `keys`, `event` |
| Keymap descriptions | Title Case short phrase | `"Find Plugin File"`, `"Organize Imports"` |

---

## LazyVim Extras

Language and tool support is enabled via LazyVim's extras system in
`lazyvim.json` — do not hand-configure LSPs or formatters that are already
covered by an extra. Currently enabled extras include TypeScript, Python, Go,
Zig, Astro, Terraform, SQL, Docker, Tailwind, Prisma, Markdown, Biome,
Prettier, Black, ESLint, Copilot, DAP, and more.

To enable a new extra, add it to `lazyvim.json` under `"extras"`.

---

## What NOT to Do

- Do not add `require` calls at the top level of `lua/plugins/` files.
- Do not use `vim.cmd("set ...")` — use `vim.opt` instead.
- Do not edit `lazy-lock.json` by hand — use `:Lazy update` / `:Lazy restore`.
- Do not add VimScript (`.vim` files) — keep everything in Lua.
- Do not configure a language server manually if a LazyVim extra already covers it.
- Do not use tabs for indentation — StyLua enforces spaces.
