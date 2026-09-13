# Day-01 复现规格

> 阶段名称：初始化独立仓库与可安装 CLI
> 规格目的：让一个没有当前聊天记录的 AI，从本文规定的初始状态重建 Day 1 的功能等价成果
> 当前参考实现根目录：`/Users/jichengye/Documents/WorkSpace/gitee/4-shizhan-xiangmu/z-tech-codex_ybs-workspace/ybs-workspace-lab`
> 下一阶段：Day-02；本规格禁止开始 Day-02
> 当前资产化文档提交授权：否；这里只禁止提交 `docs/specs/Day-01 复现规格.md` 与 `docs/learning/Day-01 掌握什么.md`，不包括第 11.3 节要求记录的已审批 design/plan

## 1. 复现目标

从一个尚未初始化 Git 的教学目录，建立独立的 Python 3.11+ 仓库和可安装 CLI，使以下能力同时成立：

1. `uv` 能根据 `pyproject.toml` 创建并冻结项目运行与开发依赖图；该锁不包含 `[build-system].requires` 的构建后端要求；
2. 项目安装后公开 `ybs` 命令；
3. `ybs --help` 展示固定项目说明和 `doctor` 子命令；
4. `ybs --version` 输出 `0.1.0`；
5. `ybs doctor` 输出当前 Python 版本以及从当前目录向上找到的 YBS 工作区根；
6. `find_workspace_root(start)` 返回最近的带标记祖先，找不到时抛出退出码为 `5` 的预期操作错误；
7. 未知子命令由 Typer/Click 作为用法错误处理，以 `2` 退出且不显示 Python Traceback；
8. `bin/ybs` 是可执行的薄 POSIX Shell 启动器，只定位项目环境和转发参数；
9. 两项真实子进程集成测试、Ruff 检查、锁检查和手工 CLI 验收全部通过；
10. Git 历史按本文规定形成两个边界清楚的本地提交。

“复现成功”指功能、公开接口、输出语义、退出码、测试与验收结果等价；不要求生产代码逐字节一致，也不要求 Git SHA、提交时间、依赖包上传时间或不同日期重新解析出的锁文件逐字节相同。

## 2. 初始状态

### 2.1 复现目录

执行者会收到一个专用于本任务的目录。当前参考路径是：

```text
/Users/jichengye/Documents/WorkSpace/gitee/4-shizhan-xiangmu/z-tech-codex_ybs-workspace/ybs-workspace-lab
```

在其他机器复现时，以“包含本文的目录”为项目根。进入该目录后，必须在当前 Shell 中执行以下初始化，并在整个复现流程中保持这三个导出变量：

```sh
export PROJECT_ROOT="$(pwd -P)"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
```

- `PROJECT_ROOT` 是后文所有相对路径和验收比较的基准；
- uv 的包缓存必须写入 `UV_CACHE_DIR`；
- uv 自动下载的 Python 必须写入 `UV_PYTHON_INSTALL_DIR`；
- 所有 `uv` 命令、pytest 启动的子进程以及 `bin/ybs` 验收都必须继承这三个变量；测试中的 `subprocess.run(...)` 默认继承父进程环境，不得清空或替换环境；
- 切换 Shell、打开新终端或使用独立执行会话后，必须重新进入复现目录并重复上述三行；不得假定变量跨 Shell 保留；
- `.demo/` 已由本阶段 `.gitignore` 忽略，缓存和 uv 管理的 Python 不得提交。

### 2.2 必须已存在的只读输入

开始时有三份必需输入资产；此外只允许有一份可选学习笔记：

```text
docs/
├── specs/
│   └── Day-01 复现规格.md
└── superpowers/
    ├── plans/
    │   └── 2026-09-13-ybs-workspace-learning-demo.md
    └── specs/
        └── 2026-09-13-ybs-workspace-learning-demo-design.md
```

- 本规格是三份必需输入之一，是执行说明，复现期间不得改写或提交。
- `docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md` 和 `docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md` 是另外两份必需输入。它们必须由任务提供方从已审批资产中原样预置；执行者不得凭空重写这两篇长文。复现期间只读取，最后按第 11.3 节把它们作为第二个提交记录。
- 已审批计划的 SHA-256 必须为 `ea302b81fff4d5a5edaec4bf3c33dc341d4f3838c368b18d60468644a1b966d5`。
- 已审批设计的 SHA-256 必须为 `f8f60db0599604697bd1d4b52dc895843f65023cdf360ff33f7e145f7168b799`。
- `docs/learning/Day-01 掌握什么.md` 可以作为额外的未跟踪学习资产存在，但不是实现输入，不得读取它来补齐本文缺失信息，也不得加入 Day 1 的两个提交。
- 如果三份必需输入任一缺失或两份已审批 design/plan 的 SHA-256 不匹配，必须停止并报告“输入资产缺失或校验失败”；不能从参考仓库复制替代，也不能伪造。

### 2.3 必须不存在的内容

开始时必须满足：

- 项目根没有 `.git/`，尚未执行 `git init`；
- 没有 `.venv/`；
- 没有 `.gitignore`、`.python-version`、`pyproject.toml`、`uv.lock`、`bin/ybs`；
- 没有 `src/ybs_cli/` 和 `tests/integration/test_cli_entrypoint.py`；
- 没有 Day-02 或更晚阶段的实现文件；
- 除三份必需输入和可选学习笔记外，没有其他文件、符号链接或目录。

若发现额外文件或 Git 仓库，不得删除、覆盖或重置；先列出差异并让任务提供方恢复规定的初始状态。

### 2.4 Git 初态

- 仓库不存在，因此也不存在分支、提交或远端；
- 复现时必须初始化为独立仓库，初始分支名为 `main`；
- 不添加远端，不推送，不改写历史；
- 两份审批文档在初始化后会暂时显示为未跟踪，这是预期状态；
- 本规格以及可选学习笔记在整个复现中保持未跟踪，不能混入 Day 1 提交。

### 2.5 外部目录边界

项目根的同级或上级可能存在参考项目 `ybs-workspace/`。它只允许用于人工对照，严禁：

- 修改参考项目；
- 从中复制业务实现、Git 元数据、虚拟环境或锁文件；
- 在其中运行会写文件的命令；
- 把它初始化为本项目的远端或子模块。

本任务的所有持久化项目状态、uv 缓存和 uv 管理的 Python 都必须位于收到的复现目录内。第 2.1 节的环境变量用于避免 uv 默认写入用户缓存；负向验收可以在操作系统临时目录创建一次性文件/空目录，但必须记录精确路径并在断言后删除。对用户目录、系统 Python、全局 Git 配置和其他仓库不得做写操作。

### 2.6 前置阶段接口

Day 1 是首个实现阶段，没有可调用的前置阶段接口。两份已审批文档是设计输入，不是运行时依赖。

## 3. 范围与非范围

### 3.1 必须实现

- 独立 Git 仓库和 `main` 分支；
- Python 3.11 项目声明、Hatchling 构建配置、运行/开发依赖；
- `uv.lock` 与本地 `.venv`；
- `ybs_cli` 包、模块入口和 console script；
- Typer 根应用、帮助、版本、最小 `doctor`；
- `YbsError` 及 CLI 层错误映射；
- 基于 `pyproject.toml` 文本标记的向上根目录搜索；
- 可执行薄 Shell 启动器；
- 两项真实子进程集成测试；
- Ruff、pytest 和锁文件检查配置；
- 两个本地 Git 提交及固定提交边界。

### 3.2 明确不实现

