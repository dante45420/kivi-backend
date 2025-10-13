import os
import subprocess
from flask import current_app


def generate_db_dump():
    url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if url and url.startswith("postgres"):
        env = os.environ.copy()
        env["PGOPTIONS"] = env.get("PGOPTIONS", "")
        proc = subprocess.Popen(
            ["pg_dump", url, "--no-owner", "--no-privileges"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        assert proc.stdout is not None
        for chunk in iter(lambda: proc.stdout.read(65536), b""):
            yield chunk
    elif url and url.startswith("sqlite"):
        path = url.split("sqlite:///")[-1]
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                yield chunk
    else:
        yield b"-- unsupported database url for dump\n"
