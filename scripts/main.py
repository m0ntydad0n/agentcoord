"""Main application entry point with Rich UI integration."""

from cli.commands import cli
from ui.rich_formatter import formatter

def main():
    """Main application entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        formatter.print_warning("Operation cancelled by user")
    except Exception as e:
        formatter.print_error("Unexpected error occurred", str(e))

if __name__ == '__main__':
    main()