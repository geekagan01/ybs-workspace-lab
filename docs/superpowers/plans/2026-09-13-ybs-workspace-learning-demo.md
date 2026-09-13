# YBS Workspace Learning Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 15 个可独立验证的学习日，从空目录实现一个可离线演示、可审计、可恢复的仓库型 AI 研发编排平台，并完整跑通 `DEMO-101`。

**Architecture:** 根仓库保存协议、声明式配置、任务状态和生成器；Python CLI 负责解释规则、执行受控状态迁移和写入结构化证据；两个 Git Submodule 提供跨项目前后端演示；外部企业系统全部由本地 Mock 适配器代替。任何写操作先经过配置校验、根目录边界、任务锁、原子替换和脱敏边界。

**Tech Stack:** Python 3.11+、Typer、Pydantic v2、PyYAML、pytest、Ruff、uv、Git/Git Bundle、POSIX Shell、Node.js 内置测试运行器。

**Spec:** `docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md`

## Global Constraints

- 所有命令默认从 `ybs-workspace-lab/` 根目录执行。
- 依赖由 `uv.lock` 锁定；开发与 CI 统一使用 `uv sync --frozen` 和 `uv run ...`。
- 测试先失败，再写最小实现；“缺少依赖”不算产品红测。
- 每个任务完成时必须运行本任务测试和累计回归，并由独立 reviewer/verifier 检查后再提交。
- 所有 Python 公共接口有类型标注；Pydantic 模型统一 `ConfigDict(extra="forbid")`。
- YAML 只用 `yaml.safe_load`；验证命令保存为参数数组并以 `shell=False` 执行。
- 所有持久化写入必须复用 Task 2 的安全路径、锁、原子写和脱敏能力。
- CLI 退出码固定为 `0` 成功、`2` 参数/配置、`3` 工作流门禁、`4` 适配器、`5` 文件/Git/执行错误。
- 普通 CLI 不自动提交、推送、重置、清理或删除 Git 数据。
- `--dry-run` 不得创建目录、锁、临时文件、状态、清单或 Mock 运行记录。
- 运行态 Mock 数据放 `mocks/runtime/` 并忽略；固定输入放 `mocks/fixtures/` 并提交。
- 每个任务的“提交”步骤只提交本任务列出的文件；若工作树中有无关修改，保留并排除。

## Specification Clarification SC-01: Six-tool Projection

官方配置能力并不完全对称，因此实现“共享语义”，不伪造不存在的原生目录：

| Tool | Repository rule projection | Skill/agent projection |
|---|---|---|
| Codex | 直接读取源 `AGENTS.md` | 直接读取源 `.agents/skills/`；可生成 `.codex/agents/*.toml` |
| Claude Code | 生成 `CLAUDE.md`，首行 `@AGENTS.md` | 生成 `.claude/skills/.../SKILL.md` 与 `.claude/agents/*.md` |
| Cursor | 生成 `.cursor/rules/ybs-workflow.mdc` | 直接发现源 `.agents/skills/`，避免重复 skill；生成 `.cursor/agents/*.md` 与可选命令文件 |
| Trae IDE | 生成 `.trae/rules/` 与 `.trae/skills/` | `.trae/agents/` 标记为 opt-in/beta；README 提醒启用导入开关 |
| Qoder | 根 `AGENTS.md` + 生成 `.qoder/skills/` | 生成 `.qoder/agents/*.md`；不提交本机私有设置 |
| OpenCode | 根 `AGENTS.md` + 直接复用 `.agents/skills/` | 生成 `.opencode/agents/*.md`；只在确有必要时生成 `opencode.json` |

这项澄清不改变“六工具可消费同一规则语义”的产品目标，只修正各工具的落盘形式。Cursor 当前官方文档明确支持项目级 `.agents/skills/`、`.cursor/skills/` 和 `.cursor/agents/`；本项目选择直接复用前者并只生成 agent，避免同名 skill 被发现两次。实现时以 [Cursor Agent Skills](https://cursor.com/docs/skills) 与 [Cursor Subagents](https://cursor.com/docs/subagents) 为契约依据。不得生成宽泛权限白名单、令牌、MCP 密钥或本机私有设置。

## Learning and Review Loop

每个学习日固定使用以下节奏：

1. 20 分钟：先读本任务的概念、接口和失败边界。
2. 50 分钟：把本任务中的“小步提示词”逐条交给 AI，不一次性要求 AI 写完整系统。
3. 60 分钟：亲自读测试、关键分支和失败消息，再运行验收命令。
4. 20 分钟：在当天提交信息或学习笔记中回答“我能否不看代码解释数据流、失败点和恢复方式”。

---

## Task 1 — Day 1: Initialize the Repository and Installable CLI

**Concept:** Python 包、命令入口、稳定退出码、仓库根目录定位。

**Files:**

- Create: `.gitignore`
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `bin/ybs`
- Create: `src/ybs_cli/__init__.py`
- Create: `src/ybs_cli/__main__.py`
- Create: `src/ybs_cli/cli.py`
- Create: `src/ybs_cli/errors.py`
- Create: `src/ybs_cli/root.py`
- Test: `tests/integration/test_cli_entrypoint.py`

**Interfaces:**

- Produces: `app: typer.Typer`
- Produces: `main() -> None`
- Produces: `YbsError(message: str, code: int)`
- Produces: `find_workspace_root(start: Path) -> Path`
- Consumes later: every command uses `find_workspace_root(Path.cwd())` and the exit-code contract.

- [ ] Initialize an independent repository and create the locked environment.

```bash
git init -b main
uv python pin 3.11
```

Create `pyproject.toml` with this baseline:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ybs-workspace-lab"
version = "0.1.0"
description = "Repository-first AI development orchestration learning lab"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.11,<3",
  "PyYAML>=6.0,<7",
  "typer>=0.16,<1",
]

[dependency-groups]
dev = [
  "pytest>=8.4,<10",
  "ruff>=0.12,<1",
]

[project.scripts]
ybs = "ybs_cli.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/ybs_cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

Run `uv sync` once to produce `uv.lock`. Add `.venv/`, `.demo/`, `mocks/runtime/`, caches and build outputs to `.gitignore`.

- [ ] Write the failing CLI contract test.

```python
from pathlib import Path
from typer.testing import CliRunner

from ybs_cli.cli import app


runner = CliRunner()


def test_help_and_version_are_available() -> None:
    help_result = runner.invoke(app, ["--help"])
    version_result = runner.invoke(app, ["--version"])

    assert help_result.exit_code == 0
    assert "Repository-first AI development orchestration" in help_result.stdout
    assert version_result.exit_code == 0
    assert "0.1.0" in version_result.stdout


def test_find_workspace_root_from_nested_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "docs" / "notes"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[tool.ybs]\nworkspace = true\n")

    from ybs_cli.root import find_workspace_root

    assert find_workspace_root(nested) == root
```

Run:

```bash
uv run pytest tests/integration/test_cli_entrypoint.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'ybs_cli'` or missing `app`/`find_workspace_root`.

- [ ] Implement the minimal CLI, error type, root finder and shell entry.

`src/ybs_cli/root.py` must walk `start.resolve()` and its parents, accepting only a `pyproject.toml` whose parsed text contains `[tool.ybs]` and `workspace = true`. If no marker exists, raise `YbsError(..., 5)`.

Add this marker to `pyproject.toml`:

```toml
[tool.ybs]
workspace = true
```

The thin shell entry is:

```sh
#!/bin/sh
set -eu
REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec uv run --project "$REPO_ROOT" ybs "$@"
```

Make it executable with `chmod +x bin/ybs`. `src/ybs_cli/cli.py` exposes `--version` and a basic `doctor` command that reports the Python version and root path; the full doctor is added in Task 14.

- [ ] Verify the installed command and exit contract.

```bash
uv lock --check
uv run pytest tests/integration/test_cli_entrypoint.py -q
uv run ybs --help
./bin/ybs doctor
uv run ybs unknown-command
```

Expected: first four commands succeed; the last exits `2` without a traceback.

- [ ] Ask an independent reviewer to verify packaging, root detection and error mapping, then commit.

```bash
git add .gitignore .python-version pyproject.toml uv.lock bin src tests/integration/test_cli_entrypoint.py
git commit -m "feat: add installable ybs command and exit contracts"
```

**Review focus:** explain why Typer parse errors are `2`, why operational exceptions must be mapped centrally, and why `bin/ybs` contains no business logic.

---

## Task 2 — Day 2: Safe Paths, Atomic Writes, Locks, and Redaction

**Concept:** write-ahead safety boundary. This task is intentionally earlier than the original teaching outline because no stateful command may write before it exists.

**Files:**

- Create: `src/ybs_cli/filesystem.py`
- Create: `src/ybs_cli/redaction.py`
- Modify: `src/ybs_cli/errors.py`
- Test: `tests/unit/test_filesystem.py`
- Test: `tests/unit/test_redaction.py`

**Interfaces:**

- Produces: `resolve_inside(root: Path, candidate: str | Path) -> Path`
- Produces: `atomic_write(path: Path, content: bytes) -> None`
- Produces: `task_lock(root: Path, task_id: str) -> ContextManager[None]`
- Produces: `redact(value: object, secrets: Sequence[str] = ()) -> object`
- Consumes later: every state, manifest, schema and Mock write.

- [ ] Write red tests for path traversal, symlink escape, interrupted replacement and lock contention.

