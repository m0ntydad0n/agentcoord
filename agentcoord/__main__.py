import sys
from agentcoord.cli import cli, launch_tui

def main():
    """Main entry point for agentcoord."""
    # If no arguments provided, launch TUI by default
    if len(sys.argv) == 1:
        if not launch_tui():
            # TUI failed, show help and exit
            from click import Context
            ctx = Context(cli)
            print(ctx.get_help())
            sys.exit(1)
    else:
        # Arguments provided, use normal CLI
        cli()

if __name__ == '__main__':
    main()