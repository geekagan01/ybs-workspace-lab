# YBS Workspace 学习演示版设计

**状态：** 已批准  
**批准日期：** 2026-09-13  
**目标目录：** `ybs-workspace-lab/`  
**参考实现：** `../ybs-workspace/`

## 1. 背景

参考项目 `ybs-workspace` 不是财税业务应用，而是一个基于 Git Submodule 的多项目协作工作区。它通过统一规则、声明式路由、任务记忆、正式文档、自动化脚本和多 AI 工具配置，约束跨前后端项目的研发流程。

参考项目已经形成以下重要思想：

- `AGENTS.md` 是仓库级唯一规则源。
- `workspace/*.yaml` 负责项目注册、功能路由、流程和部署映射。
- `docs/` 保存正式、长期有效的需求、设计和技术知识。
- `workspace-memory/` 保存任务过程、归档记录和纠偏经验。
- `.agents/` 保存统一规则与 Skills，再分发到各 AI 工具目录。
- `scripts/` 把重复且容易遗漏的流程动作自动化。

本项目不逐文件复制参考仓库，而是从零实现一个规模可控、可以独立运行、能够解释核心机制的增强复刻版。

## 2. 目标与成功标准

### 2.1 目标

在三周、十五个学习日内，实现一个仓库型 AI 研发编排平台。平台使用 Python CLI 解释和执行仓库内的规则与配置，并通过两个轻量示例子项目演示一次需求从输入到归档的完整生命周期。

教程以 AI 结对方式进行。每个学习日都包含：概念解释、限定范围的 AI 提示词、代码审阅要点、自动验证和复盘结果。

### 2.2 成功标准

完成后必须满足以下条件：

1. 新机器按照 README 可在 10 分钟内完成安装和环境自检。
2. `ybs` CLI 可以完成配置校验、项目路由、任务启动、阶段推进、验证和归档。
3. 两个本地示例项目以 Git Submodule 方式接入，并可以根据需求关键词完成项目缩圈。
4. 同一份规则与 Skills 可以分发给 Codex、Claude Code、Cursor、Trae、Qoder 和 OpenCode。
5. 工单、Wiki、CI 和通知使用本地 Mock 适配器完成契约演示，不依赖企业内网。
6. `DEMO-101` 可以完整走过启动、缩圈、设计、实施、验证、确认、Mock 回写、归档和提交证据记录。
7. 配置错误、非法阶段迁移、重复执行、写入中断、路径越界和密钥泄漏均有自动测试。
8. 使用者能够说明协议、配置、运行时、正式文档、过程记忆和适配器之间的边界。

## 3. 范围

### 3.1 包含

- 独立的 `ybs-workspace-lab` Git 仓库。
- Python 3.11+ CLI 与一个薄 Shell 启动入口。
- 项目注册、项目依赖、功能路由和工作流配置。
- Pydantic 配置模型以及可导出的 JSON Schema。
- 任务状态机、人工门禁、结构化状态和人类可读记忆。
- SRS、TDD、技术指南和任务记忆模板。
- 两个可运行的轻量示例子模块：`demo-web` 和 `demo-api`，并附带可离线恢复它们的 Git Bundle。
- 六种 AI 工具的规则/Skill 分发适配器。
- 工单、Wiki、CI、通知的 Mock 适配器。
- Ruff、pytest、配置校验和端到端 smoke 的 CI 门禁。
- `DEMO-101` 完整演示脚本与教学文档。

### 3.2 不包含

- 财税业务代码或参考仓库中的真实业务子模块。
- 中央服务、数据库、管理看板或常驻后台进程。
- GitLab、Gitee、禅道、Jira、Confluence、语雀或 Jenkins 的本地部署。
- 真实企业账号、真实令牌和真实生产发布。
- 原生 Windows 支持；首版支持 macOS 和 Linux。Python 核心保持可移植，Windows 可作为后续扩展。
- 多机器并发调度、分布式锁和远程任务队列。

