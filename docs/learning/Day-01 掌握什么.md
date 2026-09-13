# Day-01 掌握什么

> 阶段名称：初始化独立仓库与可安装 CLI
> 项目根目录：`/Users/jichengye/Documents/WorkSpace/gitee/4-shizhan-xiangmu/z-tech-codex_ybs-workspace/ybs-workspace-lab`
> 结论日期：2026-09-13
> 下一阶段：Day-02（本文完成与审计前禁止开始）

## 阶段目标

Day 1 要解决的不是“先写几个 Python 文件”，而是给后续 14 个学习日建立一条稳定、可安装、可测试的统一命令入口：

- `ybs` 能作为 Python 包提供的命令运行；
- `./bin/ybs` 能从仓库内稳定调用同一个命令；
- CLI 有版本、帮助和最小 `doctor` 命令；
- 后续命令可以复用仓库根目录定位和稳定退出码；
- 依赖、测试和格式检查都有统一、可锁定的工程配置。

这一步必须排在最前面。后续配置、任务状态、Git、适配器等功能都会挂到同一个 `ybs` 入口上；如果入口、包结构和错误契约不先稳定，后续每增加一个功能都会重复处理安装、路径和退出方式。

## 本阶段完成的成果

### 工程成果

1. 初始化了独立 Git 仓库，默认分支为 `main`。
2. 建立 Python 3.11+ 的 `uv` 项目，提交了 `pyproject.toml` 与 `uv.lock`。
3. 建立 `src/ybs_cli/` Python 包，并提供：
   - `app: typer.Typer`
   - `main() -> None`
   - `--version`
   - `doctor`
   - `YbsError(message: str, code: int)`
   - `find_workspace_root(start: Path) -> Path`
4. 建立可执行的薄 Shell 入口 `bin/ybs`。
5. 建立真实子进程集成测试，验证安装后的命令和嵌套目录根定位。
6. 固定了首版退出码语义：成功为 `0`，CLI 参数/用法错误为 `2`，文件或根目录定位等操作错误为 `5`。

### 知识成果

使用者已经能够复述并解释：

- `pyproject.toml` 与 `uv.lock` 的职责区别；
- 从 `./bin/ybs doctor` 到 `find_workspace_root()` 的主要执行链路；
- 为什么 Shell 入口要保持很薄，而业务逻辑放在 Python 包中。

需要长期保留的精确补充是：

- `uv sync --frozen` 严格按现有锁文件同步且不更新锁；
- 普通 `uv sync` 会检查并在需要时重新解析、更新锁；
- 没有锁文件时，`uv` 才会根据 `pyproject.toml` 的约束解析并创建锁文件。

### 可复用资产

- 一套 `src/` 布局的可安装 Python CLI 骨架；
- 一个可从任意安装环境转入项目环境的薄 Shell 启动器模式；
- 一个“工作区标记 + 向上查找”的根目录定位模式；
- 一个把预期业务错误映射为稳定退出码的异常边界；
- 一套对安装后命令进行真实子进程测试的方式；
- RED/GREEN、静态检查、锁文件检查、CLI 验收和 Git 边界的检查清单。

## 必须掌握的核心概念

### 1. `pyproject.toml`：项目声明与工具配置的事实源

**它是什么？**
`pyproject.toml` 是现代 Python 项目的标准项目清单。Day 1 中它声明了项目名称、版本、Python 版本约束、运行依赖、开发依赖、构建后端、命令入口，以及 pytest、Ruff 和 YBS 自身的配置。

**它解决什么问题？**
它让安装器、构建工具、测试工具和代码检查工具从一个明确位置读取项目意图，避免把依赖和入口规则分散在多个脚本中。

**为什么本项目需要它？**
`uv` 要从这里知道安装什么，Hatchling 要从这里知道打包哪个包，安装后环境要从 `[project.scripts]` 得到 `ybs` 命令，根目录定位又用 `[tool.ybs] workspace = true` 作为工作区标记。

