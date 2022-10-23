-- First read our docs (completely) then check the example_config repo

local M = {}

M.plugins = require "custom.plugins"
M.mappings = require "custom.mappings"

M.ui = {
  theme = "onedark",
}

-- Transparent
vim.g.transparent_enabled = true
vim.wo.relativenumber = true

return M