```python
def test_resolve_inside_rejects_parent_escape(tmp_path: Path) -> None:
    with pytest.raises(YbsError, match="outside workspace"):
        resolve_inside(tmp_path, "../secret.txt")


def test_resolve_inside_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(YbsError, match="outside workspace"):
        resolve_inside(tmp_path, "link/secret.txt")


def test_atomic_write_preserves_old_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "status.yaml"
    target.write_bytes(b"stage: intake\n")
    monkeypatch.setattr("ybs_cli.filesystem.os.replace", Mock(side_effect=OSError("boom")))
    with pytest.raises(YbsError, match="atomic write failed"):
        atomic_write(target, b"stage: clarify\n")
    assert target.read_bytes() == b"stage: intake\n"
```

Add lock tests asserting an active same-host PID cannot be stolen, a confirmed dead same-host PID can be recovered, and an unknown remote-host lock is never auto-recovered.

Run `uv run pytest tests/unit/test_filesystem.py -q`; expect missing-module failures.

- [ ] Implement the safety primitives.

`resolve_inside` must resolve both root and candidate and use `Path.relative_to` to prove containment. `atomic_write` must create a named temporary file in the target directory, write bytes, flush, call `os.fsync`, then `os.replace`; on failure it removes only the exact temporary file. The task lock file is `.ybs/locks/<task-id>.lock` and contains JSON `{pid, host, created_at}`. Validate `task_id` against `^[A-Z][A-Z0-9-]{1,63}$` before constructing the path.

- [ ] Write redaction tests before implementing redaction.

```python
def test_redact_nested_values_headers_and_query_strings() -> None:
    value = {
        "Authorization": "Bearer top-secret",
        "url": "https://example.test/run?token=abc123&safe=yes",
        "nested": {"api_key": "abc123", "message": "use abc123"},
    }
    result = redact(value, secrets=["abc123", "top-secret"])
    rendered = json.dumps(result)
    assert "abc123" not in rendered
    assert "top-secret" not in rendered
    assert "***REDACTED***" in rendered
```

Implement recursive mapping/list/tuple handling; redact keys matching `authorization|token|secret|password|api[_-]?key` case-insensitively; replace explicit secret substrings everywhere; parse and rebuild URL query strings with sensitive values replaced.

- [ ] Run focused and cumulative verification.

```bash
uv run pytest tests/unit/test_filesystem.py tests/unit/test_redaction.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

- [ ] Obtain independent review, then commit.

```bash
git add src/ybs_cli/errors.py src/ybs_cli/filesystem.py src/ybs_cli/redaction.py tests/unit
git commit -m "feat: add safe atomic storage locking and redaction"
```

**Review focus:** path containment after symlink resolution, exact cleanup targets, lock recovery proof and secrets in nested/error data.

---

## Task 3 — Day 3: Strict Configuration Models and JSON Schema

**Concept:** configuration is a typed contract; YAML is input, not truth until validated.

**Files:**

- Create: `src/ybs_cli/models.py`
- Create: `src/ybs_cli/config.py`
- Create: `src/ybs_cli/schemas.py`
- Create: `workspace/projects.yaml`
- Create: `workspace/feature-routing.yaml`
- Create: `workspace/workflow.yaml`
- Create: `workspace/adapters.yaml`
- Create: `workspace/schemas/projects.schema.json`
- Create: `workspace/schemas/feature-routing.schema.json`
- Create: `workspace/schemas/workflow.schema.json`
- Create: `workspace/schemas/adapters.schema.json`
- Modify: `src/ybs_cli/cli.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/integration/test_config_cli.py`

**Interfaces:**

- Produces: `ProjectType`, `ProjectSpec`, `ProjectsConfig`
- Produces: `RoutingRule`, `RoutingConfig`, `WorkflowStageSpec`, `WorkflowConfig`
- Produces: `AdapterSpec`, `AdaptersConfig`, `WorkspaceConfig`
- Produces: `load_yaml(path: Path) -> dict[str, Any]`
- Produces: `load_config(root: Path) -> WorkspaceConfig`
- Produces: `export_schemas(root: Path, dry_run: bool = False) -> dict[str, str]`

- [ ] Write failing model tests for unknown fields and malformed YAML.

Use these exact core fields:

```python
class ProjectSpec(StrictModel):
    key: str
    name: str
    path: str
    type: Literal["frontend", "backend", "support"]
    stack: list[str]
    business_domains: list[str]
    dependencies: list[str] = []
    project_doc: str
    verify_commands: list[list[str]]


class RoutingRule(StrictModel):
    key: str
    feature: str
    keywords: list[str]
    primary_projects: list[str]
    fallback_projects: list[str] = []
    priority: int = 0


class WorkflowStageSpec(StrictModel):
    requires: list[str] = []
    required_evidence: list[str] = []
    manual_approval: bool = False
    next: str | None = None


class AdapterSpec(StrictModel):
    driver: Literal["issue_mock", "wiki_mock", "ci_mock", "notification_mock"]
    enabled: bool = True
    fixture_dir: str
    runtime_dir: str
    timeout_seconds: float = 2.0
    credential_env: str | None = None
```

`StrictModel` is a `BaseModel` with `model_config = ConfigDict(extra="forbid")`; use `Field(default_factory=list)` instead of mutable list literals in implementation.

Tests must reject duplicate project/rule keys, missing dependency, self-dependency, dependency cycles, route references to unknown projects, root-escaping paths, top-level YAML lists, unknown fields and any credential value field.

Run `uv run pytest tests/unit/test_config.py -q`; expect missing types/loaders.

- [ ] Implement safe loading and cross-file validation.

`load_yaml` calls `yaml.safe_load`, requires a mapping, and maps YAML/parser/Pydantic errors to exit code `2` after `redact`. `load_config` loads all four files, then performs graph and cross-reference checks before returning one immutable `WorkspaceConfig` view.

Populate the two demo projects now, but their paths need not exist until bootstrap:

```yaml
version: 1
projects:
  - key: demo-api
    name: Demo API
    path: projects/demo-api
    type: backend
    stack: [python-stdlib]
    business_domains: [api, status, service]
    dependencies: []
    project_doc: projects/demo-api/AGENTS.md
    verify_commands: [[python3, -m, unittest, discover, -s, tests]]
  - key: demo-web
    name: Demo Web
    path: projects/demo-web
    type: frontend
    stack: [html, javascript, node-test]
    business_domains: [web, workbench, status]
    dependencies: [demo-api]
    project_doc: projects/demo-web/AGENTS.md
    verify_commands: [[node, --test, test/status.test.js]]
```

- [ ] Add `ybs config validate [--json]` and deterministic schema export.

`export_schemas` serializes each model's `model_json_schema()` using sorted keys and a trailing newline, compares before writing, and uses `atomic_write`. The validate command checks committed schema files match current models; `--json` prints exactly one JSON object with `ok`, `files`, and `errors`.

- [ ] Verify positive and negative paths.

```bash
uv run ybs config validate --json
uv run pytest tests/unit/test_config.py tests/integration/test_config_cli.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Expected: valid repository returns `0`; a copied fixture with a cycle returns `2`, names the dependency field, and contains no injected secret.

- [ ] Obtain independent review, then commit.

```bash
git add workspace src/ybs_cli tests/unit/test_config.py tests/integration/test_config_cli.py
git commit -m "feat: validate workspace configuration and export schemas"
```

**Review focus:** no unsafe YAML loader, deterministic schemas, complete cross-file references and `verify_commands` remaining argv arrays.

---

## Task 4 — Day 4: Offline Git Submodules and Project Graph

**Concept:** Gitlink, `.gitmodules`, Bundle-based offline recovery, dependency graph.

**Files:**

- Create: `src/ybs_cli/git.py`
- Create: `src/ybs_cli/projects.py`
- Create: `src/ybs_cli/demo.py`
- Create: `.gitmodules`
- Create binary artifact: `fixtures/repos/demo-api.bundle`
- Create binary artifact: `fixtures/repos/demo-web.bundle`
- Add gitlinks: `projects/demo-api`, `projects/demo-web`
- Modify: `.gitignore`
- Modify: `src/ybs_cli/cli.py`
- Test: `tests/unit/test_project_graph.py`
- Test: `tests/integration/test_demo_bootstrap.py`

**Interfaces:**

- Produces: `ProjectRegistry.from_config(config: WorkspaceConfig) -> ProjectRegistry`
- Produces: `ProjectRegistry.dependency_closure(keys: Sequence[str]) -> list[str]`
- Produces: `ProjectRegistry.topological_order(keys: Sequence[str] | None = None) -> list[str]`
- Produces: `GitSnapshot(head: str | None, branch: str | None, dirty_paths: list[str])`
- Produces: `read_git_snapshot(root: Path) -> GitSnapshot`
- Produces: `bootstrap_demo(root: Path, dry_run: bool = False) -> BootstrapResult`

- [ ] Write the dependency graph red tests.

```python
def test_dependency_closure_is_stable_and_dependency_first(config: WorkspaceConfig) -> None:
    registry = ProjectRegistry.from_config(config)
    assert registry.dependency_closure(["demo-web"]) == ["demo-api", "demo-web"]


def test_graph_rejects_unknown_project(config: WorkspaceConfig) -> None:
    registry = ProjectRegistry.from_config(config)
    with pytest.raises(YbsError, match="unknown project"):
        registry.dependency_closure(["missing"])
```

Run `uv run pytest tests/unit/test_project_graph.py -q`; expect missing registry.

- [ ] Build deterministic baseline repositories and Bundles.

`demo-api` baseline contains `server.py`, `tests/test_server.py`, and `AGENTS.md`; `demo-web` baseline contains `package.json`, `index.html`, `src/status.js`, `test/status.test.js`, and `AGENTS.md`. At this stage the status endpoint/renderer tests are skipped with the exact reason `DEMO-101 is implemented on Day 13`; basic syntax/smoke tests still pass.