**它与其他组件的关系是什么？**

- 约束 `uv.lock` 中可选择的版本；
- 把 `ybs` 映射到 `ybs_cli.cli:app`；
- 告诉 Hatchling 打包 `src/ybs_cli`；
- 给 pytest、Ruff 提供统一配置；
- 给 `find_workspace_root()` 提供 Day 1 的仓库标记。

**如果没有它会怎样？**
项目无法以统一方式解析依赖、构建并安装命令，`uv run ybs` 没有入口，工具配置会散落，根目录也失去当前阶段的识别标记。

### 2. `uv.lock`：一次解析结果的精确快照

**它是什么？**
`uv.lock` 是由 `uv` 根据 `pyproject.toml` 的依赖范围解析出的锁文件。它记录项目运行与开发依赖及其间接依赖的具体版本、来源与校验信息；`[build-system].requires` 中的 Hatchling 是构建后端要求，不在当前这份项目依赖锁中。

**它解决什么问题？**
`pyproject.toml` 中的 `typer>=0.16,<1` 是允许范围，不是唯一版本。锁文件把一次合法解析固定下来，使开发、CI 和其他机器可以使用同一依赖图。

**为什么本项目需要它？**
YBS 的目标包含可复现和可审计。若每次安装都重新选择版本，同一份代码可能在不同时间产生不同结果。

**它与其他组件的关系是什么？**

- `pyproject.toml` 给出允许范围；
- `uv lock` 生成或检查锁；
- `uv sync --frozen` 严格按现有锁文件同步环境；
- `.venv/` 是根据锁文件安装出的本地环境，但属于运行时产物，不提交。

**如果没有它会怎样？**
首次 `uv sync` 会按 `pyproject.toml` 重新解析并创建锁；随着包发布新版本，不同机器可能得到不同依赖图，增加“我的机器能跑、你的机器不能跑”的风险。

必须区分三个动作：

| 动作                            | 依赖依据                  |         是否允许改变锁文件 |
| ------------------------------- | ------------------------- | -------------------------: |
| `uv sync --frozen`              | 现有 `uv.lock`            |   否；锁缺失或不适配时失败 |
| `uv sync`                       | `pyproject.toml` 与现有锁 | 是；必要时会重新解析和更新 |
| 没有 `uv.lock` 时执行 `uv sync` | `pyproject.toml`          |         是；会解析并创建锁 |

### 3. Python 包与 `src/` 布局

**它是什么？**
`src/ybs_cli/` 是可安装 Python 包，`src/` 布局要求代码先通过项目安装机制进入环境，而不是偶然从仓库当前目录被导入。

**它解决什么问题？**
它减少“测试能从源码目录导入，但安装后的用户不能导入”的假阳性，使测试更接近真实安装后的使用方式。

**为什么本项目需要它？**
后续所有命令都会持续扩展 `ybs_cli`。从第一天建立明确包边界，比把逻辑堆进脚本后再迁移更稳妥。

**它与其他组件的关系是什么？**
Hatchling 根据 `packages = ["src/ybs_cli"]` 构建包；`uv` 把项目安装进环境；console script 再导入 `ybs_cli.cli:app`。

**如果没有它会怎样？**
模块导入、打包和安装行为容易混乱，测试可能只在仓库根目录下偶然通过。

### 4. Console script：从命令名映射到 Python 对象

**它是什么？**
`[project.scripts]` 中的 `ybs = "ybs_cli.cli:app"` 声明：安装项目时创建名为 `ybs` 的命令，调用 `ybs_cli.cli` 模块中的 `app` 对象。

**它解决什么问题？**
使用者不需要记住 `python -m ...` 或源码路径，只需使用稳定的 `ybs` 命令。

**为什么本项目需要它？**
六种 AI 编程工具、CI 和人工操作都需要共享同一个公开入口，避免每个调用方拼接不同的 Python 命令。