以下全部属于 Day-02 或更晚阶段，本任务不得提前创建：

- 安全路径、原子写、任务锁、脱敏；
- Pydantic 配置模型、YAML 加载和 JSON Schema；
- 项目注册、依赖图、Git Submodule 或 Git Bundle；
- 路由引擎、任务状态机、任务记忆；
- SRS/TDD 模板生成；
- AI 工具规则分发；
- Issue、Wiki、CI、通知适配器；
- `DEMO-101` 或任何业务示例；
- 完整 `doctor` 健康检查；Day 1 的 `doctor` 只输出 Python 版本和根路径；
- 原生 Windows 支持。

### 3.3 禁止的优化与扩展

- 不把根目录标记改成完整 TOML 解析；
- 不新增日志框架、配置框架、插件系统或网络服务；
- 不在 `bin/ybs` 中加入业务判断；
- 不新增自动提交、推送、重置、清理或删除能力；
- 不扩大测试数量来顺带实现后续阶段；
- 不修改两份已审批 design/plan 的空白、格式或内容。

## 4. 环境与依赖

### 4.1 支持环境

- 操作系统：macOS 或 Linux；
- Shell：支持 POSIX `sh`；
- Python：`>=3.11`，Day 1 固定 `.python-version` 为 `3.11`；
- 包管理器：`uv`；
- 版本控制：Git，必须支持 `git init -b main`；
- 审批输入校验工具：`shasum`，用于执行本文固定的 SHA-256 检查；macOS 通常自带，Linux 环境若缺失必须在复现前安装，并由第 4.5 节的 `command -v shasum` 立即失败，不能静默改用未写入规格的替代算法或跳过校验；
- 文件系统：必须支持可执行权限位。

原生 Windows、PowerShell 专用入口和不支持 POSIX 执行位的文件系统不在本阶段承诺范围内。

### 4.2 直接依赖

运行依赖必须是：

| 包 | 版本范围 | Day 1 是否直接使用 |
|---|---|---:|
| `pydantic` | `>=2.11,<3` | 否，作为后续阶段已批准基础依赖 |
| `PyYAML` | `>=6.0,<7` | 否，作为后续阶段已批准基础依赖 |
| `typer` | `>=0.16,<1` | 是 |

开发依赖必须是：

| 包 | 版本范围 | 用途 |
|---|---|---|
| `pytest` | `>=8.4,<10` | 测试 |
| `ruff` | `>=0.12,<1` | 静态检查和格式检查 |

构建后端为 `hatchling.build`，构建要求写作 `requires = ["hatchling"]`。

`uv.lock` 锁定的是项目运行与开发依赖图；当前锁文件不包含 Hatchling。Hatchling 由 `[build-system].requires` 单独声明，并由构建前端在隔离构建环境需要时取得。

### 4.3 锁文件要求

1. 先精确创建本文规定的 `pyproject.toml`；
2. 执行一次 `uv sync`，由 `uv` 解析并生成 `uv.lock`；
3. 锁文件必须提交，`uv lock --check` 必须返回 `0`；
4. 后续验收使用 `uv sync --frozen`，不得在验收阶段静默更新锁；
5. 参考实现的锁格式为 version `1`、revision `3`、`requires-python = ">=3.11"`，2026-09-13 复验时共解析 20 个包；
6. 因依赖声明使用版本范围，不同日期从索引重新生成锁可能选择新的合法版本。只要满足约束、完整记录来源/哈希、冻结同步和全部行为验收通过，即属于功能等价；不得手工编造或删改锁记录来追求字节相同。

### 4.4 网络规则

- 若项目内缓存没有所需 Python 或包，首次 `uv python pin`/`uv sync` 只允许访问 uv 使用的官方 Python 分发来源以及 PyPI 包索引/文件来源；不得借此授权访问其他业务系统；
- 自动下载的 Python 必须落入 `$UV_PYTHON_INSTALL_DIR`，包缓存必须落入 `$UV_CACHE_DIR`；不得使用 uv 默认的用户级缓存或 Python 安装目录；
- 不允许访问或克隆业务参考仓库；
- 锁和环境成功建立后，本阶段运行行为不依赖外部业务服务；
- 若网络不可用且缓存不完整，应清楚报告缺失项，不得改用未锁定的全局包凑合通过。

### 4.5 环境预检

进入复现目录后，在**同一个 Shell** 中执行。先固定项目根和 uv 的项目内写入位置：

```sh
export PROJECT_ROOT="$(pwd -P)"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
test -n "$PROJECT_ROOT"
test "$UV_CACHE_DIR" = "$PROJECT_ROOT/.demo/uv-cache"
test "$UV_PYTHON_INSTALL_DIR" = "$PROJECT_ROOT/.demo/uv-python"
command -v git
command -v uv
command -v shasum
test ! -e .git
test ! -e .venv
test ! -e .gitignore
test ! -e .python-version
test ! -e pyproject.toml
test ! -e uv.lock
test ! -e bin
test ! -e src
test ! -e tests
test ! -e .demo
test ! -e mocks
test ! -e workspace
test ! -e workspace-memory
test ! -e projects
test ! -e .agents
test ! -e .github
test ! -e src/ybs_cli/__init__.py
test ! -e src/ybs_cli/__main__.py
test ! -e src/ybs_cli/cli.py
test ! -e src/ybs_cli/errors.py
test ! -e src/ybs_cli/root.py
test ! -e tests/integration/test_cli_entrypoint.py
test ! -e src/ybs_cli/filesystem.py
test ! -e src/ybs_cli/redaction.py
test ! -e tests/unit/test_filesystem.py
test ! -e tests/unit/test_redaction.py
test -f 'docs/specs/Day-01 复现规格.md'
test -f docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
test -f docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
test "$(shasum -a 256 docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md | awk '{print $1}')" = "ea302b81fff4d5a5edaec4bf3c33dc341d4f3838c368b18d60468644a1b966d5"
test "$(shasum -a 256 docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md | awk '{print $1}')" = "f8f60db0599604697bd1d4b52dc895843f65023cdf360ff33f7e145f7168b799"
```

然后取得包括目录、普通文件和符号链接在内的完整初始清单：

```sh
actual_initial="$(export LC_ALL=C; find . -mindepth 1 -print | sort)"
printf '%s\n' "$actual_initial"
```

不含可选学习笔记时，输出必须精确为：

```text
./docs
./docs/specs
./docs/specs/Day-01 复现规格.md
./docs/superpowers
./docs/superpowers/plans
./docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
./docs/superpowers/specs
./docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
```

含可选学习笔记时，输出必须精确为：

```text
./docs
./docs/learning
./docs/learning/Day-01 掌握什么.md
./docs/specs
./docs/specs/Day-01 复现规格.md
./docs/superpowers
./docs/superpowers/plans
./docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
./docs/superpowers/specs
./docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
```

执行者必须把实际输出与上面两个允许值之一逐行比较；任何额外文件、目录或符号链接都必须停止并报告。清单与哈希通过后再运行 `git --version` 和 `uv --version` 记录工具版本。任一 `test` 或哈希检查失败也必须停止。不得用删除现有 `.git`、额外文件或覆盖输入的方式“修复”初始状态。

## 5. 最终目录与文件清单

复现完成后的相关目录应为：

