local keymap = vim.keymap

keymap.set('n', 'nt', ':NvimTreeToggle<Return>')

-- telescope
keymap.set('n', 'sf', ':Telescope find_files<Return>')
keymap.set('n', 'sb', ':Telescope buffers<Return>')

-- Split window
keymap.set('n', 'ss', ':split<Return><C-w>w')
keymap.set('n', 'sv', ':vsplit<Return><C-w>w')

-- Move window
keymap.set('n', '<Tab>', '<C-w>w')
keymap.set('', '<C-h>', '<C-w>h')
keymap.set('', '<C-k>', '<C-w>k')
keymap.set('', '<C-j>', '<C-w>j')
keymap.set('', '<C-l>', '<C-w>l')