**它与其他组件的关系是什么？**
`uv run ybs` 进入 console script，Typer 的 `app` 再完成参数解析和子命令分发；`python -m ybs_cli` 则通过 `__main__.py` 的 `main()` 到达同一个 `app`。

**如果没有它会怎样？**
CLI 只能靠源码路径或模块命令调用，安装后的用户体验和自动化接口不稳定。

### 5. 薄 Shell 入口 `bin/ybs`

**它是什么？**
一个仅做三件事的 POSIX Shell 启动器：根据自身位置算出仓库根目录、选择该项目的 `uv` 环境、原样转发参数。

**它解决什么问题？**
它避免调用者必须先激活虚拟环境，同时保证即便启动器由别处引用，仍使用正确项目的依赖和命令入口。

**为什么本项目需要它？**
仓库型平台常被人、CI 和不同 AI 工具从不同环境调用；统一启动器可减少环境差异。

**它与其他组件的关系是什么？**
Shell 不直接调用 Python 文件，而是执行 `uv run --project "$REPO_ROOT" ybs "$@"`；之后由 `uv`、console script、Typer 和 Python 模块继续处理。

**如果把业务逻辑写进它会怎样？**
逻辑会分散在 Shell 与 Python 两套语言中，类型检查弱、跨平台差、单元测试困难，错误与退出码也难以集中管理。保持 Shell 很薄能获得清晰分层、较好的维护性、可测试性、类型支持和统一异常边界。

### 6. Typer 命令分发与参数错误

**它是什么？**
Typer 用 Python 函数和装饰器声明 CLI。`app` 是根命令，`doctor()` 是注册的子命令，`--version` 是根回调上的 eager 选项。

**它解决什么问题？**
它统一生成帮助、解析参数、选择子命令并处理 CLI 用法错误。

**为什么本项目需要它？**
后续会新增大量命令。集中在一个命令树中，比手工解析 `$1`、`$2` 更容易维护和测试。

**它与其他组件的关系是什么？**
console script 把控制权交给 `app`；Typer 解析成功后调用 `doctor()`，解析失败时由 Typer/Click 输出用法错误并返回 `2`。

**如果没有统一分发会怎样？**
每个命令都要重复处理参数、帮助和退出方式，不同命令容易产生不一致行为。

### 7. 工作区根目录定位

**它是什么？**
`find_workspace_root(start: Path) -> Path` 先对起点做 `resolve()`，然后从当前路径逐级向父目录查找 `pyproject.toml`。文件文本同时包含 `[tool.ybs]` 和 `workspace = true` 时，最近的该目录就是根目录。

**它解决什么问题？**
命令从子目录执行时，仍需要找到统一配置和项目根，而不能假定当前目录就是根。

**为什么本项目需要它？**
后续状态、配置、项目注册和证据文件都要相对根目录定位。

**它与其他组件的关系是什么？**
`doctor()` 把 `Path.cwd()` 交给根定位函数；成功后输出绝对根路径，失败时抛出 `YbsError("YBS workspace root not found", 5)`，由 CLI 错误边界处理。

**如果没有它会怎样？**
命令只能从根目录运行，或可能把文件读写到错误仓库。Day 1 只实现文本标记识别；更严格的配置解析和路径安全属于后续阶段。

### 8. 稳定错误与退出码

**它是什么？**
`YbsError` 同时携带给人的消息和给自动化调用方的数字退出码。CLI 的 `_exit_for_error()` 负责把预期操作错误输出到标准错误并按指定代码退出。

**它解决什么问题？**
人需要可读错误，CI 和 AI 工具需要不依赖文案的稳定结果。退出码就是二者之间的机器契约。

**为什么本项目需要它？**
YBS 是编排平台，会被其他工具调用。调用方必须区分“成功”“参数错误”“工作流门禁”“适配器失败”和“文件/Git/执行错误”。