```text
.
├── .demo/                                     # uv 生成；不提交；运行时产物
│   ├── uv-cache/                              # `$UV_CACHE_DIR`
│   └── uv-python/                             # `$UV_PYTHON_INSTALL_DIR`，需要下载 Python 时出现
├── .git/                                      # Git 生成；运行时元数据
├── .gitignore                                 # 创建；提交；事实源；0644
├── .python-version                            # 生成/创建；提交；事实源；0644
├── .venv/                                     # uv 生成；不提交；运行时产物
├── bin/
│   └── ybs                                    # 创建；提交；事实源；0755
├── docs/
│   ├── learning/
│   │   └── Day-01 掌握什么.md                  # 可选预置资产；不属于复现提交
│   ├── specs/
│   │   └── Day-01 复现规格.md                  # 预置执行输入；不属于复现提交
│   └── superpowers/
│       ├── plans/
│       │   └── 2026-09-13-ybs-workspace-learning-demo.md       # 预置；第二次提交；事实源
│       └── specs/
│           └── 2026-09-13-ybs-workspace-learning-demo-design.md # 预置；第二次提交；事实源
├── pyproject.toml                             # 创建；提交；事实源；0644
├── src/
│   └── ybs_cli/
│       ├── __init__.py                        # 创建；提交；事实源；0644
│       ├── __main__.py                        # 创建；提交；事实源；0644
│       ├── cli.py                             # 创建；提交；事实源；0644
│       ├── errors.py                          # 创建；提交；事实源；0644
│       └── root.py                            # 创建；提交；事实源；0644
├── tests/
│   └── integration/
│       └── test_cli_entrypoint.py             # 创建；提交；事实源；0644
└── uv.lock                                    # uv 生成；提交；派生但受版本控制；0644
```

以下可能出现但必须被忽略且不得提交：`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`__pycache__/`、`*.egg-info/`、`build/`、`dist/`、`.demo/`、`mocks/runtime/`。

## 6. 文件级规格

短小文件给出精确内容。UTF-8 文本统一使用 LF 换行，文件末尾保留一个换行。

### 6.1 `.gitignore`

精确内容：

```gitignore
.venv/
.demo/
mocks/runtime/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
build/
dist/
*.egg-info/
```

职责：只排除本地环境、运行时数据、缓存和构建产物；不能忽略源文件、测试、审批文档或 `uv.lock`。

### 6.2 `.python-version`

精确内容：

```text
3.11
```

使用 `uv python pin 3.11` 生成或验证。它选择 Python 3.11 系列，不要求补丁版本固定为 3.11.14；3.11.14 是参考环境实测值。

### 6.3 `pyproject.toml`

精确内容：

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

[tool.ybs]
workspace = true
```

关键约束：

- 包名是 `ybs-workspace-lab`，导入包名是 `ybs_cli`，二者不要混淆；
- console script 的目标必须为 Typer `app`，不是 `main`；
- `[tool.ybs]` 的两段文本是 Day 1 根定位算法的标记；
- `pydantic` 与 `PyYAML` 本阶段暂未导入，但不能删除。

### 6.4 `uv.lock`

`uv.lock` 不手写。它必须由当前 `uv` 根据第 6.3 节的清单执行 `uv sync` 生成，且满足：

- 顶层 Python 约束与 `>=3.11` 一致；
- 包含本项目 `ybs-workspace-lab` 0.1.0；
- 包含全部运行与开发依赖及其传递依赖；
- `uv lock --check` 返回 `0`；
- `uv sync --frozen` 返回 `0` 且不修改该文件；
- 文件加入第一次提交。

### 6.5 `bin/ybs`

精确内容：

```sh
#!/bin/sh
set -eu
REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec uv run --project "$REPO_ROOT" ybs "$@"
```

权限必须为可执行，目标模式为 `0755`。职责边界：

- 根据脚本自身位置计算仓库根；
- 使用 `--project` 选择该仓库的 uv 环境；
- 调用的是普通 `uv run`：它可能协调项目锁与环境；冻结保证来自调用前已通过的 `uv sync --frozen` 和未变化的清单/锁，不是该脚本传入了 `--frozen`；
- 继承调用方的 `UV_CACHE_DIR` 与 `UV_PYTHON_INSTALL_DIR`；验收前必须按第 2.1 节设置，脚本本身不擅自覆盖环境政策；
- 以 `exec` 替换当前进程，原样传递退出码和信号；
- 用 `"$@"` 保留参数边界；
- 不 `cd`，不解析业务参数，不实现 `doctor`，不读配置。

### 6.6 `src/ybs_cli/__init__.py`

精确行为和推荐内容：

```python
"""YBS workspace command-line tools."""

__version__ = "0.1.0"
```

`__version__` 是 CLI 版本显示来源，必须与 `pyproject.toml` 的项目版本一致。

### 6.7 `src/ybs_cli/__main__.py`

精确行为和推荐内容：

```python
from ybs_cli.cli import main

if __name__ == "__main__":
    main()
```

它保证 `python -m ybs_cli` 进入与 console script 相同的 Typer 应用。导入模块时不能自动执行 CLI。

### 6.8 `src/ybs_cli/errors.py`

公共接口：

```python
class YbsError(Exception):
    """An expected operational failure with a stable process exit code."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
```

合同：

- 是 `Exception` 子类；
- 构造参数固定为 `message: str, code: int`；当前构造器只保存参数，不校验消息是否非空，也不校验 code 是否属于枚举；
- `str(error)` 与 `message` 一致；
- `.message` 和 `.code` 可由 CLI 错误边界读取；
- Day 1 不额外限制 code 枚举，但当前根定位只用 `5`。

### 6.9 `src/ybs_cli/root.py`

公共接口：

```python
def find_workspace_root(start: Path) -> Path:
    """Return the nearest ancestor marked as a YBS workspace."""
```

算法合同：

1. `current = start.resolve()`；
2. 在每个 `current` 下检查 `pyproject.toml` 是否为普通文件；
3. 若是，读取全文；
4. 文本同时包含字面量 `[tool.ybs]` 与 `workspace = true` 时，立即返回该 `current`；
5. 否则进入 `current.parent`；
6. 到达文件系统根且仍未命中时，抛出 `YbsError("YBS workspace root not found", 5)`。

推荐的功能等价实现：

```python
from pathlib import Path

from ybs_cli.errors import YbsError


def find_workspace_root(start: Path) -> Path:
    """Return the nearest ancestor marked as a YBS workspace."""
    current = start.resolve()
    while True:
        manifest = current / "pyproject.toml"
        if manifest.is_file():
            text = manifest.read_text()
            if "[tool.ybs]" in text and "workspace = true" in text:
                return current
        if current.parent == current:
            raise YbsError("YBS workspace root not found", 5)
        current = current.parent
```

边界说明：这是 Day 1 的最小文本标记实现，不解析 TOML 语义；“最近祖先优先”必须保留。

### 6.10 `src/ybs_cli/cli.py`

必须公开：

- `app: typer.Typer`
- `main() -> None`
- 子命令 `doctor() -> None`

推荐的功能等价实现：

```python
import platform
from pathlib import Path
from typing import Annotated

import typer

from ybs_cli import __version__
from ybs_cli.errors import YbsError
from ybs_cli.root import find_workspace_root

app = typer.Typer(help="Repository-first AI development orchestration")


def _show_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_show_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Repository-first AI development orchestration."""


def _exit_for_error(error: YbsError) -> None:
    typer.echo(error.message, err=True)
    raise typer.Exit(code=error.code)


@app.command()
def doctor() -> None:
    """Report the active Python version and workspace root."""
    try:
        root = find_workspace_root(Path.cwd())
    except YbsError as error:
        _exit_for_error(error)
    typer.echo(f"Python: {platform.python_version()}")
    typer.echo(f"Root: {root}")


def main() -> None:
    app()
```

