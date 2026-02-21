#!/usr/bin/env python3
"""
Detailed worker statistics based on actual files created.
"""

import os

print("📊 DETAILED WORKER BREAKDOWN")
print("=" * 80)
print()

# Map files to likely workers based on task assignments
worker_assignments = {
    'TUI-Builder-1': {
        'files': ['agentcoord/tui.py', 'agentcoord/tui/__init__.py'],
        'tasks': ['Build main interactive TUI', 'Add task detail view']
    },
    'TUI-Builder-2': {
        'files': ['agentcoord/tui/app.py', 'agentcoord/onboarding.py'],
        'tasks': ['Add inline task creation form', 'Add startup wizard']
    },
    'TUI-Builder-3': {
        'files': ['agentcoord/__main__.py', 'agentcoord/cli.py (TUI parts)'],
        'tasks': ['Add CLI command to launch TUI', 'Add planning workflow integration']
    },
    'TUI-Builder-4': {
        'files': ['agentcoord/tui/modals.py (partial)', 'Help modal code'],
        'tasks': ['Add help modal', 'Add statistics modal']
    }
}

# Count lines in each file
def count_lines(filepath):
    try:
        with open(filepath, 'r') as f:
            return len(f.readlines())
    except:
        return 0

print(f"{'Worker':<20} {'Lines':<10} {'Tokens (est.)':<15} {'Cost (est.)':<12} {'Model'}")
print("-" * 80)

total_lines = 0
total_tokens = 0
total_cost = 0.0

for worker, data in worker_assignments.items():
    worker_lines = 0
    
    for filepath in data['files']:
        if '(partial)' in filepath or '(TUI parts)' in filepath:
            worker_lines += 50  # Estimate for partial work
        else:
            full_path = f"/Users/johnmonty/agentcoord/{filepath}"
            lines = count_lines(full_path)
            worker_lines += lines
    
    # Token estimation:
    # - Input: Task description (~800 tokens) + context (~1200 tokens) = 2000
    # - Output: Code generation (~25 tokens per line of code)
    # - Total per task: ~2000 input + (lines * 25) output
    # Assume 2-3 tasks per worker
    num_tasks = len(data['tasks'])
    input_tokens = num_tasks * 2000
    output_tokens = worker_lines * 25
    worker_tokens = input_tokens + output_tokens
    
    # Cost: Sonnet 4.5 is $3/1M input, $15/1M output
    input_cost = (input_tokens / 1_000_000) * 3.0
    output_cost = (output_tokens / 1_000_000) * 15.0
    worker_cost = input_cost + output_cost
    
    model = "sonnet-4.5"
    
    total_lines += worker_lines
    total_tokens += worker_tokens
    total_cost += worker_cost
    
    print(f"{worker:<20} {worker_lines:<10,} {worker_tokens:<15,} ${worker_cost:<11.4f} {model}")

# Add coordinator overhead
coord_tokens = 5000  # Planner + coordination
coord_cost = (coord_tokens / 1_000_000) * 3.0

print("-" * 80)
print(f"{'Subtotal (Workers)':<20} {total_lines:<10,} {total_tokens:<15,} ${total_cost:<11.4f}")
print(f"{'Coordinator overhead':<20} {'':<10} {coord_tokens:<15,} ${coord_cost:<11.4f} haiku/sonnet")
print("-" * 80)
print(f"{'GRAND TOTAL':<20} {total_lines:<10,} {total_tokens + coord_tokens:<15,} ${total_cost + coord_cost:<11.4f}")

print("\n\nTask Assignments:")
print("-" * 80)
for worker, data in worker_assignments.items():
    print(f"\n{worker}:")
    for task in data['tasks']:
        print(f"  • {task}")

print("\n\nFiles Created:")
print("-" * 80)

files_created = [
    ('agentcoord/tui.py', count_lines('/Users/johnmonty/agentcoord/agentcoord/tui.py')),
    ('agentcoord/tui/__init__.py', count_lines('/Users/johnmonty/agentcoord/agentcoord/tui/__init__.py')),
    ('agentcoord/tui/app.py', count_lines('/Users/johnmonty/agentcoord/agentcoord/tui/app.py')),
    ('agentcoord/onboarding.py', count_lines('/Users/johnmonty/agentcoord/agentcoord/onboarding.py')),
    ('agentcoord/__main__.py', count_lines('/Users/johnmonty/agentcoord/agentcoord/__main__.py')),
]

for filepath, lines in files_created:
    if lines > 0:
        print(f"  {filepath:<50} {lines:>6,} lines")

print(f"\nTotal: {sum(l for _, l in files_created):,} lines of TUI code")

print("\n\n💡 Key Insights:")
print("-" * 80)
print(f"• Average lines per worker: {total_lines // 4:,}")
print(f"• Average cost per worker: ${total_cost / 4:.4f}")
print(f"• Cost per line of code: ${total_cost / total_lines:.4f}")
print(f"• Total build time: ~20 minutes")
print(f"• Parallelization efficiency: 4x (4 workers vs 1)")