**它与其他组件的关系是什么？**
Typer/Click 自己处理用法错误并返回 `2`；YBS 领域/操作代码抛 `YbsError`；命令层集中把异常映射为退出码。Day 1 的根目录未找到使用 `5`。

**如果没有它会怎样？**
调用方只能猜测错误文本，预期失败可能出现 Python Traceback，不利于稳定自动化。

## 完整执行链路

以从项目根执行 `./bin/ybs doctor` 为例，真实顺序是：

```text
用户或 AI 输入 ./bin/ybs doctor
  -> 操作系统按可执行权限启动 bin/ybs
  -> /bin/sh 执行 set -eu
  -> bin/ybs 根据“脚本自身目录/..”计算 REPO_ROOT
  -> exec uv run --project "$REPO_ROOT" ybs doctor
  -> uv 选择该项目环境，并调用已安装的 ybs console script
  -> console script 按 pyproject.toml 的 [project.scripts]
     导入 ybs_cli.cli:app
  -> Typer 解析 doctor 并分发到 cli.py 的 doctor()
  -> doctor() 把 Path.cwd() 交给 root.py 的 find_workspace_root()
  -> root finder 从当前目录向上查找带 YBS 标记的 pyproject.toml
  -> doctor() 输出 Python 版本与绝对 Root 路径
  -> 进程退出码为 0
```

用户原复述的核心链路是正确的：

```text
./bin/ybs
-> [project.scripts]
-> src/ybs_cli/cli.py:app
-> Typer 的 doctor
-> root.py 的 find_workspace_root()
```

需要补全的先后关系是：
- `bin/ybs` 并不会自己读取 `[project.scripts]`。
- 它先定位仓库并执行普通的 `uv run --project ... ybs`，随后项目安装生成的 console script 才依据 `[project.scripts]` 进入 `cli.py:app`。
- 普通 `uv run` 会选择项目环境，也可能检查并协调锁文件与环境；
- Day 1 的冻结保证来自前置的 `uv sync --frozen`、未变化的 `pyproject.toml`/`uv.lock` 和之后的验收，而不是 `bin/ybs` 自身带了 `--frozen`。

还要注意：
- `bin/ybs` 选择项目环境但不会执行 `cd`。
- `doctor()` 搜索的是调用者的当前工作目录 `Path.cwd()`，不是启动器所在目录。

## 关键文件地图