行为约束：

- `--version` 是 eager 根选项，不要求子命令；
- 版本输出写 stdout，然后 code `0` 退出；
- `doctor` 从 `Path.cwd()` 搜索，不能偷偷改用 Shell 算出的 `REPO_ROOT`；
- 只有 `YbsError` 在此被转换为稳定操作错误；
- 错误消息写 stderr，不显示预期操作错误的 Traceback；
- 未知命令由 Typer/Click 自身处理，退出 `2`。

### 6.11 `tests/integration/test_cli_entrypoint.py`

最终测试必须验证真实子进程，不能用 Mock 替代 `uv`、console script、Python 解释器或文件系统遍历。固定内容如下：

```python
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


def run_ybs(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "ybs", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_and_version_are_available() -> None:
    help_result = run_ybs("--help")
    version_result = run_ybs("--version")

    assert help_result.returncode == 0
    assert "Repository-first AI development orchestration" in help_result.stdout
    assert version_result.returncode == 0
    assert "0.1.0" in version_result.stdout


def test_find_workspace_root_from_nested_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "docs" / "notes"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[tool.ybs]\nworkspace = true\n")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; from ybs_cli.root import find_workspace_root; "
            "print(find_workspace_root(Path.cwd()))",
        ],
        cwd=nested,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(root)
```

## 7. 接口与行为契约

### 7.1 CLI 总表

| 调用 | 输入 | stdout | stderr | 退出码 | 文件写入 |
|---|---|---|---|---:|---:|
| `uv run ybs --version` | 无子命令 | 精确一行 `0.1.0` | 正常为空 | `0` | 无业务写入；uv 可能维护环境 |
| `uv run ybs --help` | 无 | 必须含固定说明和 `doctor` | 正常为空 | `0` | 无业务写入 |
| `uv run ybs doctor`，当前目录在工作区内 | `Path.cwd()` | 第一行 `Python: <运行时版本>`；第二行 `Root: <解析后的绝对根>` | 正常为空 | `0` | 无业务写入 |
| `uv run ybs doctor`，当前目录及祖先无标记 | `Path.cwd()` | 空 | 含 `YBS workspace root not found`，不得含 Python Traceback | `5` | 无业务写入 |
| `uv run ybs unknown-command` | 非法命令名 | Typer 版本可能把 usage 写到 stdout 或 stderr | 必须含未知命令说明，整体不得含 Traceback | `2` | 无业务写入 |
| `uv run python -m ybs_cli --version` | 模块调用 | 精确一行 `0.1.0` | 正常为空 | `0` | 无业务写入 |

Rich/Typer 的边框、颜色、空白和 completion 选项会随兼容版本变化，不是字节级合同；固定说明、命令名、版本值、错误语义和退出码是合同。

### 7.2 Python 公共接口

#### `YbsError(message: str, code: int)`

- 输入：字符串消息和整数退出码；调用方应传入人类可读消息与稳定代码，但 Day 1 构造器本身不执行非空或枚举校验；
- 输出：异常对象；
- 可观察字段：`.message`、`.code`；
- 幂等性：纯构造，无文件副作用。

#### `find_workspace_root(start: Path) -> Path`

- 输入：文件系统路径；本阶段按目录使用；
- 输出：`resolve()` 后的最近匹配祖先绝对路径；
- 失败：无匹配时抛固定消息、code `5` 的 `YbsError`；
- 幂等性：在文件系统不变化时重复调用结果一致；
- 安全：只读目录和清单，不写、不删除、不跨目录修改；
- 路径规则：符号链接通过 `resolve()` 归一化后再向上查找。

#### `app: typer.Typer` 与 `main() -> None`

- `app` 是可由安装入口和测试调用的命令对象；
- `main()` 不返回业务数据，只启动 `app()`；
- 参数解析错误不得映射为 `0`；
- 预期 `YbsError` 必须由命令层输出消息并使用其 code。

### 7.3 退出码合同

Day 1 可直接观察的退出码：

- `0`：命令成功；
- `2`：Typer/Click 参数或命令用法错误；
- `5`：工作区根未找到等文件/执行类操作错误。

全项目已批准但 Day 1 尚未实现的 `3`（工作流门禁）和 `4`（适配器）只保留给后续阶段，不得在本阶段伪造命令来演示。

## 8. 实施顺序：TDD RED 到 GREEN

必须按顺序执行。功能测试出现预期 RED 前，不得先创建 `src/ybs_cli/` 的实现。

### 步骤 0：验证输入与建立独立仓库

1. **文件变化：** 不改输入文档；创建 `.git/`。
2. **先验检查：** 在同一 Shell 中设置第 2.1 节三个环境变量，再运行第 4.5 节全部 `test`、SHA-256 和精确 `find` 清单检查，确认三份必需输入有效、可选学习笔记之外没有额外内容，所有 Day 1/Day 2 实现路径与 `.git` 均不存在。
3. **失败信号：** 任一 `test` 非零即说明初始状态不符合规格。
4. **预期原因：** 只能是工具缺失、输入缺失或目录已有状态，不属于产品 RED。
5. **最小动作：** 执行 `git init -b main`。
6. **验证命令：** `git branch --show-current`。
7. **预期结果：** stdout 精确为 `main`，无提交、无远端；`PROJECT_ROOT`、`UV_CACHE_DIR`、`UV_PYTHON_INSTALL_DIR` 仍在当前 Shell 中有效。
8. **提交点：** 否。

### 步骤 1：建立项目清单、锁环境和忽略规则

1. **文件变化：** 创建 `.gitignore`、`.python-version`、`pyproject.toml`；由 `uv` 生成 `.venv/` 与 `uv.lock`。
2. **先验检查：** 创建后运行 `uv lock --check`。
3. **失败信号：** 在生成锁之前，该命令应因锁缺失而非零；这是环境尚未建立的检查，不是功能 RED。
4. **预期原因：** `uv.lock` 尚不存在。
5. **最小动作：** 在三个环境变量仍已导出的同一 Shell 中执行 `uv python pin 3.11`，写入精确清单，执行 `uv sync`。任何自动下载的 Python 和包缓存都必须分别落入项目内 `.demo/uv-python` 和 `.demo/uv-cache`。
6. **验证命令：** `uv lock --check` 与 `uv sync --frozen`。
7. **预期结果：** 两条命令 exit `0`，后者不改锁；`.venv/` 被忽略。
8. **提交点：** 否；必须等功能 GREEN 和完整验收。

### 步骤 2：先写最终集成测试并取得真实 RED

1. **文件变化：** 只创建 `tests/integration/test_cli_entrypoint.py`，内容见第 6.11 节；仍不创建 `src/ybs_cli/`。
2. **先写测试：** 两项测试分别覆盖安装后帮助/版本和临时嵌套目录根定位。
3. **RED 命令：** 保持第 2.1 节环境变量后运行 `uv run pytest tests/integration/test_cli_entrypoint.py -q`；pytest 及其两个子进程必须继承这些变量。
4. **预期 RED：** 两项测试均失败；参考实现原始证据为子进程 exit `1`，stderr 含 `ModuleNotFoundError: No module named 'ybs_cli'`，汇总 `2 failed`。只接受“包/入口功能缺失”引起的失败；pytest 未安装、测试语法错误或测试无法收集不算有效 RED。
5. **最小实现：** 此步骤不写实现，只保存 RED 的命令、退出码和首个关键错误。
6. **GREEN 命令：** 尚不运行；进入步骤 3 后使用同一命令。
7. **预期 GREEN：** 延后到步骤 3，必须为 `2 passed`。
8. **提交点：** 否。

