"""CSVClean CLI — Clean and validate CSV files."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="csvclean")
def main():
    """CSVClean — Find and fix CSV file problems.

    Detect encoding issues, inconsistent delimiters, missing headers,
    duplicate rows, type mismatches — all in one command.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def check(path, output_json):
    """Analyze a CSV file and report all issues.

    \b
    Examples:
        csvclean check data.csv
        csvclean check data.csv --json
    """
    from .cleaner import analyze_csv

    console.print()
    console.print(Panel(
        f"[bold]CSVClean Check[/bold] — [cyan]{path}[/cyan]",
        border_style="blue"
    ))

    try:
        result = analyze_csv(path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    if output_json:
        import json as _json
        console.print(_json.dumps(result, indent=2, default=str))
        return

    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    # Overview
    score = result["health_score"]
    color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    console.print(f"\n[bold {color}]Health: {score}/100[/bold {color}]")
    console.print(f"  Size: {result['size_human']}")
    console.print(f"  Encoding: [cyan]{result['encoding']}[/cyan]")
    console.print(f"  Delimiter: [cyan]{result['delimiter']}[/cyan]")
    console.print(f"  Rows: [bold]{result['total_rows']:,}[/bold] × {result['total_columns']} columns")
    console.print(f"  Empty rows: {result.get('empty_rows', 0)}")
    console.print(f"  Duplicates: {result.get('duplicate_rows', 0)}")

    # Issues
    if result["issues"]:
        console.print()
        console.print("[bold]Issues found:[/bold]")
        for issue in result["issues"]:
            icon = "[red]✗[/red]" if issue["severity"] == "error" else "[yellow]![/yellow]"
            console.print(f"  {icon} {issue['message']}")
    else:
        console.print()
        console.print("[green]No issues found. File is clean![/green]")

    # Column types
    if result.get("column_types"):
        console.print()
        console.print("[bold]Column Analysis:[/bold]")
        col_table = Table()
        col_table.add_column("Column")
        col_table.add_column("Type", style="cyan")
        col_table.add_column("Empty %", justify="right")
        col_table.add_column("Distribution")

        for col_name, info in result["column_types"].items():
            dist = ", ".join(f"{t}:{c}" for t, c in info["distribution"].items() if t != "empty")
            col_table.add_row(
                col_name[:25],
                info["dominant_type"],
                f"{info['empty_pct']}%",
                dist[:40]
            )

        console.print(col_table)


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.argument("output")
@click.option("--remove-empty/--keep-empty", default=True, help="Remove empty rows")
@click.option("--normalize/--preserve", default=True, help="Normalize delimiter to comma")
def clean(path, output, remove_empty, normalize):
    """Clean a CSV file and write the fixed output.

    \b
    Example:
        csvclean clean messy.csv clean.csv
    """
    console.print()
    console.print(Panel(
        f"[bold]CSVClean Clean[/bold] — [cyan]{path}[/cyan] → [green]{output}[/green]",
        border_style="blue"))

    from .cleaner import clean_csv
    result = clean_csv(path, output, remove_empty=remove_empty,
                      normalize_delimiter=normalize)
    console.print()
    if result.get("removed_empty"):
        console.print(f"  [green]✓[/green] Removed {result['removed_empty']} empty row(s)")
    if result.get("removed_duplicates"):
        console.print(f"  [green]✓[/green] Removed {result['removed_duplicates']} duplicate row(s)")
    if result.get("normalized_delimiter"):
        console.print(f"  [green]✓[/green] Normalized delimiter → comma")
    console.print(f"  [bold]Wrote[/bold] {result['output']} (encoding: {result['encoding_used']})")


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.argument("output", required=False)
@click.option("--in-place/--new-file", "inplace", default=False,
              help="Overwrite the input file instead of writing to OUTPUT")
def dedupe(path, output, inplace):
    """Remove duplicate data rows from a CSV.

    \b
    Examples:
        csvclean dedupe data.csv deduped.csv
        csvclean dedupe data.csv --in-place
    """
    console.print()
    console.print(Panel(
        f"[bold]CSVClean Dedupe[/bold] — [cyan]{path}[/cyan]",
        border_style="blue"))

    from .cleaner import dedupe_csv
    target = path if inplace else (output or "deduped.csv")
    result = dedupe_csv(path, target)
    console.print()
    if result["removed"]:
        console.print(f"  [green]✓[/green] Removed {result['removed']} duplicate row(s)")
    else:
        console.print("  [green]No duplicate rows found.[/green]")
    if result.get("wrote"):
        console.print(f"  [bold]Wrote[/bold] {result['output']}")


@main.command()
@click.argument("path", type=click.Path(exists=True))
def stats(path):
    """Show column statistics.

    \b
    Example:
        csvclean stats data.csv
    """
    from .cleaner import analyze_csv

    result = analyze_csv(path)
    console.print()
    console.print(Panel(
        f"[bold]CSVClean Stats[/bold] — [cyan]{path}[/cyan]",
        border_style="blue"
    ))

    ct = result.get("column_types", {})
    for col_name, info in ct.items():
        console.print(f"\n[bold cyan]{col_name}[/bold cyan]")
        console.print(f"  Type: {info['dominant_type']}")
        console.print(f"  Empty: {info['empty_count']} ({info['empty_pct']}%)")
        dist = info.get("distribution", {})
        if len(dist) > 1:
            console.print(f"  Distribution: {dist}")


if __name__ == "__main__":
    main()
