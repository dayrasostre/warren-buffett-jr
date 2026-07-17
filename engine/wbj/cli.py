"""CLI for wbj compute engine."""

import typer

app = typer.Typer()


@app.command()
def fetch(ticker: str) -> None:
    """Fetch data for a ticker."""
    typer.echo(f"fetch {ticker}: not implemented")
    raise typer.Exit(1)


@app.command()
def packet(ticker: str) -> None:
    """Build packet for a ticker."""
    typer.echo(f"packet {ticker}: not implemented")
    raise typer.Exit(1)


@app.command()
def compute(ticker: str) -> None:
    """Compute scores for a ticker."""
    typer.echo(f"compute {ticker}: not implemented")
    raise typer.Exit(1)


@app.command()
def aggregate(ticker: str) -> None:
    """Aggregate specialist outputs for a ticker."""
    typer.echo(f"aggregate {ticker}: not implemented")
    raise typer.Exit(1)


@app.command()
def report(ticker: str) -> None:
    """Generate report for a ticker."""
    typer.echo(f"report {ticker}: not implemented")
    raise typer.Exit(1)


@app.command()
def analyze(ticker: str) -> None:
    """Run full analysis pipeline for a ticker."""
    typer.echo(f"analyze {ticker}: not implemented")
    raise typer.Exit(1)