## 4. 方案选择

### 4.1 采用：增强复刻

保留参考项目“仓库即平台、文件即状态”的核心结构，同时使用 Python 提升配置解析、错误处理、测试和跨平台维护能力。

选择理由：

- 比纯 Shell 更容易为状态机、路由和原子写入建立可靠测试。
- 比服务端平台更容易在个人环境中完成并演示。
- 保留与参考项目相同的信息分层，学习结果可以迁移到真实团队工作区。
- Python 代码可以被 AI 高效生成，同时通过类型、Lint 和测试保持可审阅性。

### 4.2 未采用：完全照搬 Shell/YAML

这种方案最接近参考仓库，但复杂 YAML 解析、状态恢复、并发保护和跨平台错误处理会分散在多个脚本中，难以建立稳定接口和细粒度测试。

### 4.3 未采用：中央服务与管理看板

这种方案适合产品化阶段，但会引入 Web 服务、数据库、认证、部署和运维，明显超出个人学习演示的时间边界，也会遮蔽仓库型编排的核心机制。

## 5. 总体架构

平台分为六层：

1. **任务输入层**：接收需求、Bug、任务标识、范围和验收标准。
2. **协议内核层**：用 `AGENTS.md` 定义唯一仓库级规则，用项目局部规则表达差异。
3. **声明式配置层**：用 YAML 描述项目、依赖、路由、工作流和适配器。
4. **编排运行时层**：由 Python CLI 加载配置、执行状态迁移、写入证据并返回稳定退出码。
5. **执行资产层**：保存正式文档、任务记忆、示例子模块和测试。
6. **分发与集成层**：生成六种 AI 工具需要的规则结构，并通过 Mock 适配器演示外部系统交互。

核心数据流：

```text
任务输入
  -> 协议约束
  -> 配置缩圈
  -> CLI 执行
  -> 文档与记忆留痕
  -> AI 工具分发与 CI 验证
```

Python CLI 只解释和执行规则，不拥有规则定义权。修改 CLI 不得隐式改变 `AGENTS.md` 或 `workspace/*.yaml` 的含义。

## 6. 目录与组件

```text
ybs-workspace-lab/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── bin/
│   └── ybs
├── src/ybs_cli/
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── routing.py
│   ├── workflow.py
│   ├── memory.py
│   ├── filesystem.py
│   ├── tool_sync.py
│   └── adapters/
│       ├── base.py
│       ├── issue_mock.py
│       ├── wiki_mock.py
│       ├── ci_mock.py
│       └── notification_mock.py
├── workspace/
│   ├── projects.yaml
│   ├── feature-routing.yaml
│   ├── workflow.yaml
│   ├── adapters.yaml
│   └── schemas/
├── .agents/
│   ├── rules/
│   └── skills/
├── templates/
│   ├── project-agent.md
│   ├── task-memory.md
│   ├── srs.md
│   └── tdd.md
├── docs/
│   ├── srs/
│   ├── tdd/
│   ├── guidelines/
│   └── superpowers/
├── workspace-memory/
│   ├── in-progress/
│   ├── done/
│   └── feedback/
├── projects/
│   ├── demo-web/
│   └── demo-api/
├── fixtures/repos/
│   ├── demo-web.bundle
│   └── demo-api.bundle
├── mocks/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── e2e/
└── .github/workflows/ci.yml
```

组件职责：

- `config.py` 和 `models.py`：加载 YAML、映射类型、生成 Schema 并输出字段级错误。
- `routing.py`：根据关键词、项目依赖和显式优先级生成项目范围建议。
- `workflow.py`：校验当前阶段、前置条件、人工批准和证据后执行迁移。
- `memory.py`：维护任务状态与过程摘要，不保存正式规格正文。
- `filesystem.py`：限制写入根目录、执行原子替换、任务级锁和脱敏。
- `tool_sync.py`：将统一规则和 Skills 渲染为各工具目标目录中的生成副本，并维护生成清单。
- `adapters/`：通过统一协议隐藏工单、Wiki、CI 和通知的差异。

