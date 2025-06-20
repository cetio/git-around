[![AI qa3 - Pass](https://img.shields.io/badge/AI_qa3-Pass-2ea44f?logo=openai)](https://)
[![python - 3.7+](https://img.shields.io/badge/python-3.7%2B-blue?logo=python)](https://)

# git-around

Automate Git housekeeping easily and configurably using Python, allows for easily maintaining and keeping your repositories or adjacent modules up to date and keeping tabs on your work.

## Features

* Auto‑pull, auto‑push, clean untracked files
* Submodule updates
* Custom shell commands per repo
* Wildcard path support (e.g. `~/repos/*`)
* Dry‑run mode (`-n` / `--dry-run`)
* Stale repo scanning (`-s` / `--stale`)
* Systemd service and timer for automatic scheduling

## Dependencies

* Python 3.7 or newer
* PyYAML

Install dependencies with:

```bash
pip install pyyaml
```

## Installation

1. Clone or download the `git-around` repository.
2. Make the core script executable:

```bash
chmod +x git-around.py
```

3. (Optional) Move `git-around.py` into your `$PATH`.

## Configuration

Create a YAML file at `~/.config/git-around/config.yaml`:

```yaml
repos:
  # Single repo example
  - path: ~/projects/utils
    auto_pull: true
    auto_push: false
    clean: false
    update_submodules: false
    commands:
      - git fetch --prune
      - git checkout main

  # Wildcard: all git repos under ~/repos/
  - path: ~/repos/*
    auto_pull: true
    auto_push: false
    clean: false
    update_submodules: true
    commands:
      - echo "Updating: $(basename $PWD)"

  # Work project example
  - path: ~/work/client-app
    auto_pull: true
    auto_push: true
    clean: true
    update_submodules: true
    commands:
      - git checkout develop
      - git rebase origin/develop
```

## Usage

Run directly:

```bash
./git-around.py
```

For dry run (no execution):

```bash
./git-around.py -n
```

Scan for stale repos (default 30 days):

```bash
./git-around.py -s
```

Scan for repos untouched ≥7 days:

```bash
./git-around.py -s 7
```

## Systemd Integration

To schedule `git-around` automatically, create a service and timer.

1. **Service unit** (`~/.config/systemd/user/git-around.service`):

```ini
[Unit]
Description=Git Around Housekeeping

[Service]
Type=oneshot
ExecStart=%h/path/to/git-around/git-around.py
```

2. **Timer unit** (`~/.config/systemd/user/git-around.timer`):

```ini
[Unit]
Description=Run Git Around daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

3. Reload and enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now git-around.timer
```

This will run a daily dry‑run; remove `-n` in `ExecStart` for live execution.

## Logging

* Default level: `INFO`
* For `DEBUG`, edit `logging.basicConfig(level=logging.DEBUG, ...)` in `git-around.py`.

## Contributing

Please don't.

## License

git-around is licensed under the [AGPL-3.0 license](LICENSE.txt)
