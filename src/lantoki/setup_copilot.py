"""Set up Copilot instruction symlinks for Linux user and repository scopes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable

import structlog


linked_items: list[str] = []
skipped_items: list[str] = []


LOGGER = structlog.get_logger(__name__)


def _collect_matching_files(directory: Path, pattern: str) -> list[Path]:
    """Return sorted files matching a pattern if the directory exists."""
    if not directory.is_dir():
        return []
    return sorted(directory.glob(pattern))


def _collect_skill_dirs(directory: Path) -> list[Path]:
    """Return sorted direct child directories used as project skills."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.is_dir())


def _apply_optional_files(
    files: list[Path],
    prompt_builder: Callable[[Path], str],
    destination_dir: Path,
) -> None:
    """Prompt for optional files and link selected ones into a destination dir."""
    for source_file in files:
        if ask_yes_no(prompt_builder(source_file)):
            safe_link(source_file, destination_dir / source_file.name)
        else:
            skipped_items.append(f"[User Declined] {source_file.name}")


def _apply_optional_skills(skill_dirs: list[Path], target_repo: Path) -> None:
    """Prompt for optional skills and link selected skill directories."""
    for skill_dir in skill_dirs:
        prompt = f"Apply agent skill '{skill_dir.name}' to this repo? (y/N): "
        if ask_yes_no(prompt):
            safe_link(skill_dir, target_repo / ".github" / "skills" / skill_dir.name)
        else:
            skipped_items.append(f"[User Declined Skill] {skill_dir.name}")


def safe_link(src: Path, dest: Path) -> None:
    """Create a symlink if possible and track result in summary buckets."""
    if not src.exists():
        skipped_items.append(f"[Source Missing] {src}")
        LOGGER.warning("source_missing", source=str(src), destination=str(dest))
        return

    if dest.exists() or dest.is_symlink():
        try:
            is_same_link = dest.is_symlink() and dest.resolve() == src.resolve()
            if is_same_link:
                skipped_items.append(f"[Already Linked] {dest}")
                LOGGER.info("already_linked", source=str(src), destination=str(dest))
            else:
                skipped_items.append(
                    f"[Conflict] {dest} (A file or different symlink already exists)"
                )
                LOGGER.warning("link_conflict", source=str(src), destination=str(dest))
        except OSError:
            skipped_items.append(f"[Conflict] {dest} (Failed to inspect existing target)")
            LOGGER.exception("link_inspection_failed", source=str(src), destination=str(dest))
        return

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(src)
        linked_items.append(str(dest))
        LOGGER.info("linked", source=str(src), destination=str(dest))
    except OSError:
        skipped_items.append(f"[Link Failed] {dest}")
        LOGGER.exception("link_creation_failed", source=str(src), destination=str(dest))


def print_summary() -> None:
    """Log a summary of linked and skipped targets for this run."""
    LOGGER.info("setup_summary", linked_count=len(linked_items), skipped_count=len(skipped_items))
    LOGGER.info("linked_items_header", count=len(linked_items))
    if not linked_items:
        LOGGER.info("linked_item", item="(None)")
    for item in linked_items:
        LOGGER.info("linked_item", item=item)

    LOGGER.info("skipped_items_header", count=len(skipped_items))
    if not skipped_items:
        LOGGER.info("skipped_item", item="(None)")
    for item in skipped_items:
        LOGGER.info("skipped_item", item=item)


def setup_user(sync_root: Path) -> None:
    """Link user-level instructions, prompts, and MCP configs."""
    LOGGER.info("setup_user_start", sync_root=str(sync_root))

    vscode_user_dir = Path.home() / ".config" / "Code" / "User"
    copilot_cli_dir = Path.home() / ".copilot"

    for file in sorted((sync_root / "user-level" / "instructions").glob("*")):
        safe_link(file, vscode_user_dir / "instructions" / file.name)

    for file in sorted((sync_root / "user-level" / "prompts").glob("*")):
        safe_link(file, vscode_user_dir / "prompts" / file.name)

    safe_link(
        sync_root / "user-level" / "mcp" / "vscode-mcp.json",
        vscode_user_dir / "mcp.json",
    )
    safe_link(
        sync_root / "user-level" / "mcp" / "cli-mcp-config.json",
        copilot_cli_dir / "mcp-config.json",
    )

    print_summary()


def ask_yes_no(prompt: str) -> bool:
    """Ask the user to confirm an action, accepting only lowercase `y`."""
    answer = input(prompt).strip().lower()
    return answer == "y"


def setup_repo(sync_root: Path, target_repo: Path) -> None:
    """Link repo-level configuration files into a target repository."""
    if not target_repo.exists() or not target_repo.is_dir():
        LOGGER.error("invalid_target_repo", target_repo=str(target_repo))
        sys.exit(1)

    target_repo = target_repo.resolve()
    LOGGER.info("setup_repo_start", target_repo=str(target_repo), sync_root=str(sync_root))

    LOGGER.info("linking_core_repository_files")
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

    LOGGER.info("scanning_scoped_instructions")
    scoped_dir = sync_root / "project-level" / "scoped-instructions"
    scoped_files = _collect_matching_files(scoped_dir, "*.instructions.md")
    if scoped_files:
        _apply_optional_files(
            scoped_files,
            lambda file: f"Apply '{file.name}' to this repo? (y/N): ",
            target_repo / ".github" / "instructions",
        )
    else:
        LOGGER.info("no_scoped_instructions", path=str(scoped_dir))

    LOGGER.info("scanning_project_prompts")
    prompts_dir = sync_root / "project-level" / "project-prompts"
    prompt_files = _collect_matching_files(prompts_dir, "*.prompt.md")
    if prompt_files:
        _apply_optional_files(
            prompt_files,
            lambda file: f"Apply prompt macro '{file.name}' to this repo? (y/N): ",
            target_repo / ".github" / "prompts",
        )
    else:
        LOGGER.info("no_project_prompts", path=str(prompts_dir))

    LOGGER.info("scanning_project_skills")
    skills_dir = sync_root / "project-level" / "project-skills"
    skill_dirs = _collect_skill_dirs(skills_dir)
    if skill_dirs:
        _apply_optional_skills(skill_dirs, target_repo)
    else:
        LOGGER.info("no_project_skills", path=str(skills_dir))

    print_summary()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for user-level or repo-level setup."""
    parser = argparse.ArgumentParser(
        description="Link Copilot instruction files for user-level or repo-level setup."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    subparsers.add_parser("user", help="Links global user-level configs")

    repo_parser = subparsers.add_parser("repo", help="Links repo-level configs interactively")
    repo_parser.add_argument("path", help="Path to the target repository")

    return parser.parse_args()


def main() -> None:
    """Entrypoint for CLI execution."""
    args = parse_args()

    # The sync root lives next to this script under copilot-instructions-set.
    sync_root = Path(__file__).resolve().parent / "copilot-instructions-set"

    if args.mode == "user":
        setup_user(sync_root)
    else:
        setup_repo(sync_root, Path(args.path))


if __name__ == "__main__":
    main()