## 7. 技术基线

- Python 3.11+
- Typer：命令行接口
- Pydantic：配置和状态类型
- PyYAML：YAML 读写
- pytest：自动测试
- Ruff：格式、导入和常见错误检查
- Git：版本、子模块和审计轨迹
- POSIX Shell：`bin/ybs` 薄入口

约束：

- 公共函数和数据结构必须具有类型标注。
- 模块保持单一职责，禁止用复杂元编程隐藏控制流。
- 依赖必须锁定；CLI 不在运行时自动安装依赖。
- 测试通过前不得将任务标记为验证完成。

## 8. 配置模型

### 8.1 项目注册

`workspace/projects.yaml` 中每个项目包含：

- `key`：稳定唯一标识。
- `name`：显示名称。
- `path`：仓库内相对路径。
- `type`：`frontend`、`backend` 或 `support`。
- `stack`：技术栈说明。
- `business_domains`：业务领域关键词。
- `dependencies`：其他项目 `key` 列表。
- `project_doc`：项目局部规则路径。
- `verify_commands`：该项目的确定性验证命令列表。

校验必须拒绝重复 key、越界路径、不存在的依赖、自依赖和依赖环。

### 8.2 功能路由

`workspace/feature-routing.yaml` 中每条规则包含：

- `key`：稳定路由标识。
- `feature`：人类可读功能名称。
- `keywords`：触发关键词。
- `primary_projects`：主要项目。
- `fallback_projects`：证据不足时建议检查的项目。
- `priority`：规则优先级。

路由结果必须包含命中规则、主要项目、由依赖闭包补充的项目、备选项目和解释文本。无匹配时返回“需要人工缩圈”，不得猜测项目。

### 8.3 工作流

`workspace/workflow.yaml` 定义以下有序阶段：

```text
intake
-> branch_confirm
-> clarify
-> scope
-> plan
-> implement
-> verify
-> confirm
-> memory
-> external_sync
-> commit
-> done
```

每个阶段包含：

- `requires`：前置阶段。
- `required_evidence`：必须存在的证据键。
- `manual_approval`：是否要求人工批准。
- `next`：合法后继阶段。

`stage` 表示任务当前正在执行的阶段。`required_evidence` 和 `manual_approval` 都在**离开当前阶段**时校验；`advance` 每次只能进入一个直接后继阶段。

任务等级定义为：

- `L0`：单项目的配置、文档或极小改动；不强制 SRS/TDD，但必须在 `memory.md` 中记录计划和验证方式。
- `L1`：最多两个项目且不改变公共接口；必须有 SRS，TDD 由 scope 决策记录决定。
- `L2`：跨项目公共接口、架构边界或高风险行为变更；必须有已批准的 SRS 和 TDD。

关键迁移条件：

- `scope -> plan`：已保存 `scope.projects`、路由建议证据和 scope 批准人。
- `plan -> implement`：已保存计划批准人；L1/L2 满足对应 SRS/TDD 要求。
- `verify -> confirm`：最近一次任务验证记录为 `passed`。验证证据必须包含命令、退出码、时间和产物摘要，不能只检查路径存在。
- `confirm -> memory`：已记录最终人工确认。
- `memory -> external_sync`：`memory.md` 已更新，并记录是否产生长期知识。
- `external_sync -> commit`：只能由 `ybs task sync` 在全部 Mock 同步成功后完成；失败时停留在 `external_sync`。
- `commit -> done`：只能由 `ybs task finish` 完成，且必须验证提交 SHA 后再原子归档。

普通 `advance` 拒绝直接进入 `commit` 或 `done`，也不允许跳过任何人工门禁。

### 8.4 适配器配置

