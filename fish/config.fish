set fish_greeting ""

set -gx TERM xterm-256color

# theme
set -g theme_color_scheme terminal-dark
set -g fish_prompt_pwd_dir_length 1
set -g theme_display_user yes
set -g theme_hide_hostname no
set -g theme_hostname always

# aliases
alias ls "ls -p -G"
alias la "ls -A"
alias ll "ls -l"
alias lla "ll -A"
alias g git
alias c claude
alias claude-yolo "claude --dangerously-skip-permissions"

command -qv nvim && alias vim nvim

set -gx EDITOR nvim

set -gx PATH bin $PATH
set -gx PATH ~/bin $PATH
set -gx PATH ~/.local/bin $PATH
fish_add_path ~/.scripts

# NodeJS
set -gx PATH node_modules/.bin $PATH

# fnm (Node version manager)
command -qv fnm && fnm env --use-on-cd --shell fish | source

# Go
set -g GOPATH $HOME/go
set -gx PATH $GOPATH/bin $PATH

switch (uname)
    case Darwin
        source (dirname (status --current-filename))/config-osx.fish
    case Linux
        source (dirname (status --current-filename))/config-linux.fish
    case '*'
        source (dirname (status --current-filename))/config-windows.fish
end

set LOCAL_CONFIG (dirname (status --current-filename))/config-local.fish
if test -f $LOCAL_CONFIG
    source $LOCAL_CONFIG
end

set -gx FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS \
    --highlight-line \
    --info=inline-right \
    --ansi \
    --layout=reverse \
    --border=none \
    --color=bg+:#002c38 \
    --color=bg:#001419 \
    --color=border:#063540 \
    --color=fg:#9eabac \
    --color=gutter:#001419 \
    --color=header:#c94c16 \
    --color=hl+:#c94c16 \
    --color=hl:#c94c16 \
    --color=info:#637981 \
    --color=marker:#c94c16 \
    --color=pointer:#c94c16 \
    --color=prompt:#c94c16 \
    --color=query:#9eabac:regular \
    --color=scrollbar:#063540 \
    --color=separator:#063540 \
    --color=spinner:#c94c16

# fish theme
# solarized-osaka Color Palette
set -l foreground 839395
set -l selection 1a6397
set -l base01 576d74
set -l red db302d
set -l orange c94c16
set -l yellow b28500
set -l green 849900
set -l purple 6d71c4
set -l cyan 29a298
set -l pink d23681

# Syntax Highlighting Colors
set -g fish_color_normal $foreground
set -g fish_color_command $cyan
set -g fish_color_keyword $pink
set -g fish_color_quote $yellow
set -g fish_color_redirection $foreground
set -g fish_color_end $orange
set -g fish_color_error $red
set -g fish_color_param $purple
set -g fish_color_comment $base01
set -g fish_color_selection --background=$selection
set -g fish_color_search_match --background=$selection
set -g fish_color_operator $green
set -g fish_color_escape $pink
set -g fish_color_autosuggestion $base01

# Completion Pager Colors
set -g fish_pager_color_progress $base01
set -g fish_pager_color_prefix $cyan
set -g fish_pager_color_completion $foreground
set -g fish_pager_color_description $base01
set -g fish_pager_color_selected_background --background=$selection
