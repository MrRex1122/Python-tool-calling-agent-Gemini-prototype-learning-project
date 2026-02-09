"""Small task runner for common project commands.

This keeps usage consistent across machines without requiring Make/Just.
"""

import argparse
import subprocess
import sys


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Project task runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("test", help="Run unit tests")
    subparsers.add_parser("lint", help="Run basic syntax checks")
    subparsers.add_parser("run-api", help="Run FastAPI server")
    run_cli = subparsers.add_parser("run-cli", help="Run CLI with optional prompt")
    run_cli.add_argument("prompt", nargs=argparse.REMAINDER, help="Prompt text")

    args = parser.parse_args()
    if args.command == "test":
        _run([sys.executable, "-m", "pytest", "-q"])
        return

    if args.command == "lint":
        _run([sys.executable, "-m", "compileall", "-q", "."])
        return

    if args.command == "run-api":
        _run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload",
            ]
        )
        return

    if args.command == "run-cli":
        prompt = args.prompt if args.prompt else []
        _run([sys.executable, "main.py", *prompt])
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