### 步骤 3：实现最小 CLI 并取得 GREEN

1. **文件变化：** 创建 `src/ybs_cli/__init__.py`、`__main__.py`、`cli.py`、`errors.py`、`root.py` 和 `bin/ybs`；保证 `pyproject.toml` 已含工作区标记。
2. **测试依据：** 不改步骤 2 的测试来迎合实现。
3. **RED 基线：** 使用步骤 2 保存的 `2 failed` 证据。
4. **失败原因：** `ybs_cli` 包和 CLI 入口不存在。
5. **最小实现：** 严格按第 6 节实现，不加入 Day-02 功能；执行 `chmod +x bin/ybs`。
6. **GREEN 命令：** 保持三个环境变量后运行 `uv run pytest tests/integration/test_cli_entrypoint.py -q`。
7. **预期结果：** exit `0`，汇总 `2 passed`；`test -x bin/ybs` 为 `0`；随后 `uv run ruff check src tests` 和 `uv run ruff format --check src tests` 均 exit `0`。所有 uv 和测试子进程继续继承项目内缓存/解释器目录。
8. **提交点：** 暂不提交，先做步骤 4 的完整验收和独立审阅。

### 步骤 4：验证负向合同并形成实现提交

1. **文件变化：** 不新增功能文件；只允许格式工具在审阅后修正第 6 节列出的 Python 文件。
2. **测试依据：** 继续运行 Day 1 两项集成测试，并执行版本、帮助、`doctor` 和未知命令验收。
3. **失败信号：** 任一正向命令非零、未知命令不是 `2`、输出含 Traceback、Root 不等于 `pwd -P`、`bin/ybs` 不可执行。
4. **预期原因：** 打包、参数转发、Typer 分发、错误边界或根标记没有满足合同；不能通过放宽断言解决。
5. **最小修正：** 只改第 6 节对应实现；每次修正后重跑全部验收。
6. **GREEN 命令：** 第 10 节完整命令组。
7. **预期结果：** 所有正向检查 `0`；未知命令捕获到 `2` 且无 Traceback；独立审阅 packaging、root detection、error mapping 和薄 Shell 无阻塞意见。
8. **提交点：** 有。严格暂存第 11.2 节第一次提交列出的 11 个文件；暂存后运行 `git diff --cached --summary -- bin/ybs | grep -F 'create mode 100755 bin/ybs'` 确认索引中的执行位，再提交。

### 步骤 5：记录已审批设计与计划

1. **文件变化：** 不修改两份预置文档内容，只改变其 Git 跟踪状态。
2. **先验检查：** 对两份文件分别运行 `test -s`，再用 `shasum -a 256` 重算。计划必须等于 `ea302b81fff4d5a5edaec4bf3c33dc341d4f3838c368b18d60468644a1b966d5`，设计必须等于 `f8f60db0599604697bd1d4b52dc895843f65023cdf360ff33f7e145f7168b799`。
3. **失败信号：** 文件缺失、为空或任一 SHA-256 不匹配。
4. **预期原因：** 初始输入不完整或复现过程误改文档。
5. **最小修正：** 从任务提供方重新取得审批原件；不得自行重写。
6. **验证命令：** 哈希通过后显式暂存第 11.3 节的两份文件，再运行 `git diff --cached --name-only`，只应列出两份文档。
7. **预期结果：** 实现提交仍为 HEAD 的父提交；文档原样进入第二提交。
8. **提交点：** 有。按第 11.3 节第二次提交提交，不加入本规格或学习笔记。

## 9. 测试规格

### 9.1 自动测试类型

Day 1 只有集成测试，没有独立单元测试或端到端业务测试。

| 测试 | 类型 | 真实调用 | 固定输入 | 固定期望 | 防止的回归 |
|---|---|---|---|---|---|
| `test_help_and_version_are_available` | 集成 | 在项目根启动 `uv run ybs` 两次 | `--help`、`--version` | 两者 code `0`；帮助含固定说明；版本含 `0.1.0` | 包或 console script 未安装、Typer 根应用损坏、版本入口丢失 |
| `test_find_workspace_root_from_nested_directory` | 集成 | 在临时嵌套目录启动当前 uv Python 并导入真实包 | 临时 `repo/docs/notes` 与只含两行标记的清单 | code `0`；stdout 精确等于临时根路径 | 根查找只认当前目录、未向上遍历、错误导入环境 |

### 9.2 禁止 Mock 的边界

不得 Mock：

- `subprocess.run`；
- `uv run ybs`；
- `sys.executable`；
- `Path.resolve()`、`Path.is_file()`、`Path.read_text()`；
- pytest 的 `tmp_path` 文件系统。

这些是真实安装入口、进程边界和路径行为的合同。Mock 会让测试无法证明最终命令可用。

### 9.3 通过标准

```text
..                                                                       [100%]
2 passed in <耗时>s
```

耗时可变化。必须同时满足退出码 `0` 和 `2 passed`，不能使用 `xfail`、`skip`、降低断言或只检查文件文字来取得通过。

### 9.4 自动测试未覆盖但必须验收的行为

- `bin/ybs` 可执行且能调用 `doctor`；
- `doctor` 的两行输出；
- 未知命令 exit `2` 且无 Traceback；
- `uv.lock` 未漂移；
- Ruff 检查和格式检查；
- Git 提交边界。

这些由第 10 节的可执行命令覆盖。

### 9.5 已审批计划示例与最终测试的差异

已审批实施计划的 Task 1 曾给出基于 `typer.testing.CliRunner` 和测试进程内直接导入 `find_workspace_root()` 的示例。最终落地的 `tests/integration/test_cli_entrypoint.py` 改为真实 `subprocess.run(...)`：帮助/版本通过 `uv run ybs` 验证安装后的 console script，根定位通过当前 uv Python 的独立子进程验证。

复现时必须采用第 6.11 节的最终 subprocess 测试，不得在这两种方案中自行选择。证据优先级是：已落地代码与原始 RED/GREEN 报告高于计划中的示例代码。最终方案让 RED 表现为子进程可观测的 `ModuleNotFoundError`/返回码，而不是测试收集阶段导入失败，同时能够验证打包入口；这项差异已经显式记录，不是隐藏假设。

## 10. 验收命令

### 10.1 执行目录

除根目录缺失的负向检查明确切换到临时目录外，全部命令必须从项目根执行。每次进入新 Shell 都先运行：

```sh
export PROJECT_ROOT="$(pwd -P)"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
printf '%s\n' "$PROJECT_ROOT" "$UV_CACHE_DIR" "$UV_PYTHON_INSTALL_DIR"
test "$UV_CACHE_DIR" = "$PROJECT_ROOT/.demo/uv-cache"
test "$UV_PYTHON_INSTALL_DIR" = "$PROJECT_ROOT/.demo/uv-python"
```

当前参考实现的 `PROJECT_ROOT` 应为 `/Users/jichengye/Documents/WorkSpace/gitee/4-shizhan-xiangmu/z-tech-codex_ybs-workspace/ybs-workspace-lab`。在其他机器复现时，它应是任务提供方给出的复现目录绝对路径。随后所有 uv、测试、测试子进程和 `bin/ybs` 命令必须继承这三个导出变量；如果执行工具为每条命令启动新 Shell，就必须把三行 `export` 放在每次调用前。

