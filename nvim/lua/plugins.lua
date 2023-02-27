vim.cmd [[packadd packer.nvim]]

return require('packer').startup(function(use)
  use 'wbthomason/packer.nvim'

  -- Bottom bar
  use {
    'nvim-lualine/lualine.nvim',
    requires = { 'kyazdani42/nvim-web-devicons', opt = true }
  }

  -- Theme
  use "joshdick/onedark.vim"

  -- Telescope
  use {
    'nvim-telescope/telescope.nvim', tag = '0.1.1',
    requires = { { 'nvim-lua/plenary.nvim' } }
  }

  -- NerdTree
  use {
    'nvim-tree/nvim-tree.lua',
    requires = {
      'nvim-tree/nvim-web-devicons', -- optional, for file icons
    },
    tag = 'nightly' -- optional, updated every week. (see issue #1193)
  }

  use 'kyazdani42/nvim-web-devicons'

  -- Treesitter
  use {
    'nvim-treesitter/nvim-treesitter',
    run = ':TSUpdate'
  }

  -- lsp
  use 'neovim/nvim-lspconfig'

  -- mason
  use {
    "williamboman/mason.nvim",
    "williamboman/mason-lspconfig.nvim"
  }

  -- null-ls
  use 'jose-elias-alvarez/null-ls.nvim'

  -- comp
  use 'hrsh7th/cmp-buffer' -- nvim-cmp source for buffer words
  use 'hrsh7th/cmp-nvim-lsp' -- nvim-cmp source for neovim's built-in LSP
  use 'hrsh7th/nvim-cmp' -- Completion
  use 'L3MON4D3/LuaSnip'

  --
  use 'onsails/lspkind-nvim' -- vscode-like pictograms

  -- autoclose tags
  use 'windwp/nvim-ts-autotag'
  use {
    'windwp/nvim-autopairs',
    config = function() require("nvim-autopairs").setup {} end
  }

  -- transparent
  use 'xiyaowong/nvim-transparent'
end)