`workspace/adapters.yaml` 只保存驱动名称、启用状态、Mock 数据目录、超时和环境变量名称。密钥值不得进入仓库。

首版提供四类适配器：

- Issue：读取 Mock 需求，写入 Mock 评论和标签。
- Wiki：读取 Mock 页面快照。
- CI：返回 Mock 构建状态并保存触发记录。
- Notification：保存 Mock 通知事件。

## 9. 任务状态与文档边界

每个任务使用目录：

```text
workspace-memory/in-progress/<task-id>-<slug>/
├── status.yaml
├── memory.md
└── evidence/
```

`status.yaml` 是机器状态的唯一事实源，至少包含：

- `version`
- `task_id`
- `title`
- `kind`
- `level`
- `stage`
- `scope.projects`
- `approvals`
- `evidence`
- `external_sync`
- `created_at`
- `updated_at`

`memory.md` 是给人和 AI 阅读的过程摘要，保存决策、风险、发现、验证结论和下一步。它不得重复保存完整 SRS/TDD 正文。

`docs/srs/`、`docs/tdd/` 和 `docs/guidelines/` 保存正式、长期有效内容。任务完成后，任务目录整体移动到 `workspace-memory/done/YYYY-MM/`。

## 10. CLI 接口

首版公开命令：

```text
ybs doctor
ybs config validate [--json]
ybs project list [--json]
ybs project graph [--json]
ybs route <request-text> [--task <task-id>] [--json]
ybs task start <task-id> --title <title> --kind requirement|bug --level L0|L1|L2
ybs task show <task-id> [--json]
ybs task set-scope <task-id> --projects <key,key> --approve-by <name>
ybs task advance <task-id> --to <stage> [--approve-by <name>] [--evidence <key=path>]
ybs task validate <task-id> [--json]
ybs task sync <task-id> [--retry-failed] [--json]
ybs task finish <task-id> --commit-ref <sha>
ybs tools sync [--check] [--dry-run]
ybs adapter health [--json]
ybs demo bootstrap
ybs demo verify
```

`ybs route --task` 只把路由建议写入任务证据，不直接改变实际范围。`ybs task set-scope` 校验项目 key 后写入人工确认的 `scope.projects`。任务等级在 `start` 时必须显式提供，后续不得通过手工编辑 `status.yaml` 改级。

`ybs task validate` 读取 `scope.projects` 对应的 `verify_commands`，依次记录命令、退出码、开始/结束时间和输出摘要，并把结果写入任务 `evidence/`。任一命令失败时返回退出码 `5`，任务不能离开 `verify`。

`ybs task sync` 使用 `<task-id>:<adapter-kind>:<event>` 作为幂等键。同步失败时保留已成功结果和失败原因；`--retry-failed` 只重试失败项。全部成功后才从 `external_sync` 进入 `commit`。

所有会修改文件的命令必须支持 `--dry-run` 或先提供等价预览。所有命令必须返回稳定退出码：

- `0`：成功。
- `2`：参数或配置无效。
- `3`：工作流门禁阻止执行。
- `4`：适配器不可用，核心状态保持可恢复。
- `5`：文件、Git 或未知执行错误。

## 11. 任务数据流

`DEMO-101` 的固定需求为：“在演示工作台显示 API 服务状态”。它以 `L2` 启动，路由规则首先命中 `demo-web`，再通过项目依赖闭包加入 `demo-api`。

业务验收固定为：

1. `GET /api/status` 返回 HTTP 200 和精确 JSON `{"status":"ok","service":"demo-api"}`。
2. `demo-web` 的纯函数接收上述响应后输出文本 `API status: ok`。
3. 网络失败或响应缺少 `status` 时，页面模型输出 `API status: unavailable`。

演示执行顺序：