In the `demo-api` seed repository:

```bash
git init -b teaching-baseline
git add .
git -c user.name="YBS Demo" -c user.email="demo@ybs.invalid" commit -m "chore: add teaching baseline"
git tag teaching-baseline
git bundle create ../../fixtures/repos/demo-api.bundle --all
git bundle verify ../../fixtures/repos/demo-api.bundle
```

In the `demo-web` seed repository:

```bash
git init -b teaching-baseline
git add .
git -c user.name="YBS Demo" -c user.email="demo@ybs.invalid" commit -m "chore: add teaching baseline"
git tag teaching-baseline
git bundle create ../../fixtures/repos/demo-web.bundle --all
git bundle verify ../../fixtures/repos/demo-web.bundle
```

The final plan executor must record the two resulting baseline SHAs in the Task 4 commit message body.

- [ ] Add the submodules and replace machine paths with portable placeholders.

Restore each Bundle as a bare repository under ignored `.demo/remotes/<name>.git`, add it as a submodule using the one-command local protocol allowance, then set the committed URL:

```ini
[submodule "projects/demo-api"]
    path = projects/demo-api
    url = https://invalid.example/ybs/demo-api.git
[submodule "projects/demo-web"]
    path = projects/demo-web
    url = https://invalid.example/ybs/demo-web.git
```

Keep the actual absolute local URL only in the superproject's uncommitted `.git/config`. Never enable `protocol.file.allow` globally.

- [ ] Write bootstrap red tests against self-contained temporary Git repositories.

The integration fixture first creates two temporary seed repositories, commits their baseline files, creates real Bundles, then creates and commits a temporary superproject with real mode-`160000` gitlinks and portable `.gitmodules` URLs. It clones **that committed temporary superproject**, removes its seed sources, restores each Bundle to `.demo/remotes`, configures `submodule.<name>.url` locally, and invokes:

```text
git -c protocol.file.allow=always submodule update --init --recursive
```

Assert both submodule HEADs equal the superproject gitlink, both gitlink SHAs exist in the matching Bundle, a second bootstrap is unchanged, `--dry-run` writes nothing, and a corrupt Bundle returns `5` without replacing an existing remote or submodule. This red test validates the algorithm without depending on Task 4 artifacts that have not yet been committed.

- [ ] Implement project commands and bootstrap.

Add `ybs project list [--json]`, `ybs project graph [--json]`, and `ybs demo bootstrap [--dry-run]`. Subprocess execution always passes argv lists, `cwd`, `check=False`, `text=True`, and `shell=False`. Before changing local Git config, validate both Bundles with `git bundle verify` and verify the expected gitlink object is advertised.

- [ ] Verify offline reconstruction and cumulative tests.

```bash
uv run pytest tests/unit/test_project_graph.py tests/integration/test_demo_bootstrap.py -q
uv run ybs project graph --json
uv run ybs demo bootstrap
git submodule status
uv run pytest -q
```

Expected: graph order is `demo-api`, then `demo-web`; submodule status has no leading `-` or `+`.

- [ ] Obtain independent Git safety review, then commit and verify the committed artifact from a clean clone.

```bash
git add .gitignore .gitmodules fixtures/repos projects src/ybs_cli tests
git commit -m "feat: bootstrap bundled demo submodules offline"
```

After the commit, clone that exact commit to a temporary directory without initialized submodules, run `uv run ybs demo bootstrap`, and compare submodule HEADs to `git ls-tree HEAD projects/demo-api projects/demo-web`. Task 4 is not accepted until this post-commit check passes; fix failures in a follow-up Task 4 commit rather than rewriting unrelated history.

**Review focus:** Bundle/gitlink consistency, no absolute path in commits, no global Git config and idempotent bootstrap.

---

## Task 5 — Day 5: Explainable Routing and Scope Suggestions

**Concept:** routing is a deterministic suggestion; human-approved scope is separate state.

**Files:**

- Create: `src/ybs_cli/routing.py`
- Modify: `src/ybs_cli/cli.py`
- Modify: `workspace/feature-routing.yaml`
- Test: `tests/unit/test_routing.py`
- Test: `tests/integration/test_route_cli.py`

**Interfaces:**

- Produces: `RouteResult(matched_rules, primary_projects, dependency_projects, fallback_projects, explanation, needs_manual_scope)`
- Produces: `route_request(config: WorkspaceConfig, text: str) -> RouteResult`
- Consumes: `ProjectRegistry.dependency_closure`.
- Consumed later by: `TaskService.record_route`.

- [ ] Add the exact DEMO-101 routing rule.

```yaml
version: 1
rules:
  - key: workbench-api-status
    feature: Workbench API service status
    keywords: [演示工作台, API, 服务状态, status]
    primary_projects: [demo-web]
    fallback_projects: []
    priority: 100
```

- [ ] Write routing red tests.

```python
def test_demo_101_routes_frontend_then_adds_api_dependency(config: WorkspaceConfig) -> None:
    result = route_request(config, "在演示工作台显示 API 服务状态")
    assert result.primary_projects == ["demo-web"]
    assert result.dependency_projects == ["demo-api"]
    assert result.fallback_projects == []
    assert result.needs_manual_scope is False
    assert result.matched_rules == ["workbench-api-status"]


def test_no_match_requests_manual_scope(config: WorkspaceConfig) -> None:
    result = route_request(config, "完全未知的请求")
    assert result.primary_projects == []
    assert result.needs_manual_scope is True
    assert "人工缩圈" in result.explanation
```

Also test case-folded English matching, deterministic tie-break by `(-priority, key)`, duplicate keyword scoring only once, and fallback projects never appearing in the actual dependency closure.

Run `uv run pytest tests/unit/test_routing.py -q`; expect missing implementation.

- [ ] Implement the pure routing function and read-only CLI.

Normalize text with `unicodedata.normalize("NFKC", text).casefold()`. A rule matches when any normalized keyword is a substring. Sort matched rules by descending priority then key, preserve config order only inside each rule's project lists, and deduplicate deterministically. Build `dependency_projects` as closure members not already primary. The explanation names every rule and dependency edge used.

At this task, `ybs route TEXT` is read-only. If `--task` is supplied, return exit `3` with `task storage is added on Day 7` rather than silently ignoring it.

- [ ] Verify human and JSON output.

```bash
uv run ybs route "在演示工作台显示 API 服务状态"
uv run ybs route "在演示工作台显示 API 服务状态" --json
uv run pytest tests/unit/test_routing.py tests/integration/test_route_cli.py -q
uv run pytest -q
```

- [ ] Obtain independent review, then commit.

```bash
git add workspace/feature-routing.yaml src/ybs_cli/cli.py src/ybs_cli/routing.py tests
git commit -m "feat: explain project routing and dependency scope"
```

**Review focus:** deterministic ordering, no fuzzy guesses, dependency closure separated from fallback suggestions and no state writes.

---

## Task 6 — Day 6: Typed Task State and Pure Workflow Machine

**Concept:** current stage, evidence checked on leaving a stage, restricted terminal operations and idempotent replay.

**Files:**

- Create: `src/ybs_cli/task_models.py`
- Create: `src/ybs_cli/workflow.py`
- Modify: `workspace/workflow.yaml`
- Test: `tests/unit/test_workflow.py`

**Interfaces:**

- Produces: `TaskKind`, `TaskLevel`, `Stage`, `ApprovalRecord`, `EvidenceRecord`, `TaskState`
- Produces: `TransitionContext(operation, approval, evidence)`
- Produces: `transition(state: TaskState, target: Stage, workflow: WorkflowConfig, context: TransitionContext) -> TaskState`
- Consumed later by: `TaskService.advance`, `sync_task`, `finish_task`.

- [ ] Define the exact state shape and write serialization tests.

```python
class TaskState(StrictModel):
    version: Literal[1] = 1
    task_id: str
    title: str
    kind: Literal["requirement", "bug"]
    level: Literal["L0", "L1", "L2"]
    original_level: Literal["L0", "L1", "L2"]
    stage: Stage = Stage.intake
    scope: ScopeState = Field(default_factory=ScopeState)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    evidence: dict[str, EvidenceRecord] = Field(default_factory=dict)
    external_sync: dict[str, ExternalSyncRecord] = Field(default_factory=dict)
    completed_operations: dict[str, OperationRecord] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
```

`ApprovalRecord` contains `stage`, `approved_by`, `approved_at`, optional `document_path`, and optional `document_sha256`. `EvidenceRecord` contains `key`, `path`, `sha256`, `recorded_at`, and `metadata`. Datetimes serialize as UTC ISO-8601 with `Z`.

- [ ] Write failing transition tests for every gate.

```python
def test_evidence_is_checked_when_leaving_current_stage(state_at_scope, workflow) -> None:
    with pytest.raises(GateError, match="route_suggestion"):
        transition(
            state_at_scope,
            Stage.plan,
            workflow,
            TransitionContext(operation="advance"),
        )


def test_advance_cannot_enter_commit(state_at_external_sync, workflow) -> None:
    with pytest.raises(GateError, match="task sync"):
        transition(
            state_at_external_sync,
            Stage.commit,
            workflow,
            TransitionContext(operation="advance"),
        )


def test_identical_operation_replay_is_idempotent(ready_state, workflow) -> None:
    context = TransitionContext(operation="advance", operation_id="op-123")
    first = transition(ready_state, Stage.clarify, workflow, context)
    second = transition(first, Stage.clarify, workflow, context)
    assert second == first
```

Include table-driven tests for all 11 edges, skipping a stage, missing approval, missing evidence, `sync` as the only operation that can enter `commit`, and `finish` as the only operation that can enter `done`.