### 10.2 正向验收

逐条执行并保留退出码与关键输出：

```sh
uv lock --check
uv sync --frozen
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest tests/integration/test_cli_entrypoint.py -q
uv run ybs --version
uv run ybs --help
./bin/ybs doctor
python_output="$(./bin/ybs doctor)"
printf '%s\n' "$python_output" | sed -n '1p' | grep '^Python: 3\.11\.'
test "$(printf '%s\n' "$python_output" | sed -n 's/^Root: //p')" = "$(pwd -P)"
test -x bin/ybs
```

预期：

| 命令 | 退出码 | 关键输出/状态 | 失败含义 |
|---|---:|---|---|
| `uv lock --check` | `0` | 参考复验 `Resolved 20 packages` | 声明与锁不一致或锁无效 |
| `uv sync --frozen` | `0` | 参考复验 `Audited 19 packages` | 锁不完整、Python/包不可获取 |
| Ruff check | `0` | `All checks passed!` | 代码存在 lint 问题 |
| Ruff format check | `0` | 参考复验 `6 files already formatted` | 源码或测试格式漂移 |
| pytest | `0` | `2 passed`；参考复验 0.18s | 安装入口或根定位合同破坏 |
| `--version` | `0` | `0.1.0` | 入口或版本来源破坏 |
| `--help` | `0` | 固定说明与 `doctor` | Typer 应用/子命令注册破坏 |
| `./bin/ybs doctor` | `0` | Python 3.11.x 与当前根绝对路径 | 权限、uv 委托或根定位破坏 |
| `test -x` | `0` | 无输出 | Shell 启动器未设置执行位 |

参考实现 2026-09-13 的 `doctor` 证据是：

```text
Python: 3.11.14
Root: /Users/jichengye/Documents/WorkSpace/gitee/4-shizhan-xiangmu/z-tech-codex_ybs-workspace/ybs-workspace-lab
```

补丁版本和复现根路径允许变化，格式和语义必须一致。

### 10.3 未知命令负向验收

这条命令预期非零，必须捕获后再断言，不能把它当成整体验收失败：

```sh
invalid_output="$(mktemp)"
set +e
uv run ybs unknown-command >"$invalid_output" 2>&1
invalid_code=$?
set -e
cat "$invalid_output"
test "$invalid_code" -eq 2
! grep -q 'Traceback' "$invalid_output"
rm -f "$invalid_output"
```

预期：整体断言 exit `0`；捕获到的 `invalid_code` 恰为 `2`；输出含 `No such command 'unknown-command'` 或兼容 Typer 版本的等价用法错误；不含 `Traceback`。

### 10.4 找不到根的负向验收

必须从不在项目树中的新临时目录启动项目环境中的命令：

```sh
outside_dir="$(mktemp -d)"
root_error="$(mktemp)"
set +e
(cd "$outside_dir" && uv run --project "$PROJECT_ROOT" ybs doctor) >"$root_error" 2>&1
root_code=$?
set -e
cat "$root_error"
test "$root_code" -eq 5
grep -q 'YBS workspace root not found' "$root_error"
! grep -q 'Traceback' "$root_error"
rm -f "$root_error"
rmdir "$outside_dir"
```

预期：捕获到 code `5`，有固定错误消息，无 Traceback。只删除刚由 `mktemp -d` 创建且为空的精确临时目录；不能使用递归删除。

该负向命令是代码合同的显式复验。本轮资产化已从工作区外真实运行，得到 exit `5`、`YBS workspace root not found` 且无 Traceback；复现执行者仍必须在自己的初始目录重新运行，不能直接沿用本次证据。

### 10.5 Git 验收

完成两个提交后执行：

```sh
git branch --show-current
git log --reverse --format='%s%n%b%n--'
git show --name-only --format= HEAD~1
git show --name-only --format= HEAD
git remote -v
git status --short --untracked-files=all
```

预期：

- 当前分支 `main`；
- 恰有两个 Day 1 提交，顺序、标题、正文拖尾和文件边界符合第 11 节；
- `git remote -v` 无输出；
- 本规格和可选学习笔记可以作为未跟踪资产出现；
- 不得有实现文件的未提交修改，也不得有 Day-02 文件。

## 11. Git 与提交边界

### 11.1 权限与禁止动作

本复现规格授权在收到的复现目录中创建 Day 1 所需的两个**本地**提交，用于重建原阶段历史。它不授权：

- 提交 `docs/specs/Day-01 复现规格.md` 或 `docs/learning/Day-01 掌握什么.md`；
- 添加远端或推送；
- amend、rebase、reset、clean 或强制改写历史；
- 自动提交任何额外文件；
- 修改 Git 全局配置。

若运行平台仍要求对提交动作取得人工批准，应在验收通过后暂停请求批准；不允许为了完成文档而绕过平台权限。

### 11.2 第一次提交：实现与测试

必须只暂存以下 11 个文件：

```text
.gitignore
.python-version
bin/ybs
pyproject.toml
src/ybs_cli/__init__.py
src/ybs_cli/__main__.py
src/ybs_cli/cli.py
src/ybs_cli/errors.py
src/ybs_cli/root.py
tests/integration/test_cli_entrypoint.py
uv.lock
```

使用显式路径暂存，禁止 `git add .`：

```sh
git add .gitignore .python-version pyproject.toml uv.lock bin/ybs \
  src/ybs_cli/__init__.py src/ybs_cli/__main__.py src/ybs_cli/cli.py \
  src/ybs_cli/errors.py src/ybs_cli/root.py tests/integration/test_cli_entrypoint.py
git diff --cached --name-only
git diff --cached --summary -- bin/ybs | grep -F 'create mode 100755 bin/ybs'
git commit -m "feat: add installable ybs command and exit contracts" \
  -m "Confidence: high
Scope-risk: narrow"
```

提交标题必须精确为：

```text
feat: add installable ybs command and exit contracts
```

正文必须包含两个 trailer 行：

```text
Confidence: high
Scope-risk: narrow
```

参考实现提交为 `b5d815e`；新复现因作者、时间和对象哈希不同，SHA 允许不同。

### 11.3 第二次提交：已审批设计与计划

确认两份文档从预置以来未被修改，然后只暂存：

```text
docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
```

执行：

```sh
test -s docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
test -s docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
test "$(shasum -a 256 docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md | awk '{print $1}')" = "ea302b81fff4d5a5edaec4bf3c33dc341d4f3838c368b18d60468644a1b966d5"
test "$(shasum -a 256 docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md | awk '{print $1}')" = "f8f60db0599604697bd1d4b52dc895843f65023cdf360ff33f7e145f7168b799"
git add docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md \
  docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
git diff --cached --name-only
git commit -m "docs: record approved design and implementation plan" \
  -m "Confidence: high
Scope-risk: narrow"
```

提交标题必须精确为：

```text
docs: record approved design and implementation plan
```

正文 trailer 与第一次提交相同。参考实现提交为 `e642b7a`，新 SHA 允许不同。

### 11.4 工作区边界

- 每次提交前运行 `git diff --cached --name-only`；若出现清单外文件，执行 `git restore --staged -- <精确路径>` 只取消暂存，不丢弃用户内容；
- 若存在额外未提交修改，保留它们，不覆盖、不还原；
- 已审批设计文档中存在的历史尾随空格属于输入原件的一部分，不得在第二次提交中顺手格式化；
- 两次提交之间不得混入当前资产化文档 `docs/specs/Day-01 复现规格.md`、`docs/learning/Day-01 掌握什么.md` 或后续阶段文件；第二提交的两份 `docs/superpowers/` design/plan 是 Day 1 已审批输入，不属于这里所说的“禁止提交的资产化文档”。