1. `ybs doctor` 验证 Python、Git、目录和配置。
2. `ybs demo bootstrap` 从仓库内的 Git Bundle 创建本地只读来源并初始化两个示例子模块，不访问网络。
3. `ybs task start` 创建任务目录并记录原始输入和 Git 快照。
4. `ybs route --task DEMO-101` 计算目标项目、依赖闭包和备选范围，只保存建议。
5. 使用者通过 `ybs task set-scope` 确认 `demo-web,demo-api`，并逐阶段推进到 plan。
6. 按 L2 要求生成并确认 SRS/TDD。
7. 在两个示例子模块中实现固定的服务状态需求。
8. `ybs task validate DEMO-101` 执行配置检查、两个项目的验证命令和改动范围检查，并保存结构化证据。
9. 使用者执行最终确认并更新任务记忆。
10. `ybs task sync DEMO-101` 让 Mock 适配器写入工单评论、CI 状态和通知事件。
11. 使用者完成 Git 提交，将提交 SHA 交给 `ybs task finish`。
12. CLI 校验提交证据并将任务目录归档到 `done/YYYY-MM/`。

所有迁移必须幂等。重复执行成功步骤不能生成重复记录。任何失败都不得把 `status.yaml` 留在不可解析或半更新状态。

## 12. AI 工具分发

`.agents/rules/` 和 `.agents/skills/` 是统一源目录。Codex 直接消费根 `AGENTS.md` 与 `.agents/skills/`；这两处属于源数据，不进入生成清单，也不由 `tools sync` 改写或删除。分发器为其他工具生成以下目标：

- Claude Code：`CLAUDE.md` 入口、`.claude/rules/`、`.claude/skills/`。
- Cursor：`.cursor/rules/`、`.cursor/skills/`。
- Trae：`.trae/rules/`、`.trae/skills/`。
- Qoder：`.qoder/rules/`、`.qoder/skills/`。
- OpenCode：`opencode.jsonc` 与 `.opencode/agents/`，公共规则通过生成的入口文档引用。

首版统一使用生成副本，不创建符号链接。每个生成文件都带来源标记；根目录生成清单仅记录 Claude Code、Cursor、Trae、Qoder 和 OpenCode 的目标路径、源路径和 SHA-256 摘要。`ybs tools sync --check` 比较清单与实际内容，必须检测缺失、漂移和意外新增文件。

上述五种工具的生成目录不是事实源，可以删除后重建；根 `AGENTS.md` 和 `.agents/` 不属于生成目录。手工修改生成文件不会反向覆盖 `.agents/`，下次同步会明确报告漂移并要求使用者选择覆盖或先迁移改动。

## 13. 错误处理与安全

### 13.1 配置错误

Pydantic 返回字段路径、收到的值和约束说明。任何配置错误都会在执行写操作前终止。

### 13.2 非法状态迁移

CLI 返回当前阶段、目标阶段、缺失证据和合法后继阶段；原状态保持不变。

### 13.3 文件安全

- 所有路径在解析后必须位于仓库根目录内。
- 写入通过同目录临时文件、刷新和原子替换完成。
- 任务级锁包含进程、主机和时间；只有确认锁已过期后才能恢复。
- 删除和归档先校验精确任务目录，不接受仓库根目录、通配符或未解析变量。

### 13.4 外部适配器失败

适配器具有超时和有限重试。外部失败记录为 `pending` 或 `failed`，不能伪装成成功，也不能破坏核心任务状态。重新同步必须幂等。

### 13.5 凭据与日志

- 凭据只通过环境变量传入。
- 配置只保存环境变量名称。
- 日志、异常和 `--json` 输出统一脱敏。
- 测试必须覆盖常见令牌、Authorization Header 和查询参数泄漏。

### 13.6 Git 安全

CLI 可以读取状态、校验提交范围和验证提交信息，但不自动执行强制推送、重置、清理或删除分支。提交和推送由使用者执行。

## 14. 测试与 CI

### 14.1 单元测试

覆盖配置模型、依赖环、路由评分、状态迁移、原子写入、锁恢复、路径边界和脱敏。