Run `uv run pytest tests/unit/test_workflow.py -q`; expect missing types/state machine.

- [ ] Implement a pure transition function.

The function must not read files or mutate its input. It verifies `state.level == state.original_level`, current-stage `required_evidence`, a current-stage approval when configured, the direct `next` value, and the terminal operation restriction. Return `state.model_copy(update=...)`.

`OperationRecord` stores `source`, `target`, `context_digest`, and `completed_at`. At function entry, check whether `operation_id` already exists **before** validating a new edge. An exact replay succeeds only when the current stage equals the stored target, the requested target equals the stored target, and a digest of normalized context fields (excluding current stage and timestamps) equals `context_digest`; return the input state unchanged. A reused ID with any other value is a conflict. On a new transition, record the pre-transition source explicitly, so the digest never changes merely because stage advanced.

The CLI derives stable IDs without the mutable current stage: `advance:<task-id>:<target>:<context-digest>`, `sync:<task-id>:external_sync`, and `finish:<task-id>:<resolved-commit-sha>`. The service passes that ID into `TransitionContext`; tests invoke the same public command twice and assert the second call finds the same record rather than constructing a new transition.

- [ ] Verify the whole transition matrix.

```bash
uv run pytest tests/unit/test_workflow.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

- [ ] Obtain independent state-machine review, then commit.

```bash
git add workspace/workflow.yaml src/ybs_cli/task_models.py src/ybs_cli/workflow.py tests/unit/test_workflow.py
git commit -m "feat: model guarded workflow transitions"
```

**Review focus:** evidence timing, direct successor only, immutable level, replay digest and terminal-operation restriction.

---

## Task 7 — Day 7: Task Start, Scope, State Persistence, and Memory

**Concept:** `status.yaml` is machine truth; `memory.md` is a readable process summary; route suggestions never equal approved scope.

**Files:**

- Create: `src/ybs_cli/task_repository.py`
- Create: `src/ybs_cli/task_service.py`
- Create: `src/ybs_cli/memory.py`
- Create: `templates/task-memory.md`
- Create directories: `workspace-memory/in-progress/`, `workspace-memory/done/`, `workspace-memory/feedback/`
- Modify: `src/ybs_cli/cli.py`
- Modify: `.gitignore`
- Test: `tests/integration/test_task_lifecycle.py`

**Interfaces:**

- Produces: `TaskRepository(root: Path)`
- Produces: `TaskRepository.find(task_id: str) -> TaskLocation | None`
- Produces: `TaskRepository.load(task_id: str) -> TaskState`
- Produces: `TaskRepository.save(state: TaskState) -> None`
- Produces: `TaskService.start(task_id, title, kind, level, dry_run=False) -> TaskState`
- Produces: `TaskService.record_route(task_id, result, dry_run=False) -> TaskState`
- Produces: `TaskService.set_scope(task_id, project_keys, approve_by, tdd_required: bool | None, dry_run=False) -> TaskState`

- [ ] Write the failing lifecycle integration tests.

```python
def test_start_creates_state_and_memory(repo: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["task", "start", "DEMO-101", "--title", "API status", "--kind", "requirement", "--level", "L2"],
    )
    assert result.exit_code == 0
    task_dir = next((repo / "workspace-memory/in-progress").glob("DEMO-101-*"))
    state = yaml.safe_load((task_dir / "status.yaml").read_text())
    assert state["task_id"] == "DEMO-101"
    assert state["level"] == state["original_level"] == "L2"
    assert state["stage"] == "intake"
    assert (task_dir / "memory.md").exists()
    assert (task_dir / "evidence/git-start.json").exists()
    assert (task_dir / "evidence/task-start.json").exists()


def test_route_suggestion_does_not_set_scope(repo_with_task: Path, runner: CliRunner) -> None:
    result = runner.invoke(app, ["route", "在演示工作台显示 API 服务状态", "--task", "DEMO-101"])
    assert result.exit_code == 0
    state = TaskRepository(repo_with_task).load("DEMO-101")
    assert state.scope.projects == []
    assert "route_suggestion" in state.evidence
```

Also test invalid task IDs, duplicate identical start, conflicting duplicate start, lookup in both in-progress and done directories, unknown scope projects, blank approver, slug normalization and zero writes in every dry-run. Manually changing `level` or `original_level` in status while leaving start evidence unchanged must block the next write. For scope decisions, L1 must supply exactly one of `--tdd-required` or `--no-tdd-required`; L2 always stores `tdd_required: true`; L0 defaults false, while an explicit true opts into the same TDD evidence gate.

Run `uv run pytest tests/integration/test_task_lifecycle.py -q`; expect missing repository/service.

- [ ] Implement deterministic task directories and YAML serialization.

Directory names are `<task-id>-<slug>`, where slug is lowercase ASCII derived from the title, non-alphanumerics collapse to `-`, and an empty result becomes `task`. Repository lookup reads exact `status.yaml` values rather than trusting a directory name. More than one matching task is corruption and exits `5`.

Serialize state with `yaml.safe_dump(..., sort_keys=False, allow_unicode=True)`, a trailing newline and `atomic_write`. The memory renderer is deterministic Markdown and includes input, current stage, approved scope, decisions, risks, latest validation, and next step without copying SRS/TDD bodies.

- [ ] Implement start, route evidence and scope commands under a task lock.

`start` records the immutable input tuple `task_id/title/kind/level/created_at` in `evidence/task-start.json` and `read_git_snapshot(root)` in `evidence/git-start.json`, then status and memory. Every later write re-reads task-start evidence and requires its digest plus level to match the state; this is local tamper evidence for accidental edits, not protection against an attacker who rewrites every local file. Because a new task directory does not yet exist, its lock lives in root `.ybs/locks/`. Before saving, load and validate repository config. For repeat start, compare task ID/title/kind/level and return existing state only if all match.

`route --task` writes `evidence/route-suggestion.json` and its SHA record, but not scope. `task set-scope` validates keys, requires an approver, writes `scope.projects`, `scope.approved_by`, `scope.approved_at`, `scope.tdd_required`, and adds an approval bound to stage `scope`. The CLI exposes the paired Typer option `--tdd-required/--no-tdd-required`; omission is valid for L0/L2 but rejected for L1.

- [ ] Verify the commands and inspect readable output.

```bash
uv run ybs task start DEMO-101 --title "在演示工作台显示 API 服务状态" --kind requirement --level L2 --dry-run
uv run ybs task start DEMO-101 --title "在演示工作台显示 API 服务状态" --kind requirement --level L2
uv run ybs route "在演示工作台显示 API 服务状态" --task DEMO-101
uv run ybs task set-scope DEMO-101 --projects demo-web,demo-api --approve-by learner --tdd-required
uv run ybs task show DEMO-101 --json
uv run pytest tests/integration/test_task_lifecycle.py -q
uv run pytest -q
```

- [ ] Remove the manual DEMO-101 task created during the command rehearsal only if it is uncommitted and exactly matched, obtain independent review, then commit implementation files.

```bash
git add .gitignore templates workspace-memory src/ybs_cli tests/integration/test_task_lifecycle.py
git commit -m "feat: persist task state scope and readable memory"
```

**Review focus:** lock covers the complete read/validate/write transaction, archived lookup works, dry-run has zero side effects and route does not approve scope.

---

## Task 8 — Day 8: SRS/TDD Templates and Approval-bound Document Gates

**Concept:** file existence is not approval; approvals bind a stage, reviewer, path and content digest.

**Files:**

- Create: `AGENTS.md`
- Create: `.agents/rules/workflow.md`
- Create: `.agents/skills/task-workflow/SKILL.md`
- Create: `templates/srs.md`
- Create: `templates/tdd.md`
- Create: `templates/project-agent.md`
- Create: `src/ybs_cli/documents.py`
- Modify: `src/ybs_cli/task_service.py`
- Modify: `src/ybs_cli/cli.py`
- Test: `tests/unit/test_document_gates.py`
- Test: `tests/integration/test_task_advance.py`

**Interfaces:**

- Produces: `DocumentEvidence(path: str, sha256: str, approved_by: str, approved_at: datetime)`
- Produces: `parse_evidence_arg(value: str) -> tuple[str, str]`
- Produces: `record_document_approval(root, state, key, path, approved_by) -> TaskState`
- Produces: `validate_plan_evidence(state: TaskState, root: Path) -> None`
- Produces: `TaskService.advance(task_id, target, approve_by=None, evidence=(), dry_run=False) -> TaskState`

- [ ] Write exact templates and repository protocol before implementing gates.

`AGENTS.md` states the stage order, L0/L1/L2 document rules, no automatic Git mutation, read-before-write, deterministic verification, memory/document boundary, generated-file rule and secret rule. `.agents/rules/workflow.md` expands only workflow examples. The Skill contains YAML frontmatter with `name: task-workflow` and a stepwise procedure that invokes public `ybs` commands rather than internal modules.

`templates/srs.md` has headings: Context, Goal, Non-goals, User-visible Behavior, Acceptance Criteria, Scope, Risks, Approval. `templates/tdd.md` has Architecture, Interfaces, Data Flow, Failure Handling, Security, Test Strategy, Rollback, Approval. The document Approval section holds the human-readable reviewer name only. The SHA-256 of the complete file bytes is stored exclusively in `status.yaml`'s `ApprovalRecord`/`EvidenceRecord`, avoiding a digest that tries to include itself.

- [ ] Write red tests for level-specific evidence.

```python
@pytest.mark.parametrize(
    ("level", "evidence", "expected_error"),
    [
        ("L0", {}, "memory_plan"),
        ("L1", {}, "srs"),
        ("L2", {"srs": approved_srs}, "tdd"),
    ],
)
def test_plan_gate_requires_level_evidence(level, evidence, expected_error, task_state, root) -> None:
    state = task_state.model_copy(update={"level": level, "original_level": level, "evidence": evidence})
    with pytest.raises(GateError, match=expected_error):
        validate_plan_evidence(state, root)


