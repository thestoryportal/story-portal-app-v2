#!/bin/bash

echo "=== Claude Code Command Loading Diagnostic ==="
echo

# Check filesystem type
echo "1. Filesystem Type:"
diskutil info "/Volumes/Extreme SSD" | grep -E "File System|Volume Name" || df -T "$(pwd)"
echo

# Check inode support
echo "2. Inode Information:"
df -i "$(pwd)" | tail -1
echo

# List command files with inodes
echo "3. Command Files and Inodes:"
ls -li .claude/commands/*.md 2>/dev/null | grep -v "^\._" | awk '{print $1 "\t" $NF}'
echo

# Check for duplicate inodes
echo "4. Duplicate Inode Check:"
inode_list=$(ls -i .claude/commands/*.md 2>/dev/null | grep -v "^\._" | awk '{print $1}' | sort)
duplicates=$(echo "$inode_list" | uniq -d)
if [ -z "$duplicates" ]; then
    echo "No duplicate inodes found (but may still have issues on ExFAT)"
else
    echo "WARNING: Duplicate inodes detected:"
    echo "$duplicates"
fi
echo

# Check Claude Code process
echo "5. Claude Code Process:"
if pgrep -f "claude.*--dangerously-skip-permissions" > /dev/null; then
    echo "Claude Code is running"
    ps aux | grep "claude.*--dangerously-skip-permissions" | grep -v grep | head -1
else
    echo "Claude Code is NOT running"
fi
echo

# Check debug log
echo "6. Latest Debug Log Check:"
if [ -f ~/.claude/debug/latest ]; then
    echo "Checking for command loading errors..."
    grep -i "duplicate\|skipping.*command\|commands.*loaded" ~/.claude/debug/latest 2>/dev/null | tail -5
else
    echo "No debug log found"
fi
echo

echo "=== RECOMMENDATION ==="
if diskutil info "/Volumes/Extreme SSD" 2>/dev/null | grep -q "ExFAT\|FAT"; then
    echo "⚠️  Project is on ExFAT/FAT filesystem"
    echo "   Commands may not load reliably due to inode issues"
    echo
    echo "SOLUTIONS:"
    echo "  1. Move project to APFS-formatted drive (recommended)"
    echo "  2. Use MCP tools directly: mcp__platform-services__browse_services()"
    echo "  3. Try different command names and restart Claude Code"
else
    echo "✅ Filesystem appears to support proper inodes"
    echo "   If commands still don't load, check file permissions and YAML frontmatter"
fi
