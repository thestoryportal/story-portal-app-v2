#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract all needed values
user=$(whoami)
hostname=$(hostname -s)
current_dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd')
model_name=$(echo "$input" | jq -r '.model.display_name // .model.id')
output_style=$(echo "$input" | jq -r '.output_style.name // empty')
context_remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
vim_mode=$(echo "$input" | jq -r '.vim.mode // empty')
agent_name=$(echo "$input" | jq -r '.agent.name // empty')

# Get short directory name (last component)
short_dir=$(basename "$current_dir")

# Get git status (skip optional locks for performance)
git_info=""
if git -C "$current_dir" rev-parse --git-dir > /dev/null 2>&1; then
    # Get branch name
    branch=$(git -C "$current_dir" -c core.useBuiltinFSMonitor=false symbolic-ref --short HEAD 2>/dev/null || echo "detached")

    # Get status counts (skip locks)
    git_status=$(git -C "$current_dir" -c core.useBuiltinFSMonitor=false status --porcelain 2>/dev/null)
    modified=$(echo "$git_status" | grep -c "^ M" || echo "0")
    added=$(echo "$git_status" | grep -c "^A\|^M" || echo "0")
    deleted=$(echo "$git_status" | grep -c "^ D\|^D" || echo "0")
    untracked=$(echo "$git_status" | grep -c "^??" || echo "0")

    # Build git info string
    git_info="[$branch"
    [ "$modified" -gt 0 ] && git_info="$git_info ~$modified"
    [ "$added" -gt 0 ] && git_info="$git_info +$added"
    [ "$deleted" -gt 0 ] && git_info="$git_info -$deleted"
    [ "$untracked" -gt 0 ] && git_info="$git_info ?$untracked"
    git_info="$git_info]"
fi

# Build status line components
components=()

# User and hostname
components+=("$user@$hostname")

# Current directory
components+=("$short_dir")

# Model and output style
if [ -n "$output_style" ]; then
    components+=("$model_name ($output_style)")
else
    components+=("$model_name")
fi

# Context remaining
if [ -n "$context_remaining" ]; then
    # Color code based on remaining percentage
    if (( $(echo "$context_remaining < 20" | bc -l 2>/dev/null || echo 0) )); then
        components+=("ctx: ${context_remaining}% LOW")
    elif (( $(echo "$context_remaining < 50" | bc -l 2>/dev/null || echo 0) )); then
        components+=("ctx: ${context_remaining}%")
    else
        components+=("ctx: ${context_remaining}%")
    fi
fi

# Git status
[ -n "$git_info" ] && components+=("$git_info")

# Vim mode (if enabled)
[ -n "$vim_mode" ] && components+=("vim:$vim_mode")

# Agent name (if running with --agent)
[ -n "$agent_name" ] && components+=("agent:$agent_name")

# Join components with " | " separator and print
printf "%s" "${components[0]}"
for ((i=1; i<${#components[@]}; i++)); do
    printf " | %s" "${components[$i]}"
done
printf "\n"