| 文件                                                                      | 职责                                                       | 主要输入                          | 主要输出                           | 被谁调用                              | 依赖                           |
| ------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------- | ---------------------------------- | ------------------------------------- | ------------------------------ |
| `.python-version`                                                         | 声明本地项目使用 Python 3.11 系列                          | `3.11`                            | `uv` 的版本选择提示                | `uv`                                  | 本机或 `uv` 可提供 Python 3.11 |
| `pyproject.toml`                                                          | 项目、构建、依赖、入口和工具配置事实源                     | 人工维护的 TOML                   | 可安装项目定义与 `ybs` 入口        | `uv`、Hatchling、pytest、Ruff、根定位 | TOML 语义及各工具              |
| `uv.lock`                                                                 | 固定项目运行与开发依赖图（不含 build-system 构建后端要求） | `pyproject.toml` 的范围与解析结果 | 精确包版本、来源、哈希             | `uv sync --frozen`、CI                | `uv`                           |
| `.gitignore`                                                              | 排除环境、缓存、构建和运行态数据                           | 路径模式                          | Git 忽略规则                       | Git                                   | 无                             |
| `bin/ybs`                                                                 | 定位自身仓库并委托给项目 `ybs` 命令                        | CLI 参数、脚本位置                | 用同样参数替换为 `uv run ...` 进程 | 人、AI、CI                            | POSIX `sh`、`uv`               |
| `src/ybs_cli/__init__.py`                                                 | 包说明和 `__version__`                                     | 无                                | `0.1.0`                            | `cli.py`                              | Python                         |
| `src/ybs_cli/__main__.py`                                                 | 支持 `python -m ybs_cli`                                   | 模块调用                          | 调用 `main()`                      | Python 模块运行器                     | `cli.py`                       |
| `src/ybs_cli/cli.py`                                                      | Typer 应用、版本、`doctor`、错误映射                       | 参数、当前目录                    | 标准输出/错误和退出码              | console script、`__main__.py`         | Typer、`root.py`、`errors.py`  |
| `src/ybs_cli/errors.py`                                                   | 定义带稳定代码的预期操作错误                               | message、code                     | `YbsError` 实例                    | 根定位及后续领域模块                  | Python                         |
| `src/ybs_cli/root.py`                                                     | 从起点向上寻找最近 YBS 工作区                              | `Path`                            | 根目录 `Path` 或 code 5 错误       | `doctor()` 及后续命令                 | `pathlib`、`YbsError`          |
| `tests/integration/test_cli_entrypoint.py`                                | 从子进程验证真实安装入口与根定位                           | 临时目录、CLI 参数                | pytest 断言结果                    | pytest                                | `uv`、已同步环境               |
| `docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md` | 保存已审批的整体目标、架构、安全边界与 15 日教学路线       | 已确认的需求与设计决策            | 后续实施必须遵守的设计基线         | 人、AI、实施计划与审阅流程            | 使用者审批、项目目标           |
| `docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md`        | 把设计拆成逐日任务、接口、TDD、验收和提交边界              | 已审批设计                        | Day 1 至 Day 15 的可执行任务清单   | 人、AI、Day 1 执行与后续阶段          | 已审批设计、工具链约束         |

## 关键命令与结果

以下命令都从项目根目录执行。表中的结果来自 2026-09-13 的真实复验；“应该亲自运行”不等于声称使用者已经亲手输入过。

| 命令                                                                                                                                                   | 作用                             | 本次关键结果                                                | 成功判断                       | 失败时优先检查                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- | ----------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------- |
| `uv lock --check`                                                                                                                                      | 检查锁文件与项目声明一致         | exit `0`，`Resolved 20 packages`                            | 无锁漂移错误                   | `pyproject.toml` 是否改过、锁文件是否缺失                  |
| `uv sync --frozen`                                                                                                                                     | 严格按锁文件同步环境             | exit `0`，`Audited 19 packages`                             | 不改锁且同步成功               | Python 版本、网络/缓存、锁文件平台兼容性                   |
| `uv run ruff check src tests`                                                                                                                          | 静态检查 Python 源码和测试       | exit `0`，`All checks passed!`                              | 无 lint 错误                   | 输出中的文件、规则编号                                     |
| `uv run ruff format --check src tests`                                                                                                                 | 检查格式而不改文件               | exit `0`，`6 files already formatted`                       | 没有需要格式化的文件           | 运行 `uv run ruff format src tests` 后审阅差异             |
| `uv run pytest tests/integration/test_cli_entrypoint.py -q`                                                                                            | 运行 Day 1 集成测试              | exit `0`，`2 passed in 0.18s`                               | 两项测试全部通过               | 首个失败、子进程 stderr、包是否安装                        |
| `uv run ybs --version`                                                                                                                                 | 验证安装入口和版本               | exit `0`，`0.1.0`                                           | stdout 含 `0.1.0`              | `[project.scripts]`、包安装、版本常量                      |
| `uv run ybs --help`                                                                                                                                    | 验证根命令、帮助和 `doctor` 注册 | exit `0`，显示项目说明及 `doctor`                           | 帮助含固定说明和命令名         | Typer `app`、命令装饰器                                    |
| `./bin/ybs doctor`                                                                                                                                     | 验证薄入口、环境、根定位         | exit `0`，Python `3.11.14`，Root 为项目绝对路径             | 两行输出且根正确               | 文件执行位、`uv`、当前目录、工作区标记                     |
| `uv run ybs unknown-command`                                                                                                                           | 验证用法错误契约                 | exit `2`，无 `Traceback`                                    | 非零值恰为 2 且有清晰错误      | 是否绕过 Typer、异常是否泄漏                               |
| 从工作区外执行 `uv run --project /Users/jichengye/Documents/WorkSpace/gitee/4-shizhan-xiangmu/z-tech-codex_ybs-workspace/ybs-workspace-lab ybs doctor` | 验证找不到工作区时的操作错误合同 | exit `5`，含 `YBS workspace root not found`，无 `Traceback` | 非零值恰为 5、消息固定且无堆栈 | 当前目录是否真的在工作区外、`YbsError` 是否由 CLI 集中映射 |

