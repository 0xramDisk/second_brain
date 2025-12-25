# second_brain/cli/youtube.py
"""
CLI entrypoint for YouTube content ingestion.

Thin adapter — no business logic.
Responsibilities:
- Parse arguments
- Invoke core pipeline
- Write artifact
- Provide clear user feedback

All logging is structured JSON from the core pipeline.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from second_brain.content_ingestor.runner import run_ingestion
from second_brain.content_ingestor.output.writer import write_artifact


app = typer.Typer(
    name="second-brain",
    help="Second Brain — Content Ingestor for YouTube",
    no_args_is_help=True,
)

# To ingest the input
@app.command()
def ingest(
    url: str = typer.Argument(..., help="YouTube video URL"),
    out: str = typer.Option("./output", "--out", "-o", help="Output directory for JSON artifact"),
    download_audio_dir: str | None = typer.Option(
        None, "--download-audio-dir", help="Directory to save extracted audio (optional)"
    ),
    no_transcribe: bool = typer.Option(
        False, "--no-transcribe", help="Download audio only, skip transcription"
    ),
) -> None:
    """
    Ingest a YouTube video and produce a structured JSON artifact.
    """
    # Defensive guard — allow None for optional download_audio_dir
    if download_audio_dir is not None and not isinstance(download_audio_dir, (str, bytes, os.PathLike)):
        typer.echo("Internal error: download-audio-dir received invalid type.", err=True)
        raise typer.Abort()

    if not isinstance(out, (str, bytes, os.PathLike)):
        typer.echo("Internal error: Output directory option received invalid type.", err=True)
        typer.echo("Hint: Ensure you provide a valid --out path or use the default.", err=True)
        raise typer.Abort()

    output_path = Path(out).expanduser()

    typer.echo(f"Starting ingestion for: {url}")
    typer.echo(f"Output directory: {output_path.resolve()}")

    # Build config for transcription stage
    config = {
        "download_audio_dir": download_audio_dir,
        "transcribe": not no_transcribe,
    }

    try:
        content_object = run_ingestion(url, config=config)
        artifact_path = write_artifact(content_object, output_path)

        typer.echo("")
        typer.echo(typer.style("✓ Ingestion completed successfully!", fg=typer.colors.GREEN, bold=True))
        typer.echo(f"Artifact written to: {artifact_path}")

        diagnostics = content_object.get("diagnostics", {})
        if diagnostics.get("warnings") or diagnostics.get("errors"):
            typer.echo("")
            typer.echo(typer.style("⚠ Partial success — check diagnostics in the JSON artifact or logs above.", fg=typer.colors.YELLOW))

    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user.", err=True)
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-except
        typer.echo("")
        typer.echo(typer.style("✗ Ingestion failed", fg=typer.colors.RED, bold=True), err=True)
        typer.echo(f"Error: {exc}", err=True)
        typer.echo("")
        typer.echo("See structured JSON logs above for detailed diagnostics and suggested fixes.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    app()




#     High-Level Intent

# cli/youtube.py is the thin, interface-agnostic adapter for the Content Ingestor pipeline.
# Single responsibility:

#     Parse CLI arguments (YouTube URL and optional output directory)
#     Invoke the core runner (run_ingestion)
#     Invoke the output writer
#     Print high-level, human-readable status (success path or clear error with diagnostics hint)

# Contains zero business logic — only argument parsing, orchestration call, and user feedback.
# Uses Typer (per standards) for CLI-friendliness and future extensibility (subcommands, config, etc.).
# Architecture

#     Typer app with single command ingest
#     --out optional (defaults to ./output/)
#     Rich error handling: catches pipeline exceptions, prints diagnostics guidance
#     Success: prints artifact path
#     All logging goes through the centralized logger (structured JSON lines to stdout)

# Data Flow

# CLI invocation → Typer parses → run_ingestion(url) → content_object → write_artifact → Path → print success
# On exception → print user-friendly message + "See JSON logs above for diagnostics"
# Edge Cases & Failure Scenarios

#     Invalid arguments → Typer handles with clear message
#     Pipeline raises (e.g., disk error in writer) → caught, print "Ingestion failed" + suggestion to check logs
#     Partial success (e.g., no transcript) → still success (artifact written with diagnostics)
#     No permissions/disk full → writer raises → caught and reported

# Extension Points

#     Add subcommands (e.g., reprocess, validate)
#     Add config file support (TOML/YAML)
#     Add verbosity flag to control log level
#     Future: Slack/Discord adapters import and call same run_ingestion
