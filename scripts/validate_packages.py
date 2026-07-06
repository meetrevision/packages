from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def main() -> int:
    schema_path = ROOT / "schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    validator = jsonschema.Draft7Validator(schema)

    yaml_files = sorted(ROOT.glob("*.yaml"))
    if not yaml_files:
        print("No package YAML files found.", file=sys.stderr)
        return 1

    failures: list[str] = []
    for path in yaml_files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            failures.append(f"{path.name}: invalid YAML: {exc}")
            continue

        if not isinstance(data, dict):
            failures.append(f"{path.name}: top-level document must be a mapping")
            continue

        for error in sorted(validator.iter_errors(data), key=str):
            location = ".".join(str(part) for part in error.absolute_path)
            prefix = f"{path.name}:{location or '<root>'}"
            failures.append(f"{prefix}: {error.message}")

        expected_arch = path.stem.rsplit("-", 1)[-1]
        if expected_arch in {"amd64", "arm64", "wow64"}:
            actual_arch = data.get("target_arch")
            if actual_arch != expected_arch:
                failures.append(
                    f"{path.name}: target_arch {actual_arch!r} does not match filename arch {expected_arch!r}"
                )

        version = data.get("version")
        if isinstance(version, str) and not VERSION_RE.match(version):
            failures.append(f"{path.name}: version {version!r} must be x.x.x.x")

    if failures:
        print("Package validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Validated {len(yaml_files)} package YAML files against schema.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
