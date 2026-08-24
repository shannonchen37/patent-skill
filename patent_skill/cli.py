from __future__ import annotations

import argparse
from pathlib import Path

from .case_workspace import (
    advance_stage,
    export_case_package,
    init_case_workspace,
    resolve_case_question,
    revise_case_stage,
    validate_case_workspace,
)
from .claims import validate_abstract_cn, validate_claims_cn
from .render import render_docx
from .scanner import write_manifest
from .security import detect_sensitive_files
from .symbols import write_symbols
from .workspace import validate_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="patent-skill")
    groups = parser.add_subparsers(dest="group", required=True)

    case = groups.add_parser("case", help="Canonical Chinese patent case workflow")
    case_commands = case.add_subparsers(dest="case_command", required=True)
    initialize = case_commands.add_parser("init")
    initialize.add_argument("case_dir", type=Path)
    initialize.add_argument("--project", type=Path, required=True)
    initialize.add_argument("--title", default="")
    for name in ("status", "validate"):
        command = case_commands.add_parser(name)
        command.add_argument("case_dir", type=Path)
    advance = case_commands.add_parser("advance")
    advance.add_argument("case_dir", type=Path)
    advance.add_argument("target_stage")
    advance.add_argument("--confirmation", default="")
    revise = case_commands.add_parser("revise")
    revise.add_argument("case_dir", type=Path)
    revise.add_argument("target_stage")
    revise.add_argument("--reason", required=True)
    resolve = case_commands.add_parser("resolve-question")
    resolve.add_argument("case_dir", type=Path)
    resolve.add_argument("question_id")
    resolve.add_argument("--answer", required=True)
    resolve.add_argument("--source", required=True)
    export = case_commands.add_parser("export")
    export.add_argument("case_dir", type=Path)
    export.add_argument("--output", type=Path, required=True)

    legacy = groups.add_parser("legacy", help="Deprecated pre-case workspace tools")
    legacy_commands = legacy.add_subparsers(dest="legacy_command", required=True)
    legacy_commands.add_parser("init-context")
    scan = legacy_commands.add_parser("scan")
    scan.add_argument("project", type=Path)
    scan.add_argument("--output", type=Path, default=Path("patent-workspace"))
    status = legacy_commands.add_parser("status")
    status.add_argument("workspace", type=Path)
    validate = legacy_commands.add_parser("validate")
    validate.add_argument("workspace", type=Path)
    validate.add_argument("--invention", default="P001")
    render = legacy_commands.add_parser("render")
    render.add_argument("workspace", type=Path)
    render.add_argument("invention", default="P001")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.group == "case":
        return _run_case(args)
    return _run_legacy(args)


def _run_case(args: argparse.Namespace) -> int:
    try:
        if args.case_command == "init":
            result = init_case_workspace(args.case_dir, args.project, args.title)
            snapshot = result["snapshot"]
            print(f"Created patent case: {result['status']['case_dir']}")
            print(f"Snapshot type: {snapshot['snapshot_type']}")
            print(f"Snapshot SHA-256: {snapshot['snapshot_sha256']}")
            print(f"Evidence files: {snapshot['file_count']}")
            for warning in snapshot["security_warnings"]:
                print(f"SECURITY WARNING: excluded {warning}")
        elif args.case_command == "status":
            print((args.case_dir / "case-status.json").read_text(encoding="utf-8"))
        elif args.case_command == "validate":
            errors = validate_case_workspace(args.case_dir)
            if errors:
                for error in errors:
                    print(f"FAIL {error}")
                return 1
            print("PASS canonical case validation")
        elif args.case_command == "advance":
            status = advance_stage(args.case_dir, args.target_stage, confirmation=args.confirmation)
            print(f"PASS advanced to {status['current_stage']}")
        elif args.case_command == "revise":
            status = revise_case_stage(args.case_dir, args.target_stage, args.reason)
            print(f"PASS reopened {status['current_stage']} as revision {status['revision']}")
        elif args.case_command == "resolve-question":
            question = resolve_case_question(
                args.case_dir, args.question_id, args.answer, args.source
            )
            print(f"PASS resolved {question['id']}")
        elif args.case_command == "export":
            print(export_case_package(args.case_dir, args.output))
    except (OSError, ValueError) as exc:
        print(f"FAIL {exc}")
        return 1
    return 0


def _run_legacy(args: argparse.Namespace) -> int:
    print("WARNING: legacy workspace commands are deprecated; use `patent-skill case`. ")
    if args.legacy_command == "init-context":
        template = Path(__file__).resolve().parent.parent / "assets" / "PATENT_CONTEXT.template.md"
        Path("PATENT_CONTEXT.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        print("Created PATENT_CONTEXT.md")
    elif args.legacy_command == "scan":
        engineering = args.output / "engineering"
        manifest = write_manifest(args.project, engineering / "repository-manifest.json")
        write_symbols(args.project, engineering / "symbols.json")
        (args.output / "status.json").write_text('{"state": "DISCOVERY"}\n', encoding="utf-8")
        print(f"Scanned {manifest['file_count']} files")
    elif args.legacy_command == "status":
        print((args.workspace / "status.json").read_text(encoding="utf-8"))
    elif args.legacy_command == "validate":
        errors = validate_workspace(args.workspace, args.invention)
        draft = args.workspace / "drafting" / args.invention
        if (draft / "claims-v2.md").exists():
            errors.extend(validate_claims_cn((draft / "claims-v2.md").read_text(encoding="utf-8")))
        if (draft / "abstract.md").exists():
            errors.extend(validate_abstract_cn((draft / "abstract.md").read_text(encoding="utf-8")))
        errors.extend(
            f"Sensitive file in workspace: {item}"
            for item in detect_sensitive_files(args.workspace)
        )
        if errors:
            for error in errors:
                print(f"FAIL {error}")
            return 1
        print("PASS workspace validation")
    elif args.legacy_command == "render":
        source = args.workspace / "drafting" / args.invention
        output = source / "attorney-review-draft.docx"
        render_docx(source, output)
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
