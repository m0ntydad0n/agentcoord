"""Enhanced CLI commands with Rich formatting."""

import click
from datetime import datetime
from ui.rich_formatter import formatter, TaskStatus

@click.group()
def cli():
    """AI Agent System with Rich UI"""
    pass

@cli.command()
@click.option('--format', default='table', help='Output format: table, json, plain')
def status(format):
    """Display system status with rich formatting."""
    
    # Sample data - replace with actual data sources
    tasks = [
        {
            "id": "T001",
            "name": "Data Processing Pipeline",
            "status": TaskStatus.RUNNING,
            "progress": 65,
            "updated": datetime.now()
        },
        {
            "id": "T002", 
            "name": "Model Training",
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "updated": datetime.now()
        },
        {
            "id": "T003",
            "name": "Report Generation", 
            "status": TaskStatus.FAILED,
            "progress": 0,
            "updated": datetime.now()
        }
    ]
    
    agents = [
        {
            "name": "DataAgent",
            "status": "active",
            "current_task": "Processing CSV files",
            "load": 75,
            "uptime": "2h 15m"
        },
        {
            "name": "ModelAgent",
            "status": "idle", 
            "current_task": "Waiting for data",
            "load": 10,
            "uptime": "1h 45m"
        }
    ]
    
    stats = {
        "active_tasks": 2,
        "completed_tasks": 15,
        "failed_tasks": 1,
        "active_agents": 2
    }
    
    if format == 'table':
        formatter.create_dashboard(tasks, agents, stats)
    else:
        formatter.print_warning(f"Format '{format}' not yet implemented")

@cli.command()
@click.argument('code_file', type=click.Path(exists=True))
@click.option('--language', default='python', help='Programming language for syntax highlighting')
def show_code(code_file, language):
    """Display code file with syntax highlighting."""
    try:
        with open(code_file, 'r') as f:
            code = f.read()
        formatter.print_code_snippet(code, language, f"📄 {code_file}")
    except Exception as e:
        formatter.print_error(f"Failed to read file: {code_file}", str(e))

@cli.command()
def demo():
    """Show a demo of Rich formatting capabilities."""
    formatter.print_header("🎨 Rich Formatting Demo", "Showcasing UI capabilities")
    
    # Success/Warning/Error examples
    formatter.print_success("System initialized successfully")
    formatter.print_warning("High memory usage detected")
    formatter.print_error("Connection timeout", "Failed to connect to database after 30 seconds")
    
    # Code example
    sample_code = '''def hello_world():
    """A simple hello world function."""
    print("Hello, Rich World! 🌟")
    return True'''
    
    formatter.print_code_snippet(sample_code, "python", "Sample Function")
    
    # Section example
    formatter.print_section(
        "System Information",
        "CPU: 8 cores @ 3.2GHz\nMemory: 16GB RAM\nDisk: 512GB SSD\nPython: 3.9.7",
        "blue"
    )

if __name__ == '__main__':
    cli()