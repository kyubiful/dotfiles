if test -x /opt/homebrew/bin/brew
    eval (/opt/homebrew/bin/brew shellenv)
    # Persist as a universal path so conf.d/*.fish (sourced before
    # config.fish) can find Homebrew binaries like fnm from the first tab.
    fish_add_path -U /opt/homebrew/bin /opt/homebrew/sbin
end

if type -q eza
    alias ll "eza -l -g --icons"
    alias lla "ll -a"
    alias ls "eza --icons"
    alias la "ls --icons -a"
end

# Inkdrop
set -gx INKDROP_HOME ~/.inkdrop

# Fzf
set -g FZF_PREVIEW_FILE_CMD "bat --style=numbers --color=always --line-range :500"
set -g FZF_LEGACY_KEYBINDINGS 0