def test_document_change_invalidates_approval(approved_l2_state, root: Path) -> None:
    path = root / approved_l2_state.evidence["srs"].path
    path.write_text(path.read_text() + "\nchanged\n")
    with pytest.raises(GateError, match="digest"):
        validate_plan_evidence(approved_l2_state, root)
```

L1 `scope.tdd_required` must be an explicit boolean. L2 always requires both documents. L0 requires `memory_plan` and `memory_validation` evidence recorded from its memory file sections.

- [ ] Implement evidence parsing and approval binding.

`--evidence` accepts repeated `key=relative/path` values. Supported document keys are `srs`, `tdd`, `memory_plan`, `memory_validation`, `validation`, and `memory_updated`; unknown keys exit `2`. A document evidence entry is accepted only with nonblank `--approve-by`, a regular file inside the root, and a digest computed at recording time. Re-read and compare the digest whenever the gate is evaluated.

An `advance` operation first builds a candidate context and calls pure `transition` under one task lock. `status.yaml` is the only transaction commit point. `memory.md` has a generated block delimited by `<!-- ybs:generated:start/end -->` and a separate `## Learner Notes` block whose bytes are always preserved.

Before a two-file update, write `.ybs/task-intents/<task-id>.json` containing prior/candidate status digests and prior/candidate generated-memory digests. Write memory first, status last, then remove the exact intent. A read-only command such as `task show` or any `--dry-run` never repairs files; it reports `recovery_required: true` while returning the authoritative current status. The next **write** command acquires the task lock and calls `recover_task_transaction`: if status has the prior digest, restore only the prior generated block; if it has the candidate digest, finish the candidate generated block; preserve Learner Notes in both cases, then remove the intent. Any other digest is ambiguous and exits `5` without writing. Tests inject memory-write, status-write and intent-cleanup failures and prove this convergence. The approval applies only to the stage being left; it does not implicitly approve SRS/TDD unless they are supplied as evidence in the same operation.

- [ ] Exercise every level and the L2 happy path through `implement`.

The public command form exercised by integration fixtures is `uv run ybs task advance DEMO-101 --to branch_confirm --approve-by learner`; fixtures create the task and required current-stage evidence first.

```bash
uv run ybs task advance --help
uv run pytest tests/unit/test_document_gates.py tests/integration/test_task_advance.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Expected: digest mutation and missing approver exit `3`; malformed `key=path` exits `2`; successful direct-successor transitions update exactly one history record.

- [ ] Obtain independent protocol/gate review, then commit.

```bash
git add AGENTS.md .agents templates src/ybs_cli tests
git commit -m "feat: enforce approved requirements and design gates"
```

**Review focus:** approval meaning is unambiguous, document digest is rechecked, L1 decision is explicit and protocol/CLI agree.

---

## Task 9 — Day 9: Deterministic Validation and Fresh Evidence

**Concept:** a passing file is not enough; evidence is trustworthy only when bound to commands, scope and current Git content.

**Files:**

- Create: `src/ybs_cli/validation.py`
- Modify: `src/ybs_cli/git.py`
- Modify: `src/ybs_cli/task_service.py`
- Modify: `src/ybs_cli/cli.py`
- Test: `tests/integration/test_task_validation.py`

**Interfaces:**

- Produces: `CommandResult(argv, cwd, exit_code, started_at, ended_at, output_summary)`
- Produces: `ValidationReport(result, commands, scope_check, config_check, git_fingerprint, project_content_digests, created_at)`
- Produces: `compute_git_fingerprint(root: Path, scope: Sequence[str]) -> str`
- Produces: `validate_task(root: Path, task_id: str, dry_run: bool = False) -> ValidationReport`

- [ ] Write failing validation tests with real subprocesses.

Create temporary demo projects whose configured commands use `python3 -c "..."` as separate argv elements. Test command order, working directory, nonzero exits, missing executable, timeout, output truncation and redaction.

```python
def test_validation_failure_does_not_unlock_verify_gate(repo_at_verify: Path) -> None:
    report = validate_task(repo_at_verify, "DEMO-101")
    assert report.result == "failed"
    state = TaskRepository(repo_at_verify).load("DEMO-101")
    assert state.evidence["validation"].metadata["result"] == "failed"
    with pytest.raises(GateError, match="latest validation"):
        TaskService(repo_at_verify).advance("DEMO-101", Stage.confirm, approve_by="learner")
```

Also prove that code changes after a pass make evidence stale, a later failure supersedes an earlier pass, an out-of-scope project change fails scope check, and `--dry-run` lists commands without executing or writing. Add two named regressions: `test_validation_report_write_does_not_stale_its_own_fingerprint` validates immediately after the report/status write; `test_second_edit_to_already_dirty_tracked_file_stales_validation` changes the bytes of a file that was already reported modified and requires a different fingerprint.

Run `uv run pytest tests/integration/test_task_validation.py -q`; expect missing validator.

- [ ] Implement scope-aware Git fingerprinting.

The allowed change set for scope enforcement is:

- each approved `projects/<key>/` path;
- exact task directory;
- `docs/srs/<task-id>.md` and `docs/tdd/<task-id>.md`;
- `workspace-memory/feedback/<task-id>.md` when present.

Configuration, CLI source or an unapproved project change is out of scope for an ordinary product task. The exact task directory is allowed to change for orchestration bookkeeping, but it is **excluded** from the freshness fingerprint so writing validation/status/memory cannot invalidate its own evidence.

Compute the freshness fingerprint from superproject HEAD plus source-bearing allowed paths only: approved project submodule HEADs; SHA-256 of every modified or untracked file inside approved project worktrees; a deletion sentinel for each deleted file; and current bytes of the task SRS/TDD. Porcelain-v2 status supplies candidate paths, but path names/status alone are insufficient—hash the actual bytes of all tracked modifications too. Sort normalized relative paths and digests before the final hash. Recomputing after the validation report is written must yield the same value; changing an already-dirty tracked source file must yield a different value.

Also compute `project_content_digests` independently of Git HEAD: for every registered project, hash the sorted relative path, executable bit and bytes of all tracked plus non-ignored untracked files, excluding `.git`. This digest lets Task 13 prove that the content committed after validation is exactly the content that validation executed.

- [ ] Implement deterministic command execution and evidence.

Validation order is: `load_config`, scope check, then each selected project in dependency-first order and each configured argv in list order. Run with `shell=False`, captured text, a fixed 120-second timeout, and an environment containing only inherited non-secret values plus `PYTHONUNBUFFERED=1`. Redact and cap each combined output summary at 4 KiB while retaining exit code and timestamps.

Write `evidence/validation-<UTC timestamp>.json`, update the `validation` record to its digest/result/fingerprint, and return `5` when failed. A verification gate re-computes the current fingerprint and requires exact equality with the latest passed report.

- [ ] Verify pass, failure and staleness behavior.

```bash
uv run pytest tests/integration/test_task_validation.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

- [ ] Obtain independent validation-security review, then commit.

```bash
git add src/ybs_cli tests/integration/test_task_validation.py
git commit -m "feat: record fresh task validation evidence"
```

**Review focus:** `shell=False`, correct project cwd/order, scope policy, latest-record semantics, fingerprint freshness and redacted bounded output.

---

## Task 10 — Day 10: Six-tool Rule/Skill Projection and Drift Detection

**Concept:** one semantic source, tool-native generated projections, manifest ownership and safe conflict handling.

**Files:**

- Create: `src/ybs_cli/tool_sync.py`
- Create: `templates/tools/claude-entry.md`
- Create: `templates/tools/cursor-rule.mdc`
- Create: `templates/tools/agent.md`
- Create: `templates/tools/codex-agent.toml`
- Generate: `CLAUDE.md`
- Create: `.ybs-generated.json`
- Modify: `src/ybs_cli/cli.py`
- Modify: `.gitignore`
- Modify: `README.md`
- Test: `tests/contract/test_tool_sync.py`

**Interfaces:**

- Produces: `GeneratedFile(tool, source, target, sha256, content)`
- Produces: `SyncPlan(create, unchanged, drift, missing, unexpected)`
- Produces: `plan_tool_sync(root: Path) -> SyncPlan`
- Produces: `sync_tools(root: Path, check=False, dry_run=False, overwrite=False) -> SyncReport`

- [ ] Encode SC-01 as a contract test before writing the generator.

```python
EXPECTED_TARGETS = {
    "CLAUDE.md",
    ".claude/skills/task-workflow/SKILL.md",
    ".claude/agents/ybs-reviewer.md",
    ".codex/agents/ybs-reviewer.toml",
    ".cursor/rules/ybs-workflow.mdc",
    ".cursor/commands/run-ybs-task.md",
    ".cursor/agents/ybs-reviewer.md",
    ".trae/rules/ybs-workflow.md",
    ".trae/skills/task-workflow/SKILL.md",
    ".qoder/skills/task-workflow/SKILL.md",
    ".qoder/agents/ybs-reviewer.md",
    ".opencode/agents/ybs-reviewer.md",
}


def test_projection_uses_only_documented_targets(workspace: Path) -> None:
    report = sync_tools(workspace)
    assert {item.target for item in report.generated} == EXPECTED_TARGETS
    assert not (workspace / ".cursor/skills").exists()
    assert (workspace / ".agents/skills/task-workflow/SKILL.md").exists()
    assert not (workspace / ".claude/settings.local.json").exists()
```

