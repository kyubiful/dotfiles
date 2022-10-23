local M = {}

M.keymaps = {
  n = {
    ['<Leader>ss'] = {':split<Return><C-w>w'},
    ['<Leader>sv'] = {':vsplit<Return><C-w>w'},
    ['<Leader>mf'] = {'mF:%!eslint_d --stdin --fix-to-stdout --stdin-filename %<CR>`F'},
  },
  i = {

  }
}

return M
