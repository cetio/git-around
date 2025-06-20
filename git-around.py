#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import argparse
import time
from pathlib import Path
import yaml
import fnmatch


class RepoConfig:
    """
    Holds configuration for a single repository.

    Attributes:
        path (Path): Filesystem path to the git repository.
        auto_pull (bool): Whether to run 'git pull'.
        auto_push (bool): Whether to run 'git push'.
        clean (bool): Whether to run 'git clean -fd'.
        update_submodules (bool): Whether to run 'git submodule update --init --recursive'.
        commands (List[str]): List of arbitrary git (or shell) commands to run.
    """
    def __init__(
        self,
        path: Path,
        auto_pull: bool = True,
        auto_push: bool = False,
        clean: bool = False,
        update_submodules: bool = False,
        commands: list = None,
    ):
        logging.debug(f"Initializing RepoConfig with path: {path}")
        self.path = path
        self.auto_pull = auto_pull
        self.auto_push = auto_push
        self.clean = clean
        self.update_submodules = update_submodules
        self.commands = commands or []


class GitAroundConfig:
    """
    Holds the overall configuration loaded from YAML.
    """
    def __init__(self, repos: list):
        logging.debug(f"Initializing GitAroundConfig with repos: {repos}")
        self.repos = repos

    @classmethod
    def load_from_file(cls, path: Path) -> 'GitAroundConfig':
        logging.info(f"Loading configuration from file: {path}")
        if not path.exists():
            logging.error(f"Config file not found: {path}")
            sys.exit(1)
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML: {e}")
            sys.exit(1)

        repos = []
        for entry in data.get('repos', []):
            raw_path = entry.get('path')
            expanded = Path(raw_path).expanduser()
            matched_paths = []
            if any(ch in raw_path for ch in ['*', '?', '[']):
                base = expanded.parent if expanded.parent.exists() else Path.home()
                pattern = expanded.name
                for p in base.iterdir():
                    if fnmatch.fnmatch(p.name, pattern) and (p / '.git').is_dir():
                        matched_paths.append(p.resolve())
            else:
                if expanded.is_dir():
                    matched_paths.append(expanded.resolve())
            for repo_path in matched_paths:
                logging.debug(f"Adding repo path: {repo_path}")
                repo = RepoConfig(
                    path=repo_path,
                    auto_pull=entry.get('auto_pull', True),
                    auto_push=entry.get('auto_push', False),
                    clean=entry.get('clean', False),
                    update_submodules=entry.get('update_submodules', False),
                    commands=entry.get('commands', []),
                )
                repos.append(repo)
        return cls(repos=repos)


class GitAround:
    """
    Core class handling git housekeeping tasks based on configuration.
    """
    def __init__(self, config: GitAroundConfig, dry_run: bool = False, stale_days: int = None):
        self.config = config
        self.dry_run = dry_run
        self.stale_days = stale_days
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
        mode = 'DRY RUN' if dry_run else 'LIVE'
        logging.debug(f"GitAround initialized (mode={mode}, stale_days={stale_days})")

    def run(self):
        if self.stale_days is not None:
            self._report_stale()
            return
        logging.info("Running GitAround...")
        for repo_cfg in self.config.repos:
            logging.info(f"Processing repository at: {repo_cfg.path}")
            if not repo_cfg.path.is_dir():
                logging.warning(f"Path does not exist or is not a directory: {repo_cfg.path}")
                continue
            self._process_repo(repo_cfg)

    def _process_repo(self, repo: RepoConfig):
        logging.info(f"Processing repo: {repo.path}")
        git_tasks = [
            (['git', 'pull'], repo.auto_pull),
            (['git', 'clean', '-fd'], repo.clean),
            (['git', 'submodule', 'update', '--init', '--recursive'], repo.update_submodules),
        ]
        for cmd_args, enabled in git_tasks:
            if enabled:
                self._run_command(cmd_args, shell=False, cwd=repo.path)
        for cmd in repo.commands:
            self._run_command(cmd, shell=True, cwd=repo.path)
        if repo.auto_push:
            self._run_command(['git', 'push'], shell=False, cwd=repo.path)

    def _run_command(self, cmd, shell: bool, cwd: Path):
        desc = 'shell' if shell else 'git'
        if self.dry_run:
            logging.info(f"[DRY RUN] Would execute {desc} command: {cmd} in {cwd}")
            return
        logging.info(f"Executing {desc} command: {cmd} in {cwd}")
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            logging.error(f"Command failed ({desc}): {cmd}")
            logging.error(result.stderr)
        else:
            logging.debug(result.stdout)

    def _report_stale(self):
        logging.info(f"Scanning for repositories stale for >= {self.stale_days} days...")
        cutoff = time.time() - (self.stale_days * 86400)
        for repo_cfg in self.config.repos:
            git_dir = repo_cfg.path
            if not git_dir.is_dir():
                continue
            # get last commit timestamp
            try:
                ts = subprocess.check_output(
                    ['git', 'log', '-1', '--format=%ct'],
                    cwd=git_dir,
                    text=True
                ).strip()
                last = int(ts)
                age_days = (time.time() - last) / 86400
                if last < cutoff or (repo_cfg.update_submodules and (repo_cfg.path / '.gitmodules').exists()):
                    logging.info(f"STALE: {repo_cfg.path} (last commit: {age_days:.1f} days ago)")
            except subprocess.CalledProcessError:
                logging.warning(f"Could not determine last commit for {repo_cfg.path}")


def main():
    parser = argparse.ArgumentParser(description='git-around: Git housekeeping')
    parser.add_argument('-n', '--dry-run', action='store_true', help='Show commands without executing')
    parser.add_argument('-s', '--stale', metavar='DAYS', type=int, nargs='?', const=30,
                        help='Report repos stale for DAYS (default 30) or with submodules')
    args = parser.parse_args()

    config_path = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config')) / 'git-around' / 'config.yaml'
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    logging.info(f"Using config file: {config_path}")
    config = GitAroundConfig.load_from_file(config_path)
    runner = GitAround(config, dry_run=args.dry_run, stale_days=args.stale)
    runner.run()


if __name__ == '__main__':
    main()
