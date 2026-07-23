-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local map = vim.keymap.set

local function terminal_opts()
  local tab = vim.api.nvim_get_current_tabpage()
  return {
    win = {
      style = "terminal",
      position = "float",
      border = "rounded",
    },
    start_insert = false,
    auto_insert = false,
    env = { NVIM_TAB_ID = tostring(tab) },
  }
end

-- stylua: ignore start
map("n", "<leader>oc", function()
  local opts = terminal_opts()
  opts.count = vim.fn.getpid()
  Snacks.terminal.toggle("opencode", opts)
end, { desc = "Toggle OpenCode" })
map("n", "<leader>tt", function() Snacks.terminal.toggle({ "tmux", "new-session", "-A", "-s", "nvim-" .. vim.fn.getpid() .. "-" .. vim.api.nvim_get_current_tabpage() }, terminal_opts()) end, { desc = "Toggle Terminal (tmux)" })
-- stylua: ignore end
