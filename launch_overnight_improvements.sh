#!/bin/bash
# Launch overnight improvement process

cd /Users/johnmonty/agentcoord

# Ensure API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    echo "Set it with: export ANTHROPIC_API_KEY='your-key'"
    echo "Or add to ~/.zshrc: export ANTHROPIC_API_KEY='your-key'"
    exit 1
fi

# Ensure Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not running"
    echo "Start it with: brew services start redis"
    exit 1
fi

# Launch overnight coordinator
echo "🌙 Launching overnight improvement process..."
python3 scripts/overnight_improvement_coordinator.py

echo ""
echo "✅ Overnight process started!"
echo "Monitor with: agentcoord dashboard"
echo ""
echo "Workers are running autonomously. Sleep well! 😴"
