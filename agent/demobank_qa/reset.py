
"""Reset DemoBank to its deterministic synthetic seed data."""
import subprocess
from pathlib import Path


def reset_seed(database_dir: Path):
    database_dir = Path(database_dir).resolve()

    for sqlfile in (
        "migrations/001_create_schema.sql",
        "seed.sql",
    ):
        sql_path = database_dir / sqlfile

        # Send raw UTF-8 bytes, avoiding Windows code-page conversion.
        sql_bytes = sql_path.read_bytes()

        result = subprocess.run(
            [
                "docker", "compose", "exec", "-T",
                "postgres", "psql",
                "-v", "ON_ERROR_STOP=1",
                "-U", "demobank",
                "-d", "demobank",
            ],
            cwd=database_dir,
            input=sql_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
            check=False,
        )

        if result.returncode != 0:
            error = result.stderr.decode(
                "utf-8", errors="replace"
            )
            raise RuntimeError(
                f"DemoBank reset failed ({sqlfile}): {error[-500:]}"
            )

        print(f"RESET OK: {sqlfile}")
