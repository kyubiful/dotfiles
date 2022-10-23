return {
  -- Tmux
  ['benmills/vimux'] = {},
  ['christoomey/vim-tmux-navigator'] = {},
  -- Transparent
  ['xiyaowong/nvim-transparent'] = {},
  ['aserowy/tmux.nvim'] = {
    config = function() require("tmux").setup() end
  },
  ["neovim/nvim-lspconfig"] = {
    config = function()
      require "plugins.configs.lspconfig"
      require "custom.plugins.lspconfig"
    end,
  },
  ["jose-elias-alvarez/null-ls.nvim"] = {
      after = "nvim-lspconfig",
      config = function()
         require "custom.plugins.null-ls"
      end,
 }
}
