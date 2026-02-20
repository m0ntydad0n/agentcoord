"""CLI module initialization."""
import click
from .health import health
from .coordinate import coordinate


@click.group()
def cli():
    """AgentCoord CLI."""
    pass


cli.add_command(health)
cli.add_command(coordinate)