`unknown-command` 本来就应该失败，因此不能只看“非零”就把验收判为失败；要验证它以**预期的**退出码 `2` 失败，并且没有 Traceback。

## 测试驱动记录

### RED：先建立可执行但必然失败的行为测试

先写 `tests/integration/test_cli_entrypoint.py`，通过真实子进程检查两类行为：

1. `uv run ybs --help` 与 `--version` 可用；
2. 从临时仓库的深层目录调用 `find_workspace_root()`，能够返回带标记的临时根目录。

当时 Python 包和 console script 实现尚不存在。测试本身成功被 pytest 收集并执行，但两个子进程都因 `ModuleNotFoundError: No module named 'ybs_cli'` 返回 `1`，最终为 `2 failed in 0.51s`。这是目标功能缺失导致的 RED，不是 pytest 没装或测试语法错误造成的伪红。

### GREEN：只补足合同所需的最小实现

最小实现包括：

- 可安装的 `ybs_cli` 包；
- Typer `app`、帮助与 `--version`；
- `YbsError`；
- 向上搜索工作区的 `find_workspace_root()`；
- 最小 `doctor`；
- 薄 Shell 启动器；
- `pyproject.toml` 中的 YBS 工作区标记。

原始 GREEN 证据为 `2 passed in 0.16s`；2026-09-13 的重新验收为 `2 passed in 0.18s`。耗时不是合同，`2 passed` 和退出码 `0` 才是合同。

### 这些测试防止的回归

- 项目仍存在源码，但安装入口 `ybs` 消失；
- 帮助说明或版本入口被破坏；
- `find_workspace_root()` 只能从根目录工作；
- 测试绕过实际包安装，产生“源码能导入、安装后不能运行”的假通过。

当前测试没有直接覆盖 `doctor` 的输出、找不到根时的 code `5`、未知命令的 code `2`；这些已由验收命令补充验证。其中，本轮资产化又从工作区外使用项目环境运行了 `doctor`，真实得到 exit `5`、固定错误消息且无 Traceback。后续可以把这些验收转成自动回归测试，但不能在 Day 1 资产化时修改已验收实现。

## 过关标准

Day 1 的过关不是会背文件名，而是能完成以下判断和复述：

- 能用自己的话区分 `pyproject.toml` 的“允许范围/项目声明”和 `uv.lock` 的“具体解析结果”；
- 能说明 `uv sync --frozen`、普通 `uv sync`、无锁同步的差异；
- 能从 `./bin/ybs doctor` 讲清 Shell、`uv`、console script、Typer、`doctor()`、根定位和最终输出的顺序；
- 能解释为什么 Shell 层不承载业务逻辑；
- 能说明未知命令为什么返回 `2`，找不到工作区为什么按设计返回 `5`；
- 能运行或指挥 AI 运行锁检查、测试、Ruff、帮助、版本、`doctor` 和负向命令；
- 能根据退出码、关键输出和 Traceback 判断实现是否符合合同；
- 能检查 AI 是否保持了 `bin/ybs` 的薄层、`src/` 包结构、稳定错误边界和真实子进程测试。