## 12. 错误处理与恢复

### 12.1 `uv` 或 Git 缺失

表现：`command -v` 非零或 shell 报 command not found。
恢复：停止并报告缺失工具及检测输出；由环境所有者安装。不能用全局 `pip`、另一个包管理器或手写锁文件替代。

### 12.2 Python 3.11 不可用

表现：`uv python pin 3.11` 或同步失败。
恢复：若网络政策允许，用 `uv` 获取 3.11；否则报告环境阻塞。不能把 `requires-python` 或 `.python-version` 降到其他版本。

### 12.3 依赖下载失败

表现：`uv sync` 显示 DNS、证书、超时或包不可用。
恢复：保留 `pyproject.toml`，不要提交不完整 `uv.lock`；检查网络/代理/缓存后重试同一命令。不得把临时镜像凭据写进仓库。

### 12.4 锁文件与清单不一致

表现：`uv lock --check` 非零或 `uv sync --frozen` 拒绝同步。
恢复：先确认 `pyproject.toml` 精确符合第 6.3 节；在第一次提交前重新运行 `uv lock`/`uv sync` 并审阅 `uv.lock`。提交后不得在验收中静默改锁。

### 12.5 构建或 console script 配置错误

表现：`uv run ybs` 找不到命令、导入失败或找不到 `ybs_cli`。
恢复：检查 `packages = ["src/ybs_cli"]`、`ybs = "ybs_cli.cli:app"`、包目录和 `__init__.py`；修正后执行冻结同步并重跑全部测试。

### 12.6 CLI 参数错误

表现：未知命令或无效选项。
期望行为：Typer/Click 输出用法错误、exit `2`、无 Traceback、无业务文件写入。
恢复：使用 `ybs --help` 查看合法命令；不能把非法输入吞掉后返回 `0`。

### 12.7 工作区根未找到

表现：`doctor` stderr 含 `YBS workspace root not found`，exit `5`。
恢复：切换到含 `[tool.ybs]` 和 `workspace = true` 标记的目录树内，或修复本项目清单；不能把任意父目录当根。

### 12.8 文件权限错误

表现：`./bin/ybs` 报 permission denied，或 `test -x bin/ybs` 失败。
恢复：未暂存时先执行 `chmod +x bin/ybs` 并用 `test -x bin/ybs` 检查；显式暂存 `bin/ybs` 后，再用 `git diff --cached --summary -- bin/ybs | grep -F 'create mode 100755 bin/ybs'` 确认索引中的模式为 `100755`，最后重跑启动器验收。普通 `git diff --summary` 不能证明未跟踪文件的索引权限。

### 12.9 测试失败

表现：pytest 非零。
恢复：保留首个失败的 stdout/stderr；先判断是环境失败还是行为回归；只修改合同涉及的最小实现，不降低断言、不跳过测试。修正后依次重跑 pytest、Ruff 和全部 CLI 验收。

### 12.10 写入中断

Day 1 尚未提供原子写工具。若创建文件时中断：

- 用第 6 节逐个核对目标文件；
- 只覆盖本任务新建且明确不完整的精确路径；
- 不递归删除项目根、`docs/` 或用户已有内容；
- `uv.lock` 不完整时由 `uv` 重新生成，不手工修补。

### 12.11 工作区不干净

表现：Git 初始化后出现清单外修改或未跟踪文件。
恢复：资产化规格和学习笔记可以保持未跟踪；其他内容先报告来源。使用显式 `git add` 排除，不执行 `git clean`、`git reset --hard` 或覆盖用户修改。

### 12.12 提交失败

表现：Git 缺作者身份、钩子失败或权限拒绝。
恢复：查看错误与 `git status`；作者身份由用户在仓库级配置或提供，不修改全局配置；修复后重试同一个提交。不 amend 已成功提交，不推送。

### 12.13 已审批文档缺失或变化

表现：第二次提交无法得到两份规定路径的原件。
恢复：停止，让任务提供方重新预置审批副本；不得从对话记忆、本文摘要或参考仓库拼出替代品。

## 13. 验收矩阵

| 阶段目标 | 可执行验证 | 必须结果 | 证据类型 |
|---|---|---|---|
| 独立仓库与分支 | `git branch --show-current`、`git remote -v` | `main`；无远端 | Git |
| uv 写入限制 | 第 10.1 节两个路径 `test`；检查 `.demo/` | 缓存与 uv 管理 Python 均在 `$PROJECT_ROOT/.demo/` | 环境/路径 |
| 审批输入未变化 | 第 4.5 或 11.3 节的两个 `shasum -a 256` 断言 | plan/design 分别匹配固定哈希 | 输入完整性 |
| Python 3.11 项目 | `uv run python --version` | Python 3.11.x | 运行时 |
| 清单与锁一致 | `uv lock --check` | exit `0` | 锁检查 |
| 冻结环境可同步 | `uv sync --frozen` | exit `0` 且不改锁 | 环境 |
| 包可安装并公开命令 | `uv run ybs --version` | exit `0`，`0.1.0` | CLI |
| 根帮助正确 | `uv run ybs --help` | 固定说明和 `doctor` | CLI |
| Shell 入口可执行 | `test -x bin/ybs` | exit `0` | 权限 |
| Shell 委托成功 | `./bin/ybs doctor` | Python 行、Root 行、exit `0` | CLI |
| 根定位支持嵌套目录 | pytest 第二项测试 | 返回临时根绝对路径 | 集成测试 |
| 无根时稳定失败 | 第 10.4 节命令 | code `5`、固定消息、无 Traceback | 负向 CLI |
| 未知命令稳定失败 | 第 10.3 节命令 | code `2`、无 Traceback | 负向 CLI |
| Python 质量检查 | 两条 Ruff 命令 | 均 exit `0` | 静态检查 |
| Day 1 回归 | pytest 命令 | `2 passed` | 集成测试 |
| 第一次提交边界 | `git show --name-only HEAD~1` | 只含规定 11 文件 | Git |
| 第二次提交边界 | `git show --name-only HEAD` | 只含两份审批文档 | Git |
| 提交消息与顺序 | `git log --reverse --format=...` | 两个固定标题和 trailer，顺序正确 | Git |
| 未进入 Day-02 | `git ls-files` 与第 5 节比较 | 不含 Day-02 实现 | 范围审计 |
| 未提交资产化文档 | `git ls-files docs/learning docs/specs` | 不列出本学习笔记/本规格 | 授权审计 |

所有阶段目标至少由上表一条命令验证。若某条因环境限制未运行，最终报告必须标成“未验证”，不能用代码阅读代替执行证据。

## 14. 功能等价判定

### 14.1 必须一致

- 项目名 `ybs-workspace-lab`、版本 `0.1.0`、Python/依赖范围；
- console script 名 `ybs` 及目标 `ybs_cli.cli:app`；
- 公开 Python 接口名称、签名和异常字段；
- `--version`、`--help`、`doctor`、未知命令和无根错误的语义；
- `0`、`2`、`5` 的退出码；
- 工作区标记和“最近祖先优先”的根定位；
- `bin/ybs` 的薄层职责、参数转发、`exec` 和执行权限；
- 两项真实子进程测试及其固定断言；
- 全部验收结果；
- 两个提交的顺序、文件集合、标题和 trailer；
- 不进入 Day-02、不改外部参考项目、不推送。

