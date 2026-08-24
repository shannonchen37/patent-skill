from __future__ import annotations

import argparse
import json
from pathlib import Path

from .case_workspace import init_case_workspace, validate_case_workspace
from .claims import validate_abstract_cn, validate_claims_cn
from .render import render_docx
from .scanner import write_manifest
from .security import detect_sensitive_files
from .symbols import write_symbols
from .workspace import validate_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="patent-skill")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-context")
    init_case = commands.add_parser("init-case")
    init_case.add_argument("case_dir", type=Path)
    init_case.add_argument("--project", type=Path, required=True)
    init_case.add_argument("--title", default="")
    validate_case = commands.add_parser("validate-case")
    validate_case.add_argument("case_dir", type=Path)
    scan = commands.add_parser("scan")
    scan.add_argument("project", type=Path)
    scan.add_argument("--output", type=Path, default=Path("patent-workspace"))
    status = commands.add_parser("status")
    status.add_argument("workspace", type=Path)
    validate = commands.add_parser("validate")
    validate.add_argument("workspace", type=Path)
    validate.add_argument("--invention", default="P001")
    render = commands.add_parser("render")
    render.add_argument("workspace", type=Path)
    render.add_argument("invention", default="P001")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init-context":
        template = Path(__file__).resolve().parent.parent / "assets" / "PATENT_CONTEXT.template.md"
        Path("PATENT_CONTEXT.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        print("Created PATENT_CONTEXT.md")
        return 0
    if args.command == "init-case":
        result = init_case_workspace(args.case_dir, args.project, args.title)
        snapshot = result["snapshot"]
        git = snapshot["git"]
        print(f"Created patent case: {result['status']['case_dir']}")
        print(f"Evidence files: {snapshot['file_count']}")
        if git.get("is_repository"):
            print(f"Git HEAD: {git['head']}")
            print(f"Worktree clean: {git['worktree_clean']}")
        for warning in snapshot["security_warnings"]:
            print(f"SECURITY WARNING: excluded {warning}")
        return 0
    if args.command == "validate-case":
        errors = validate_case_workspace(args.case_dir)
        if errors:
            for error in errors:
                print(f"FAIL {error}")
            return 1
        print("PASS canonical case validation")
        return 0
    if args.command == "scan":
        engineering = args.output / "engineering"
        manifest = write_manifest(args.project, engineering / "repository-manifest.json")
        write_symbols(args.project, engineering / "symbols.json")
        (args.output / "status.json").write_text('{"state": "DISCOVERY"}\n', encoding="utf-8")
        print(f"Scanned {manifest['file_count']} files")
        for warning in manifest["security_warnings"]:
            print(f"SECURITY WARNING: excluded {warning}")
        return 0
    if args.command == "status":
        print((args.workspace / "status.json").read_text(encoding="utf-8"))
        return 0
    if args.command == "validate":
        errors = validate_workspace(args.workspace, args.invention)
        draft = args.workspace / "drafting" / args.invention
        if (draft / "claims-v2.md").exists():
            errors.extend(validate_claims_cn((draft / "claims-v2.md").read_text(encoding="utf-8")))
        if (draft / "abstract.md").exists():
            errors.extend(validate_abstract_cn((draft / "abstract.md").read_text(encoding="utf-8")))
        for sensitive in detect_sensitive_files(args.workspace):
            errors.append(f"Sensitive file in workspace: {sensitive}")
        if errors:
            for error in errors:
                print(f"FAIL {error}")
            return 1
        print("PASS workspace validation")
        return 0
    if args.command == "render":
        source = args.workspace / "drafting" / args.invention
        output = source / "attorney-review-draft.docx"
        render_docx(source, output)
        print(output)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