Also test valid MDC frontmatter, TOML parsing, Markdown frontmatter, Claude's first line exactly `@AGENTS.md`, source marker presence, no generated entry for `AGENTS.md` or `.agents/`, second-run idempotence and `--dry-run` zero writes.

Run `uv run pytest tests/contract/test_tool_sync.py -q`; expect missing generator.

- [ ] Implement pure planning and atomic apply.

Every generated file contains a syntax-appropriate marker `generated by ybs tools sync; source=<path>; do not edit`, but native file syntax decides its location. `CLAUDE.md` keeps exact first line `@AGENTS.md` and places the marker on line 2; Markdown/MDC files with YAML frontmatter place the marker immediately after the closing `---`; TOML uses a leading comment before the first table. `.ybs-generated.json` contains version and sorted `{tool, source, target, sha256}` rows; it never claims source files.

Planning scans only known generated roots and manifest-owned files. A target that exists but is absent from the old manifest is `unexpected`; a manifest-owned content mismatch is `drift`; an absent manifest-owned target is `missing`. Normal sync refuses drift/unexpected with exit `3`. `--overwrite` replaces manifest-owned drift only; it never overwrites unexpected/unowned files.

- [ ] Add CLI modes and explicit surface notes.

`ybs tools sync --check` is read-only and returns `3` for missing/drift/unexpected. `--dry-run` prints the plan and returns `0` when the desired apply would be safe. `--overwrite` is mutually exclusive with `--check` and must be supplied explicitly. README notes that Trae IDE requires its import/skill switch and `.trae/agents` is intentionally not generated in v1 because it remains opt-in/beta.

- [ ] Run contract and drift scenarios.

```bash
uv run ybs tools sync --dry-run
uv run ybs tools sync
uv run ybs tools sync --check
uv run pytest tests/contract/test_tool_sync.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Then edit a generated copy in a temporary test clone, confirm `--check` reports drift without changing it, and confirm `--overwrite` restores only manifest-owned content.

- [ ] Obtain independent tool-format and overwrite-safety review, then commit.

```bash
git add .gitignore .ybs-generated.json CLAUDE.md README.md templates/tools src/ybs_cli .claude .codex .cursor .trae .qoder .opencode tests/contract/test_tool_sync.py
git commit -m "feat: distribute shared rules to six AI tools"
```

**Review focus:** official native paths, Cursor directly discovers the shared source skill while its agent uses the native path, valid per-tool syntax, ownership manifest, no permissions/secrets and unowned files never overwritten.

---

## Task 11 — Day 11: Mock Issue, Wiki, CI, and Notification Adapters

**Concept:** ports/adapters, stable contracts, idempotency keys and failure truthfulness.

**Files:**

- Create: `src/ybs_cli/adapters/__init__.py`
- Create: `src/ybs_cli/adapters/base.py`
- Create: `src/ybs_cli/adapters/issue_mock.py`
- Create: `src/ybs_cli/adapters/wiki_mock.py`
- Create: `src/ybs_cli/adapters/ci_mock.py`
- Create: `src/ybs_cli/adapters/notification_mock.py`
- Create: `src/ybs_cli/adapters/registry.py`
- Create: `mocks/fixtures/issues/DEMO-101.json`
- Create: `mocks/fixtures/wiki/workbench-status.json`
- Create: `mocks/fixtures/ci/default.json`
- Create: `mocks/fixtures/notifications/default.json`
- Modify: `src/ybs_cli/cli.py`
- Test: `tests/contract/test_adapters.py`
- Test: `tests/integration/test_adapter_health_cli.py`

**Interfaces:**

- Produces: recursive `JsonValue` type alias.
- Produces: `AdapterRequest(task_id, event, idempotency_key, payload)`
- Produces: `AdapterResult(status, external_id, payload, error)`
- Produces: `AdapterHealth(kind, status, detail)`
- Produces: `Adapter.health() -> AdapterHealth`
- Produces: `Adapter.execute(request: AdapterRequest) -> AdapterResult`
- Produces: `build_adapters(root: Path, config: WorkspaceConfig) -> dict[str, Adapter]`

- [ ] Write the common contract tests first.

```python
@pytest.mark.parametrize("kind", ["issue", "wiki", "ci", "notification"])
def test_adapter_is_idempotent(kind: str, adapter_factory) -> None:
    adapter = adapter_factory(kind)
    request = AdapterRequest(
        task_id="DEMO-101",
        event="completed",
        idempotency_key=f"DEMO-101:{kind}:completed",
        payload={"result": "passed"},
    )
    first = adapter.execute(request)
    second = adapter.execute(request)
    assert first == second
    records = list((adapter.runtime_dir).glob("*.json"))
    assert len(records) == 1


def test_same_key_with_different_payload_is_conflict(issue_adapter) -> None:
    first = AdapterRequest("DEMO-101", "completed", "same-key", {"value": 1})
    changed = AdapterRequest("DEMO-101", "completed", "same-key", {"value": 2})
    issue_adapter.execute(first)
    with pytest.raises(AdapterError, match="idempotency conflict"):
        issue_adapter.execute(changed)
```

Also require all four adapter results to serialize to the same fields, disabled/missing fixture health to fail, fixture-declared timeout/error to remain failed, and all persisted payloads/errors to pass through `redact`. Add a real file-adapter `fail_once` fixture: the first call persists one failed attempt, the second identical call re-executes and updates that same file to success with two attempts.

Run `uv run pytest tests/contract/test_adapters.py -q`; expect missing adapter package.

- [ ] Implement the common file-backed adapter base.

For each request, compute a canonical JSON payload digest with sorted keys. Runtime record path is `mocks/runtime/<kind>/<sha256(idempotency_key)>.json`, not a raw task-controlled filename. Under a lock, a matching existing **successful** record is terminal and returned unchanged; the same key with a different digest is always a conflict. A matching failed or pending record may be attempted again when the caller invokes the adapter. Append the attempt to the same canonical record and atomically update its final status, so retry never creates a second event file and can converge from failed to success. Task 12 owns the policy that decides whether the adapter is called again.

Adapter meanings are concrete:

- Issue: read task summary; on `completed`, save one comment and label `demo-complete`.
- Wiki: on `memory_published`, save the referenced guideline title and digest.
- CI: on `validation_reported`, save `passed`/`failed` and validation digest.
- Notification: on `task_completed`, save recipient `demo-user` and concise message.

No adapter performs network I/O in v1.

- [ ] Add `ybs adapter health [--json]`.

Health checks config, fixture directory readability, runtime parent writability and driver registration without creating runtime records. Any enabled unhealthy adapter makes the command exit `4`; JSON output is one redacted object.

- [ ] Verify contract, health, idempotency and failure fixtures.

```bash
uv run ybs adapter health --json
uv run pytest tests/contract/test_adapters.py tests/integration/test_adapter_health_cli.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

- [ ] Obtain independent adapter/security review, then commit.

```bash
git add mocks/fixtures src/ybs_cli/adapters src/ybs_cli/cli.py tests
git commit -m "feat: add local issue wiki CI and notification adapters"
```

**Review focus:** same-key/different-payload conflict, timeout/failure not converted to success, runtime isolation, no network and secrets redacted before persistence/output.

---

## Task 12 — Day 12: Recoverable External Sync and Commit-backed Archive

**Concept:** partial success, retry only failures, terminal-stage authority, commit evidence and crash-recoverable directory movement.

**Files:**

- Create: `src/ybs_cli/sync.py`
- Create: `src/ybs_cli/archive.py`
- Modify: `src/ybs_cli/git.py`
- Modify: `src/ybs_cli/task_repository.py`
- Modify: `src/ybs_cli/task_service.py`
- Modify: `src/ybs_cli/cli.py`
- Test: `tests/integration/test_task_sync.py`
- Test: `tests/integration/test_task_finish.py`

**Interfaces:**

- Produces: `sync_task(root: Path, task_id: str, retry_failed: bool = False, dry_run: bool = False) -> TaskState`
- Produces: `CommitEvidence(ref, resolved_sha, subject, changed_paths, verified_at)`
- Produces: `verify_commit(root: Path, ref: str, state: TaskState) -> CommitEvidence`
- Produces: `finish_task(root: Path, task_id: str, commit_ref: str, dry_run: bool = False) -> TaskState`
- Produces: `recover_archive(root: Path, task_id: str) -> TaskLocation`

- [ ] Write sync red tests as a complete first cycle.

```python
def test_partial_sync_is_saved_and_retry_only_calls_failed(repo_at_external_sync, adapters) -> None:
    adapters["ci"].fail_once("timeout")
    with pytest.raises(AdapterError):
        sync_task(repo_at_external_sync, "DEMO-101")

    partial = TaskRepository(repo_at_external_sync).load("DEMO-101")
    assert partial.stage == Stage.external_sync
    assert partial.external_sync["issue"].status == "success"
    assert partial.external_sync["ci"].status == "failed"

    completed = sync_task(repo_at_external_sync, "DEMO-101", retry_failed=True)
    assert completed.stage == Stage.commit
    assert adapters["issue"].call_count == 1
    assert adapters["ci"].call_count == 2
```

Also test: default rerun does not duplicate successes, `--retry-failed` with no failed entries is idempotent, disabled required adapter is a gate error, and ordinary `advance --to commit` remains rejected.

Run `uv run pytest tests/integration/test_task_sync.py -q`; expect missing sync service.

- [ ] Implement ordered, resumable sync.

Use fixed order `issue`, `wiki`, `ci`, `notification`. The idempotency key is exactly `<task-id>:<adapter-kind>:<event>`. After every adapter result, save task state atomically before continuing, so a crash loses at most the in-flight attempt. The stage changes to `commit` through `transition(... operation="sync")` only after every enabled required adapter has `success`.

