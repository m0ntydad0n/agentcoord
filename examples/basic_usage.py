"""Basic usage example for agentcoord library."""

from agentcoord import CoordinationClient

# Example 1: Manual session management
def manual_session_example():
    """Example using manual session management."""
    client = CoordinationClient(
        redis_url="redis://localhost:6379",
        fallback_dir="./workbench"
    )

    # Register agent
    agent_id = client.register_agent(
        role="CTO",
        name="Claude",
        working_on="Implementing new features"
    )
    print(f"Registered as {agent_id} in {client.mode} mode")

    # Lock a file
    try:
        with client.lock_file("backend/main.py", intent="Add /health endpoint"):
            print("File locked - safe to edit")
            # Edit the file here
    except Exception as e:
        print(f"Could not acquire lock: {e}")

    # Log a decision
    client.log_decision(
        decision_type="implementation",
        context="Adding health endpoint",
        reason="Needed for monitoring"
    )

    # Cleanup
    client.shutdown()


# Example 2: Context manager (recommended)
def context_manager_example():
    """Example using context manager for automatic cleanup."""
    with CoordinationClient.session(
        redis_url="redis://localhost:6379",
        role="Engineer",
        name="Agent-42",
        working_on="Implementing Redis coordination",
        fallback_dir="./workbench"
    ) as coord:
        print(f"Session started in {coord.mode} mode")

        # Claim a task
        task = coord.claim_task(tags=["backend"])
        if task:
            print(f"Claimed task: {task.title}")

        # Lock and edit files
        with coord.lock_file("src/main.py", intent="Refactor authentication"):
            print("Locked src/main.py")
            # Safe to edit

        # Post to board
        thread = coord.post_thread(
            title="Deployment Complete",
            message="Successfully deployed backend v2.0",
            priority="high"
        )
        if thread:
            print(f"Posted thread: {thread.id}")

        # Log decision
        coord.log_decision(
            decision_type="deployment",
            context="Backend v2.0",
            reason="New features tested and ready"
        )

    # Automatic cleanup when exiting context


if __name__ == "__main__":
    print("=== Manual Session Example ===")
    manual_session_example()

    print("\n=== Context Manager Example ===")
    context_manager_example()

    print("\nDone!")
