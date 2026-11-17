"""Package only public website files: python3 -m blutspenden.build_site --output-dir DIR."""

import argparse
import json
from pathlib import Path

from .storage import load_dataset


PUBLIC_FILES = ("index.html", "assets/app.js", "assets/model.mjs", "assets/styles.css",
                "data/status.json")


def build_site(source_root, output_dir):
    root, output = Path(source_root).resolve(), Path(output_dir).resolve()
    if output == root or output in root.parents or root in output.parents:
        raise ValueError("Ausgabe muss außerhalb des Repositorys liegen.")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Ausgabeverzeichnis muss leer oder noch nicht vorhanden sein.")
    dataset = load_dataset(root / "data/appointments.json")
    if dataset is None:
        raise ValueError("Kein gültiger Terminbestand vorhanden.")
    # Read and validate everything before writing the artifact.
    contents = {name: (root / name).read_bytes() for name in PUBLIC_FILES}
    status = json.loads(contents["data/status.json"])
    if not isinstance(status, dict) or status.get("schema_version") != 1:
        raise ValueError("Aktualisierungsstatus hat ein unbekanntes Format.")
    contents["data/appointments.json"] = (
        json.dumps(dataset, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    contents[".nojekyll"] = b""
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in contents.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def main():
    parser = argparse.ArgumentParser(description="Geprüfte statische Website für GitHub Pages paketieren.")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    build_site(Path(__file__).resolve().parents[1], args.output_dir)
    print("Website-Artefakt erstellt: " + str(args.output_dir))


if __name__ == "__main__":
    main()
