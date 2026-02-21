"""CLI module initialization."""
import click
from .health import health
from .coordinate import coordinate
from .implement import implement
from .build import build


@click.group()
def cli():
    """AgentCoord CLI."""
    pass


cli.add_command(health)
cli.add_command(coordinate)
cli.add_command(implement)
cli.add_command(build)