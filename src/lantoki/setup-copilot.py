#!/usr/bin/env python3

"""Set up Copilot instruction symlinks for Linux user and repository scopes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


LINKED: list[str] = []
SKIPPED: list[str] = []


def safe_link(src: Path, dest: Path) -> None:
    """Create a symlink if possible and track result in summary buckets."""
    if not src.exists():
        SKIPPED.append(f"[Source Missing] {src}")
        return

    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() and dest.resolve() == src.resolve():
            SKIPPED.append(f"[Already Linked] {dest}")
        else:
            SKIPPED.append(
                f"[Conflict] {dest} (A file or different symlink already exists)"
            )
            print(f"   Warning: Conflict detected at {dest}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(src)
    LINKED.append(str(dest))
    print(f"   Linked: {dest.name}")


def print_summary() -> None:
    print("\n========================================")
    print("            SETUP SUMMARY")
    print("========================================")

    print(f"\nSUCCESSFULLY LINKED ({len(LINKED)}):")
    if not LINKED:
        print("   (None)")
    for item in LINKED:
        print(f"   - {item}")

    print(f"\nSKIPPED ({len(SKIPPED)}):")
    if not SKIPPED:
        print("   (None)")
    for item in SKIPPED:
        print(f"   - {item}")

    print("========================================\n")


def setup_user(sync_root: Path) -> None:
    print("\nSetting up global User-Level instructions for Linux...\n")

    vscode_user_dir = Path.home() / ".config" / "Code" / "User"
    copilot_cli_dir = Path.home() / ".copilot"

    for file in sorted((sync_root / "user-level" / "instructions").glob("*")):
        safe_link(file, vscode_user_dir / "instructions" / file.name)

    for file in sorted((sync_root / "user-level" / "prompts").glob("*")):
        safe_link(file, vscode_user_dir / "prompts" / file.name)

    safe_link(sync_root / "user-level" / "mcp" / "vscode-mcp.json", vscode_user_dir / "mcp.json")
    safe_link(
        sync_root / "user-level" / "mcp" / "cli-mcp-config.json",
        copilot_cli_dir / "mcp-config.json",
    )

    print_summary()


def ask_yes_no(prompt: str) -> bool:
    answer = input(prompt).strip().lower()
    return answer == "y"


def setup_repo(sync_root: Path, target_repo: Path) -> None:
    if not target_repo.exists() or not target_repo.is_dir():
        print("Error: Please provide a valid path to the target repository.")
        print("Usage: ./setup-copilot.sh repo /path/to/your/project")
        sys.exit(1)

    target_repo = target_repo.resolve()
    print(f"\nSetting up Repository-Level instructions in: {target_repo}\n")

    print("Linking core repository files...")
    safe_link(
        sync_root / "project-level" / "global-repo" / "copilot-instructions.md",
        target_repo / ".github" / "copilot-instructions.md",
    )
    safe_link(
        sync_root / "project-level" / "global-repo" / "AGENTS.md",
        target_repo / "AGENTS.md",
    )

    shared_mcp = sync_root / "project-level" / "project-mcp" / "shared-mcp.json"
    if shared_mcp.is_file():
        safe_link(shared_mcp, target_repo / ".vscode" / "mcp.json")

    print("\nScanning for Scoped Instructions...")
    scoped_dir = sync_root / "project-level" / "scoped-instructions"
    scoped_files = sorted(scoped_dir.glob("*.instructions.md")) if scoped_dir.is_dir() else []
    if scoped_files:
        for file in scoped_files:
            if ask_yes_no(f"Apply '{file.name}' to this repo? (y/N): "):
                safe_link(file, target_repo / ".github" / "instructions" / file.name)
            else:
                SKIPPED.append(f"[User Declined] {file.name}")
    else:
        print(f"   No scoped instructions found in {scoped_dir}.")

    print("\nScanning for Project-Specific Prompts...")
    prompts_dir = sync_root / "project-level" / "project-prompts"
    prompt_files = sorted(prompts_dir.glob("*.prompt.md")) if prompts_dir.is_dir() else []
    if prompt_files:
        for file in prompt_files:
            if ask_yes_no(f"Apply prompt macro '{file.name}' to this repo? (y/N): "):
                safe_link(file, target_repo / ".github" / "prompts" / file.name)
            else:
                SKIPPED.append(f"[User Declined] {file.name}")
    else:
        print(f"   No project prompts found in {prompts_dir}.")

    print("\nScanning for Reusable Agent Skills...")
    skills_dir = sync_root / "project-level" / "project-skills"
    skill_dirs = sorted(path for path in skills_dir.iterdir() if path.is_dir()) if skills_dir.is_dir() else []
    if skill_dirs:
        for skill_dir in skill_dirs:
            if ask_yes_no(f"Apply agent skill '{skill_dir.name}' to this repo? (y/N): "):
                safe_link(skill_dir, target_repo / ".github" / "skills" / skill_dir.name)
            else:
                SKIPPED.append(f"[User Declined Skill] {skill_dir.name}")
    else:
        print(f"   No project skills found in {skills_dir}.")

    print_summary()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Link Copilot instruction files for user-level or repo-level setup."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    subparsers.add_parser("user", help="Links global user-level configs")

    repo_parser = subparsers.add_parser(
        "repo", help="Links repo-level configs interactively"
    )
    repo_parser.add_argument("path", help="Path to the target repository")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # The sync root lives next to this script under copilot-instructions-set.
    sync_root = Path(__file__).resolve().parent / "copilot-instructions-set"

    if args.mode == "user":
        setup_user(sync_root)
    else:
        setup_repo(sync_root, Path(args.path))


if __name__ == "__main__":
    main()