### 14.2 文件内容必须精确一致的部分

- `.gitignore` 的 10 行模式；
- `.python-version` 的 `3.11`；
- `pyproject.toml` 第 6.3 节全部键、值和依赖范围；
- `bin/ybs` 的四行语义和 shebang；
- 固定帮助文案、版本值、根未找到消息；
- 测试的行为、固定输入与断言；
- 两份已审批 design/plan 必须与任务提供方预置原件字节一致。

生产 Python 代码允许使用不同但清晰的内部组织，只要第 6、7、9、10 节全部合同不变。为降低无上下文复现歧义，第 6 节给出的推荐实现可以直接采用。

### 14.3 允许不同

- Git SHA、作者、提交时间；
- Python 3.11 的补丁版本；
- pytest 耗时；
- Typer/Rich 帮助的颜色、边框和空白；
- 满足版本范围且由当前 `uv` 合法生成的间接依赖版本、锁文件包上传时间和排序细节；
- 私有辅助函数的名字或等价内部写法，但不得改变公开接口和错误边界；
- 复现目录的绝对路径。

### 14.4 最终判定算法

只有同时满足以下条件才判为功能等价：

1. 第 10 节所有已要求命令都实际运行；
2. 第 13 节矩阵没有失败或未解释的未验证项；
3. 自动测试不是通过跳过、Mock 关键边界或降低断言得到；
4. 两次提交边界正确，当前资产化文档 `docs/specs/Day-01 复现规格.md` 与 `docs/learning/Day-01 掌握什么.md` 保持未提交；
5. 代码和 Git 中没有 Day-02 文件；
6. 一个未获得当前聊天记录、只获得修订后本规格与规定初始目录的新独立审阅者，实际走查或复现后确认没有阻塞性歧义。

只比较文件是否存在、只比较字符串片段或只运行 `pytest`，都不足以判为功能等价。

## 15. 已知限制与后续阶段边界

1. 根目录识别只是全文字符串包含检查，不是真正 TOML 解析；注释或无关文本可能误命中。
2. `read_text()` 的编码/权限类 `OSError` 尚未统一包装为 `YbsError`，极端文件错误可能出现未集中映射的异常。
3. 自动测试没有直接覆盖无根 code `5` 和未知命令 code `2`；当前由手工验收覆盖。
4. 版本在 `pyproject.toml` 与 `__init__.py` 两处维护，存在人工同步风险。
5. `bin/ybs` 依赖 POSIX Shell 和外部 `uv`，没有原生 Windows 启动器。
6. `doctor` 不检查 Git、Node、配置、锁状态或外部适配器；完整检查在后续阶段实现。
7. 没有安全路径、原子写、锁和脱敏能力；这些必须在 Day-02 完成后，其他状态写入功能才能开始。
8. Pydantic 与 PyYAML 已作为批准依赖进入锁，但 Day 1 尚未使用。
9. 当前根定位是只读能力，不能据此推断后续写路径已经安全。

以上限制是 Day 1 的明确边界，不是本次资产化遗漏。不得在复现 Day 1 时顺手解决；下一阶段只能在 Day 1 文档和复现审计完成后另行开始。

## 16. 复现审计

### 16.1 作者自检

- 未使用“之前”“同上”“保持原样”“按需实现”“适当处理”等依赖聊天上下文的实施指令；
- 初始目录、预置输入、禁止存在内容、外部边界和 Git 初态已明确；
- 最终文件清单、权限、事实源/派生产物/运行态分类已明确；
- 公开接口、固定消息、输出、退出码、幂等性和路径行为已明确；
- RED/GREEN、测试、验收、Git 提交和恢复命令已明确；
- 已明确两份长审批文档必须由任务提供方预置，无法从本文伪造；
- 已为两份审批输入固定 SHA-256，并区分三份必需输入与一份可选学习笔记；
- 已把 uv 缓存和 uv 管理 Python 的路径限制在项目内，并要求所有 uv、测试子进程和 `bin/ybs` 验收继承环境；
- 已明确只有本规格和学习笔记不得加入当前未授权的资产化提交，第二提交的 design/plan 不属于该禁令。

### 16.2 第一轮独立无上下文实操审计

第一轮审计者只收到返修前的本规格和规定初始目录，没有当前聊天记录。它在隔离临时目录中进行了真实重建，取得以下证据：

- RED：两项测试均因 `ModuleNotFoundError: No module named 'ybs_cli'` 失败；
- GREEN：同一测试文件得到 `2 passed`；
- 锁检查、冻结同步、Ruff、版本、帮助、根内 `doctor`、未知命令 code `2`、工作区外 `doctor` code `5` 均通过，两个负向结果都没有 Traceback；
- 建立两个边界正确的本地提交：实现提交 `4e53e2c`，设计/计划提交 `1ee61c9`。这些是隔离审计仓库的 SHA，不替代当前参考实现的 `b5d815e`/`e642b7a`。

第一轮虽成功重建功能，却暴露了阻塞性文档缺口：旧规格要求写入不越出项目根，却没有规定 `UV_CACHE_DIR` 和 `UV_PYTHON_INSTALL_DIR`。审计者为了满足隔离环境约束，自行选择了项目内 uv 缓存路径；另一个无上下文执行者可能使用用户级默认缓存，产生不同的安全边界。因此第一轮结论是：

```text
功能复现成功，但复现规格需要返修；不能判定最终 PASS。
```

本版已经加入项目根、uv 缓存、uv 管理 Python 的固定环境变量及跨 Shell/子进程继承规则，同时补齐精确初态清单、审批输入哈希和权限检查。第一轮审计提供了真实复现证据，但不能替代返修后的重新审计。

### 16.3 返修后独立无上下文实操复审

新审阅者只得到本版复现规格，以及初始目录中两份通过固定 SHA-256 校验的 design/plan；它没有原实现、当前聊天记录或第一轮审计上下文。审阅者在临时隔离目录中从规定初态重新实施，所有 uv 持久化状态均位于项目内 `.demo/uv-cache` 和 `.demo/uv-python`。

复审得到以下实际证据：

- 运行时为 Python `3.11.14`；
- 锁文件尚不存在时，`uv lock --check` 按预期以 `2` 退出；
- 真实 RED 为两项测试失败，原因都是 `ModuleNotFoundError: No module named 'ybs_cli'`；
- 最小实现后，同一测试文件 GREEN 为 `2 passed`；
- `uv lock --check` 解析 20 个包，`uv sync --frozen` 审计 19 个包；冻结同步前后的锁文件 SHA-256 不变，且锁中不含 Hatchling；
- Ruff 检查、Ruff 格式检查、版本、帮助、根内 `doctor` 均通过；
- 未知命令返回 code `2`，工作区外 `doctor` 返回 code `5`，两个负向结果均无 Traceback；
- 嵌套的独立只读代码审阅结论为 `PASS`；
- Git 分支为 `main`，无远端，恰有两个提交：`b0e2607` 只含规定的 11 个实现/测试文件且 `bin/ybs` 模式为 `100755`；`62fc0e0` 只含两份已审批 design/plan；
- 最终只有本规格处于未跟踪状态，没有实现文件残留修改，也没有 Day-02 文件；
- 执行过程中不需要规格之外的隐含选择；Blocker、Important、Minor 均为零。

最终结论：

```text
PASS：本版复现规格已通过独立无上下文实操审计，Day 1 资产化可据此判定闭合。
```

该结论只关闭 Day 1 资产化与复现审计，不代表已开始或完成 Day-02。