### 14.2 契约测试

覆盖六种 AI 工具的目标路径、来源标记、内容摘要、漂移检测和重复同步；覆盖四种 Mock 外部适配器的统一请求与结果结构。

### 14.3 集成测试

在 pytest 临时目录中创建真实 Git 仓库，验证 CLI、状态文件、文档模板、子模块注册和归档行为。两个示例子模块以提交到主仓的 Git Bundle 作为离线来源；`ybs demo bootstrap` 在 `.demo/remotes/` 中恢复仓库并配置本地 submodule URL，因此新机器和 CI 都不依赖网络。

### 14.4 端到端测试

仅保留一条完整的 `DEMO-101` 链路。测试先验证 API 的精确响应，再把真实响应交给 `demo-web` 的渲染函数，并断言成功文本；随后注入无效响应并断言降级文本。流程必须从空的任务状态开始，最终产生：

- 已归档任务目录。
- 完整 `status.yaml` 和 `memory.md`。
- SRS/TDD 文件。
- 路由解释和验证证据。
- 六工具同步结果。
- Mock 工单、CI 和通知记录。
- Git 提交 SHA 证据。

`demo-api` 使用 Python 标准库实现最小 HTTP 服务；`demo-web` 使用无第三方依赖的 HTML、JavaScript 和 Node 内置测试运行器。`ybs doctor` 因此同时检查 Python、Git 和 Node 是否可用。

### 14.5 CI 顺序

```text
Ruff
-> 配置与 Schema 校验
-> pytest 单元/契约/集成测试
-> DEMO-101 smoke
```

任何一步失败都阻止合并。

## 15. 三周教学路线

### 第 1 周：平台骨架

- D1：创建仓库、Python 环境和最小 CLI。
- D2：统一协议与目录边界。
- D3：Pydantic 配置模型与 Schema。
- D4：项目注册、依赖图与示例子模块。
- D5：功能路由引擎与范围建议。

### 第 2 周：任务闭环

- D6：状态机与合法阶段迁移。
- D7：任务启动、记忆与恢复。
- D8：SRS/TDD 模板与文档门禁。
- D9：验证证据、人工确认和归档。
- D10：原子写入、锁、退出码和脱敏。

### 第 3 周：集成与演示

- D11：六种 AI 工具规则生成器。
- D12：工单、Wiki、CI 和通知 Mock 适配器。
- D13：CI 门禁与反向故障测试。
- D14：跑通 `DEMO-101` 端到端任务。
- D15：README、演示脚本和复盘。

每天使用同一学习循环：20 分钟理解设计，50 分钟指挥 AI，60 分钟审阅与验证，20 分钟记录复盘。

## 16. 从演示版升级到团队版

演示版验证完成后，按以下顺序升级：

1. 将 Mock Issue 适配器替换为禅道或 Jira 沙箱适配器。
2. 将 Mock CI 适配器替换为 Jenkins 或 GitLab CI 适配器。
3. 接入企业密钥管理、OIDC/LDAP 和审计日志。
4. 增加 Windows 支持和真实多开发者并发测试。
5. 增加度量采集与只读管理看板。
6. 经过团队试点后，再考虑中央调度服务。

升级过程中保持协议、配置模型和适配器接口稳定，不把外部系统细节写入核心工作流。

## 17. 设计决策摘要

- 采用仓库型平台，不建设中央服务。
- 使用 Python CLI，不使用纯 Shell 实现复杂逻辑。
- 采用 Pydantic 类型模型并导出 JSON Schema。
- 使用结构化 `status.yaml` 作为机器任务状态，`memory.md` 只保存叙述性证据。
- 保留人工范围、方案和最终确认门禁。
- 首版只使用 Mock 外部系统。
- 首版支持 macOS/Linux，暂不承诺原生 Windows。
- 测试优先保证状态、边界、安全和端到端闭环，而不是追求无意义的覆盖率数字。
