# Dashboard Export Feature

The AgentCoord dashboard supports exporting snapshots to SVG or HTML formats for documentation, reporting, or sharing purposes.

## Usage

### Single Snapshot Export

Export a single snapshot of the current dashboard state:


### Automatic Continuous Export

Export snapshots automatically while running the live dashboard:


## File Naming

By default, exported files are named with timestamps:
- `agentcoord_dashboard_20231201_143022.svg`
- `agentcoord_dashboard_20231201_143022.html`

## Programmatic Usage


## Export Formats

- **SVG**: Vector format, good for documentation and presentations
- **HTML**: Web format with embedded CSS, good for sharing and web integration

Both formats preserve the Rich console styling and layout structure.