- [ ] Write commit and archive red tests as a separate cycle.

Create a real temporary Git repository. Tests must reject unknown refs, refs not resolving to commits, a commit whose changed paths do not overlap approved scope/task docs, dirty approved project changes not contained in the commit, and a commit that predates task creation. A valid existing implementation commit advances and archives.

Inject failures at these exact points:

1. after writing `archive-intent.json` but before directory rename;
2. after directory rename but before saving final `stage=done` state;
3. after final status write before intent cleanup.

Re-running `finish` must converge to one directory under `workspace-memory/done/YYYY-MM/`, one `commit.json`, `stage=done`, and no in-progress duplicate.

- [ ] Implement commit verification and the archive recovery protocol.

`verify_commit` resolves via `git rev-parse <ref>^{commit}`, reads subject/time/changed paths without a shell, and requires the commit to include at least one approved project or task document path. It records an already existing implementation commit. It does not claim that the commit contains the later archive record; the user may commit archive evidence separately.

Archive protocol under the task lock:

1. write `evidence/commit.json` and verify its digest;
2. write root-local `.ybs/archive-intents/<task-id>.json` containing exact source, destination, state digest and commit digest;
3. `os.replace(source_dir, destination_dir)` on the same filesystem;
4. load state from destination, transition using `operation="finish"`, atomically write `status.yaml` and `memory.md` there;
5. remove only the exact intent file.

`recover_archive` inspects both exact locations plus intent digest. It resumes only a uniquely provable state; ambiguity exits `5` without deletion. Never recursively delete either directory.

- [ ] Verify sync and archive recovery.

```bash
uv run pytest tests/integration/test_task_sync.py -q
uv run pytest tests/integration/test_task_finish.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

- [ ] Obtain independent workflow/Git/crash-recovery review, then commit.

```bash
git add src/ybs_cli tests/integration/test_task_sync.py tests/integration/test_task_finish.py
git commit -m "feat: recover mock sync and archive verified commits"
```

**Review focus:** partial results survive, retry selection is exact, terminal transitions stay restricted, SHA self-reference is avoided and all three crash windows converge without deletion.

---

## Task 13 — Day 13: Implement and Replay DEMO-101 End to End

**Concept:** cross-project change from a reproducible teaching baseline, real HTTP behavior, deterministic frontend fallback and full orchestration proof.

**Files:**

In `projects/demo-api` submodule:

- Modify: `server.py`
- Modify: `tests/test_server.py`
- Modify: `AGENTS.md`

In `projects/demo-web` submodule:

- Modify: `src/status.js`
- Modify: `test/status.test.js`
- Modify: `index.html`
- Modify: `AGENTS.md`

In superproject:

- Create: `docs/srs/DEMO-101.md`
- Create: `docs/tdd/DEMO-101.md`
- Create: `scripts/demo_101.sh`
- Create: `src/ybs_cli/demo_verify.py`
- Create: `tests/e2e/test_demo_101.py`
- Modify binary artifacts: `fixtures/repos/demo-api.bundle`, `fixtures/repos/demo-web.bundle`
- Modify gitlinks: `projects/demo-api`, `projects/demo-web`
- Modify: `src/ybs_cli/cli.py`

**Interfaces:**

- Produces API: `GET /api/status` → HTTP `200`, `Content-Type: application/json`, exact JSON object `{"status":"ok","service":"demo-api"}`.
- Produces web: `renderStatus(payload: unknown) -> string`.
- Produces web: `loadStatus(fetchStatus: () => Promise<unknown>) -> Promise<string>`.
- Produces: `verify_demo(root: Path) -> DemoVerificationReport`.

- [ ] Create approved DEMO-101 SRS/TDD from the templates.

The SRS acceptance criteria are exactly the three approved behaviors in the design spec. The TDD states that the API uses `http.server.ThreadingHTTPServer`, binds to `127.0.0.1` on an injected port, and exposes a handler factory testable without a daemon. The browser model receives a fetch function; it does not couple tests to a browser DOM. Record learner approval and the actual document digests through the CLI, never by hand-editing `status.yaml`.

- [ ] Write failing backend behavior tests and run them inside the submodule.

```python
class StatusEndpointTest(unittest.TestCase):
    def test_status_endpoint_returns_exact_payload(self) -> None:
        with running_server() as base_url:
            with urllib.request.urlopen(f"{base_url}/api/status", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "application/json")
                self.assertEqual(json.load(response), {"status": "ok", "service": "demo-api"})

    def test_unknown_path_returns_404(self) -> None:
        with running_server() as base_url:
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(f"{base_url}/missing", timeout=2)
            self.assertEqual(error.exception.code, 404)
```

Run `python3 -m unittest discover -s tests`; expect the Day 4 skip to be replaced by a failing endpoint assertion before implementation.

- [ ] Implement the minimal standard-library API and commit the submodule.

The handler encodes the constant object with compact separators, writes `Content-Length`, suppresses default request logging in tests, returns JSON only for `/api/status`, and returns `404` otherwise. Expose `create_server(host="127.0.0.1", port=0) -> ThreadingHTTPServer` and a CLI main guarded by `if __name__ == "__main__"`.

```bash
python3 -m unittest discover -s tests
git add server.py tests/test_server.py AGENTS.md
git commit -m "feat: expose demo API service status"
git tag completed-demo-101-api
```

- [ ] Write failing frontend tests and run them inside the submodule.

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { loadStatus, renderStatus } from "../src/status.js";

test("renders exact API status", () => {
  assert.equal(renderStatus({ status: "ok", service: "demo-api" }), "API status: ok");
});

test("missing status degrades safely", () => {
  assert.equal(renderStatus({ service: "demo-api" }), "API status: unavailable");
});

test("network failure degrades safely", async () => {
  const text = await loadStatus(async () => { throw new Error("offline"); });
  assert.equal(text, "API status: unavailable");
});
```

Run `node --test test/status.test.js`; expect failed imports/assertions.

- [ ] Implement the minimal frontend model and commit the submodule.

```javascript
export function renderStatus(payload) {
  return payload && typeof payload.status === "string"
    ? `API status: ${payload.status}`
    : "API status: unavailable";
}

export async function loadStatus(fetchStatus) {
  try {
    return renderStatus(await fetchStatus());
  } catch {
    return "API status: unavailable";
  }
}
```

`index.html` imports this module, fetches `/api/status`, passes `response.json()` through `loadStatus`, and writes text with `textContent`.

```bash
node --test test/status.test.js
git add src/status.js test/status.test.js index.html AGENTS.md
git commit -m "feat: render demo API service status"
git tag completed-demo-101-web
```

- [ ] Refresh Bundles and prove every gitlink is recoverable.

From each submodule, create the matching Bundle with `--all` at a sibling `.next` path, verify it, then atomically replace the tracked Bundle and update superproject gitlinks. `demo-api.bundle` must advertise `teaching-baseline` and `completed-demo-101-api`; `demo-web.bundle` must advertise `teaching-baseline` and `completed-demo-101-web`. Each Bundle must contain the current matching gitlink commit. Validate both from a clean temporary clone. Never update a gitlink without the matching Bundle in the same superproject commit.

- [ ] Write the true cross-project E2E red test with one registered project checkout per project.

Use this single concrete sequence so the business files, validation inputs and committed files cannot diverge:

1. Create a temporary clone of the superproject and run offline bootstrap. Keep `workspace/projects.yaml` pointing to the real registered paths `projects/demo-api` and `projects/demo-web`; do not create alternate project worktrees.
2. In those exact two paths, checkout detached `teaching-baseline`. Run `ybs task start` now so its Git snapshot records the baseline gitlinks/worktrees.
3. Route, perform legal direct advances, approve `demo-web,demo-api` scope with `--tdd-required`, record approved SRS/TDD digests, and advance through `plan -> implement`.
4. In `projects/demo-api`, obtain bytes with `subprocess.run(["git", "diff", "--binary", "teaching-baseline", "completed-demo-101-api"], stdout=PIPE)` and apply them in that same directory with `subprocess.run(["git", "apply", "-"], input=diff.stdout)`. Repeat in `projects/demo-web` using `completed-demo-101-web`. No shell pipeline is used.
5. Advance `implement -> verify`, run the public `ybs task validate`, and assert every recorded command `cwd` resolves to one of those same two registered paths. Start the real API from the validated API path on an ephemeral port, read its real JSON with Python, pass that JSON on standard input to a Node process importing `renderStatus` from the validated web path, and assert all three business behaviors.
6. Complete final approval and memory evidence, advance to `external_sync`, then run `ybs task sync` so stage becomes `commit`.
7. Save each `project_content_digest` from the validation report, commit the applied files inside each submodule, and require a clean submodule worktree. Recompute the content digest and require exact equality with the saved validation digest; this proves each new commit tree contains the validated files even though its HEAD necessarily changed from `teaching-baseline`. Stage the two updated gitlinks in the temporary superproject and create one superproject implementation commit. Assert each gitlink SHA equals the corresponding **post-commit** submodule HEAD.
8. Pass that superproject SHA to `ybs task finish`. Assert the archived state, SRS/TDD, route explanation, validation report, tool manifest, four Mock records and commit evidence all refer to the same task and registered project paths.

- [ ] Implement `ybs demo verify` and a safe wrapper script.

`verify_demo` performs only checks in the current workspace and returns structured results. `scripts/demo_101.sh` creates a new temporary clone and runs the demonstration there; it never resets or commits the caller's working tree. It prints the temporary path on failure for inspection and cleans it on success.

- [ ] Run the full proof.

