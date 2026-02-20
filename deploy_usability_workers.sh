#!/bin/bash
# Deploy usability improvement workers using agentcoord

set -e

WORKSPACE=~/agentcoord/workspace/usability-improvements
NUM_WORKERS=3

echo "════════════════════════════════════════════════════════════════"
echo "  DEPLOYING USABILITY IMPROVEMENT WORKERS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Create workspace
mkdir -p "$WORKSPACE/logs"

# Run coordinator to create tasks
echo "📋 Creating tasks with coordinator..."
cd ~/agentcoord
python3 usability_improvements_coordinator.py

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  DEPLOYING $NUM_WORKERS LLM WORKERS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Deploy workers
for i in $(seq 1 $NUM_WORKERS); do
    WORKER_NAME="USABILITY-WORKER-$i" \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    nohup python3 ~/agentcoord/workers/usability_implementation_worker.py \
        > "$WORKSPACE/logs/worker-$i.log" 2>&1 &

    WORKER_PID=$!
    echo "✅ Worker $i deployed (PID: $WORKER_PID)"
    sleep 1
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Workers: $NUM_WORKERS"
echo "Database: $WORKSPACE/tasks.db"
echo "Logs: $WORKSPACE/logs/"
echo ""
echo "Monitor progress:"
echo "  tail -f $WORKSPACE/logs/worker-*.log"
echo ""
echo "Kill workers:"
echo "  pkill -f usability_implementation_worker"
echo ""