## 过关问题、使用者回答与准确解释

### 问题 1：`pyproject.toml` 和 `uv.lock` 分别解决什么问题？

**使用者回答**

> `pyproject.toml` 主要解决项目 name、依赖包、项目构建、入口脚本、代码检查和格式化等相关信息。
> `uv.lock` 锁住了当前项目所使用的依赖版本，实际项目安装也是首先使用 `uv.lock` 中的版本；如果没有 `uv.lock`，以 `pyproject.toml` 的依赖包版本为准进行依赖安装。

**回答中正确的部分**

- 准确识别了 `pyproject.toml` 的项目元数据、依赖、构建、入口和工具配置职责；
- 准确识别了 `uv.lock` 用来固定具体依赖版本；
- 理解了没有锁文件时需要从项目声明中的依赖范围解析。

**需要补充或纠正的部分**

“安装首先使用锁文件”需要附带命令语义：

- `uv sync --frozen` 必须使用现有锁，不允许更新；
- 普通 `uv sync` 会先检查项目声明与锁是否一致，必要时会重新解析并更新锁；
- 没有锁时，普通同步才从 `pyproject.toml` 解析并创建锁。

**准确解释**

`pyproject.toml` 表达项目**允许和需要什么**；`uv.lock` 记录一次解析后**实际选中了什么**。前者是意图和约束，后者是可重复安装的精确依赖图。CI 使用 `--frozen` 的意义是发现声明与锁不一致就失败，而不是在验收时悄悄改锁。

### 问题 2：请从 `./bin/ybs doctor` 说出完整调用链。

**使用者回答**

> `./bin/ybs` → 根据 `pyproject.toml` 中的 `[project.scripts]` 找到命令入口文件 `src/ybs_cli/cli.py:app` → `app` 是 Typer 程序 → 找到注册的 command `doctor` → 执行 `root.py` 中的 `find_workspace_root()` 函数。

**回答中正确的部分**

- 识别了 `[project.scripts]` 到 `ybs_cli.cli:app` 的映射；
- 识别了 `app` 是 Typer 应用；
- 识别了 `doctor` 的命令分发和根定位函数。

**需要补充或纠正的部分**

Shell 与 console script 之间还有 `uv`：`bin/ybs` 先根据**脚本自身位置**计算仓库根，然后执行 `uv run --project <root> ybs doctor`；项目环境中的 `ybs` console script 才按 `[project.scripts]` 导入 `app`。此外，根定位的起点是调用者当前目录，而不是 `REPO_ROOT`。

**准确解释**

完整顺序是：Shell 定位项目并委托 → `uv` 选择项目环境 → 安装入口导入 `app` → Typer 解析参数并调用 `doctor()` → `doctor()` 以 `Path.cwd()` 调根定位 → 输出 Python 版本和根路径。任何一层都各有单一职责。

### 问题 3：为什么不把所有逻辑直接写进 `bin/ybs`？

**使用者回答**

> 是为了更清晰的分层和功能维护。

**回答中正确的部分**

这就是最核心的架构理由：入口层与业务层分离，使职责清楚、后续修改范围可控。

**需要补充或纠正的部分**

还可以从工程能力补充四点：Python 业务代码更容易做自动测试和类型标注；不同平台的行为更一致；异常与退出码可以集中映射；所有调用方最终走同一个可安装入口，避免 Shell 与 Python 出现两份规则。

**准确解释**

`bin/ybs` 只负责“找到哪一个项目环境、把哪些参数交过去”；“命令意味着什么、如何找根、如何报错”属于 Python 包。这样既保留了一个方便的仓库入口，又不会让启动器成为第二套业务系统。

## 常见误区