```bash
uv run pytest tests/e2e/test_demo_101.py -q
uv run ybs demo verify
./scripts/demo_101.sh
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Expected: exact API JSON, both frontend success/fallback texts and one archived `DEMO-101` task in the temporary clone.

- [ ] Obtain independent cross-project/E2E review, then commit the superproject.

```bash
git add docs/srs/DEMO-101.md docs/tdd/DEMO-101.md scripts/demo_101.sh src/ybs_cli tests/e2e fixtures/repos projects/demo-api projects/demo-web
git commit -m "feat: demonstrate DEMO-101 across bundled projects"
```

**Review focus:** tests cross the real HTTP/process boundary, exact business output, Bundle/gitlink atomicity, caller worktree safety and the E2E invokes public commands rather than internal shortcuts.

---

## Task 14 — Day 14: Full Doctor, CI, and Failure-regression Gates

**Concept:** diagnostics distinguish fatal prerequisites from repairable demo state; CI exercises failure behavior as well as the happy path.

**Files:**

- Create: `src/ybs_cli/doctor.py`
- Create: `.github/workflows/ci.yml`
- Create: `tests/integration/test_doctor.py`
- Create: `tests/integration/test_failure_recovery.py`
- Modify: `src/ybs_cli/cli.py`
- Modify: `README.md`

**Interfaces:**

- Produces: `DoctorCheck(name, status, detail, remediation)`
- Produces: `DoctorReport(ok: bool, checks: list[DoctorCheck])`
- Produces: `doctor(root: Path) -> DoctorReport`

- [ ] Write diagnostic red tests.

Test these exact outcomes:

| Condition | Status | Exit | Remediation |
|---|---:|---:|---|
| Python < 3.11, Git missing, Node missing | fatal | 5 | install named prerequisite |
| invalid config or invalid Bundle | fatal | 2 or 5 | name exact file/check |
| uninitialized but recoverable submodules | repairable | 0 | run `ybs demo bootstrap` |
| active lock | blocked | 3 | name owning PID/host |
| confirmed stale same-host lock | repairable | 0 | run exact retry command |
| all ready | ok | 0 | none |

The first official flow is `doctor` before `bootstrap`, so uninitialized submodules must not make a recoverable installation look broken.

- [ ] Implement side-effect-free doctor checks.

Use `sys.version_info`, `shutil.which`, config loading, `git --version`, `node --version`, `git bundle verify`, manifest/tool drift read checks and lock metadata inspection. Doctor never deletes a lock, bootstraps a project, generates a file or creates runtime directories.

- [ ] Add failure-injection regressions.

`tests/integration/test_failure_recovery.py` parameterizes exceptions at atomic replacement, task save, adapter result save and all three archive points. For each case assert parseable prior/new state, no duplicate task directories, legal retry behavior and no false stage advancement. Also cover secret text in each exception and JSON output.

- [ ] Add the CI workflow in the approved order.

```yaml
name: ci
on:
  push:
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: false
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run ybs config validate --json
      - run: uv run pytest tests/unit tests/contract tests/integration -q
      - run: uv run pytest tests/e2e/test_demo_101.py -q
```

Pin third-party action references to reviewed full commit SHAs before merging the implementation; keep the readable version comments next to them. The YAML above shows the required action/version intent, not permission to leave mutable tags in the final CI file.

- [ ] Run the local CI equivalent and inspect each failure message.

```bash
uv lock --check
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run ybs config validate --json
uv run pytest tests/unit tests/contract tests/integration -q
uv run pytest tests/e2e/test_demo_101.py -q
uv run ybs doctor
```

- [ ] Obtain independent CI/failure-recovery review, then commit.

```bash
git add .github/workflows/ci.yml README.md src/ybs_cli tests/integration
git commit -m "ci: gate configuration contracts recovery and demo smoke"
```

**Review focus:** doctor is read-only, bootstrap state is correctly classified, all failure injections preserve recovery, E2E is run once and action refs are immutable.

---

## Task 15 — Day 15: Verified Quickstart, Learning Guide, and Delivery Rehearsal

**Concept:** documentation is executable product surface; a new learner must reproduce the result without tribal knowledge.

**Files:**

- Rewrite: `README.md`
- Create: `docs/guidelines/learning-route.md`
- Create: `docs/guidelines/architecture-boundaries.md`
- Create: `docs/guidelines/troubleshooting.md`
- Create: `docs/guidelines/retrospective.md`
- Create: `tests/integration/test_readme_quickstart.py`

**Interfaces:**

- Produces: one copyable README quickstart for macOS/Linux.
- Produces: 15-day guide where every day has concept, bounded AI prompt, review checklist, verification command and retrospective question.
- Produces: troubleshooting decisions keyed by exit codes `2`–`5`.

- [ ] Write the executable quickstart test before finalizing README.

The test uses a clean temporary clone with no initialized submodules and runs the actual README command list:

```python
QUICKSTART = [
    ["uv", "sync", "--frozen"],
    ["uv", "run", "ybs", "doctor"],
    ["uv", "run", "ybs", "demo", "bootstrap"],
    ["uv", "run", "ybs", "tools", "sync", "--check"],
    ["uv", "run", "ybs", "demo", "verify"],
]
```

It asserts every command returns zero, no network access is required after uv dependencies are present, submodules match gitlinks, and a second bootstrap/sync/check remains unchanged. Initially this test must fail because the README/clean-clone sequence is incomplete, not because of missing local dependencies.

- [ ] Write the README around the proven command list.

README order is:

1. what the lab is and is not;
2. prerequisites with exact version checks;
3. five-command quickstart;
4. DEMO-101 ten-minute walkthrough;
5. six-tool support matrix including Trae/Cursor caveats;
6. directory map and source/generated ownership;
7. exit codes and recovery entry points;
8. link to the 15-day learning route;
9. upgrade path from Mock adapters to team systems.

Do not claim native Windows, production readiness, real enterprise integrations or unsupported tool features.

- [ ] Write the 15-day learning route.

For each task in this plan, provide a bounded prompt with this form:

```text
只实现 Day N 的文件和接口。先运行列出的红测并解释失败原因；
再写满足测试的最小实现。不要修改其他任务文件，不要自动提交。
完成后给出：改动摘要、风险、验证命令、仍未通过的累计测试。
```

Specialize the file/interface names per day. Add a human review checklist and one teach-back question. Map that question require explanation in the learner's own words, not a copied test result.

- [ ] Write architecture boundaries and troubleshooting.

Architecture boundaries explain protocol/config/runtime/documents/memory/adapters with one concrete input and output each. Troubleshooting starts from the exit code, then checks the exact JSON error, task stage, lock, config, Bundle/gitlink, adapter runtime or validation fingerprint. It never recommends global `protocol.file.allow`, force reset, recursive deletion or direct `status.yaml` editing.

- [ ] Rehearse in a genuinely clean clone and record evidence.

```bash
uv run pytest tests/integration/test_readme_quickstart.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run ybs config validate --json
./scripts/demo_101.sh
```

Also time a clean local rehearsal from `uv sync --frozen` through `ybs demo verify`; record date, OS, tool versions, duration and result in `docs/guidelines/retrospective.md`. The 10-minute target is a measured acceptance result, not a unit-test assertion about documentation text.

- [ ] Run a final independent product/spec verification.

The verifier checks every success criterion in the approved spec, all 15 task commits, a clean offline bootstrap, exact DEMO-101 behavior, all six tool projections, Mock records, error-path tests and the absence of secrets/absolute developer paths. Any failure returns to the owning task; do not waive it in the retrospective.

- [ ] Commit the teaching delivery.

```bash
git add README.md docs/guidelines tests/integration/test_readme_quickstart.py
git commit -m "docs: deliver fifteen day lab and verified quickstart"
```

**Review focus:** a new learner can copy the commands, all caveats are honest, learning prompts are bounded, recovery guidance is safe and the install-time claim has real evidence.

---

## Final Verification Matrix

Run this matrix only after all 15 task commits exist:

| Requirement | Evidence | Command |
|---|---|---|
| Locked install | committed `uv.lock` | `uv lock --check && uv sync --frozen` |
| Typed config and schema | JSON output + schema files | `uv run ybs config validate --json` |
| Offline submodules | Bundle contains gitlinks | `uv run ybs demo bootstrap && git submodule status` |
| Explainable routing | exact route result | `uv run ybs route "在演示工作台显示 API 服务状态" --json` |
| State/gate safety | unit + integration suite | `uv run pytest tests/unit tests/integration -q` |
| Six-tool projections | clean manifest check | `uv run ybs tools sync --check` |
| Mock contracts | contract suite + health | `uv run pytest tests/contract -q && uv run ybs adapter health --json` |
| Exact business behavior | real E2E | `uv run pytest tests/e2e/test_demo_101.py -q` |
| Style/static quality | Ruff | `uv run ruff check . && uv run ruff format --check .` |
| Clean learner journey | isolated rehearsal | `uv run pytest tests/integration/test_readme_quickstart.py -q` |

Final acceptance requires every row to pass in one clean clone. Save the command outputs in the final implementation task summary; do not commit environment-specific logs or absolute paths.

## Execution Handoff

Two supported execution modes:

1. **Subagent-driven development (recommended):** stay in this task, give one task at a time to an implementation agent, then use a separate reviewer/verifier before proceeding. Best for speed and independent quality checks.
2. **Plan execution in a separate task:** create an isolated worktree, execute batches of 2–3 tasks, and stop at the listed review checkpoints. Best when the learner wants to type, inspect and discuss each step personally.

In both modes, start with Task 1 only. Do not scaffold all 15 days at once: later tests are deliberately designed to constrain earlier interfaces and should remain visible learning checkpoints.