1. **把 `pyproject.toml` 当成精确锁文件。** 依赖范围允许多个版本；精确解析结果在 `uv.lock`。
2. **认为有 `uv.lock` 时所有 `uv sync` 都绝不会改锁。** 只有 `--frozen` 明确禁止更新。
3. **认为 `bin/ybs` 直接解析 `[project.scripts]`。** 它只调用 `uv run ... ybs`；安装系统负责 console script 映射。
4. **认为 `--project` 会改变 CLI 的当前目录。** 它选择项目环境；`doctor()` 仍从 `Path.cwd()` 查根。
5. **把未知命令的退出 `2` 当成程序崩溃。** 这是 Typer/Click 的正常用法错误合同；真正要防的是错误码漂移或 Traceback 泄漏。
6. **在 Shell 中继续加入业务分支。** 这会破坏单一入口、可测试性和统一错误管理。
7. **只测试 Python 函数，不测试安装后的命令。** 可能漏掉构建配置、console script 或环境同步问题。
8. **用固定真实仓库路径测试根定位。** 集成测试应使用临时目录，固定输入、隔离状态。
9. **把 RED 解释成任何失败都可以。** 只有目标功能尚未实现造成的预期失败才是有效 RED。
10. **认为文本包含检查等价于完整 TOML 语义验证。** Day 1 的根标记只是最小实现，注释或特殊文本也可能误命中；这是已知边界。

## Teach-back 结论

| 维度               | 判断                                       | 证据与边界                                                                                                                                                                           |
| ------------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 工程验收           | 通过                                       | 锁检查、冻结同步、Ruff、2 项集成测试、版本、帮助、`doctor`、未知命令和工作区外 `doctor` 的负向验收均真实执行并符合预期；存在两次边界清楚的 Git 提交。                                |
| 理解复述           | 通过                                       | 使用者能正确说明项目清单、锁文件、主要调用链和薄 Shell 的分层理由；本文已补齐 `uv` 的精确同步语义、调用先后和工程性理由。                                                            |
| 实践操作           | 按“支配 AI 完成并能审查结果”的学习方式通过 | 正向验收、未知命令以及从工作区外触发 code `5` 的负向命令均由 AI/控制端实际执行，使用者参与复述与判断；没有证据表明使用者本人逐条在终端手动输入，因此“个人手动操作熟练度”未单独验证。 |
| Day 1 是否真正完成 | 可以判定完成                               | 既有功能与证据，也有理解复述和可复用资产；当前学习目标允许借助 AI 编程工具完成实现。若个人目标升级为“不借助 AI 独立操作”，仍需补做一次手动重建练习，但它不是当前 Day 1 的阻塞项。    |

建议在不进入 Day 2 的前提下做一次 10 分钟闭卷复述：只看命令名，解释 `./bin/ybs doctor` 每一层的职责，以及三种 `uv sync` 情形。它用于增强记忆，不改变本阶段已经通过的结论。

## 证据索引

- 实现：`.gitignore`、`.python-version`、`pyproject.toml`、`uv.lock`、`bin/ybs`、`src/ybs_cli/`、`tests/integration/test_cli_entrypoint.py`
- 已批准设计：`docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md`
- 已批准计划：`docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md` 的 Task 1
- TDD 原始报告：`.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/task-1-report.md`
- 本轮补充负向实证：从工作区外运行项目环境中的 `ybs doctor`，exit `5`，stderr 含 `YBS workspace root not found`，且无 `Traceback`
- 第一轮无上下文实操审计：隔离目录中重现 RED `2 failed`、GREEN `2 passed`、全部正负验收和两个边界提交；同时发现旧规格未固定 uv 缓存/解释器目录，因此规格已返修并等待新审阅者复审，不能把第一轮当作最终审计 PASS
- 实现提交：`b5d815e` — `feat: add installable ybs command and exit contracts`
- 设计/计划提交：`e642b7a` — `docs: record approved design and implementation plan`
- 使用者 Teach-back：本阶段对 `pyproject.toml`、`uv.lock`、调用链和薄 Shell 的三项复述
