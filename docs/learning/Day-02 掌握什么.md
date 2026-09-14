# Day-02 掌握什么

> 阶段名称：安全路径、原子写入、任务锁与敏感信息脱敏
> 项目：`ybs-workspace-lab`
> 阶段分支：`feat/day-02-safety-boundary`
> Day 1 基线：`2ad8396def0cbcae838f066eb0aff478a56c1e52`
> Day 2 最终实现：`9f2ea4c4d483f8b7b181fcd572150f6a2d5cb0fa`
> 结论日期：2026-09-14
> 下一阶段：Day-03 — 严格配置模型与 JSON Schema（本文只记录 Day 2，不开始 Day 3）

## 阶段目标

Day 2 的目标不是增加一个可见的业务命令，而是在任何状态、清单、Schema 或 Mock 记录真正落盘前，先建立一条统一的“写前安全边界”。这条边界回答四个问题：

1. 要写的路径真的仍在工作区内吗？
2. 写入中断时，正式文件会不会变成半份内容？
3. 两个 AI 或进程会不会同时修改同一个任务？
4. 输出、日志或错误对象里会不会残留令牌、密码等敏感信息？

最终公开了四个接口：

```python
resolve_inside(root: Path, candidate: str | Path) -> Path
atomic_write(path: Path, content: bytes) -> None
task_lock(root: Path, task_id: str) -> ContextManager[None]
redact(value: object, secrets: Sequence[str] = ()) -> object
```

这些接口会被后续所有持久化功能复用。因此 Day 2 必须早于状态机、配置写入、工具投影和适配器记录；否则后续功能会在没有共同安全边界的情况下各自读写文件。

## 本阶段完成的成果

### 工程成果

1. 新增 `resolve_inside()`，在解析真实路径后证明目标位于工作区内，拒绝父目录逃逸、符号链接逃逸和解析异常。
2. 新增 `atomic_write()`，通过同目录唯一临时文件、完整写入、刷新、`fsync` 和原子替换保护正式文件。
3. 新增 `task_lock()`，实现任务 ID 校验、独占锁创建、保守的失效锁恢复、并发恢复互斥和有所有权验证的释放。
4. 新增 `redact()`，递归处理结构化数据、敏感键、显式 secret 和 URL 查询参数。
5. 将 `YbsError` 的说明从“操作失败”扩展为“面向使用者的稳定失败”，保留 `(message, code)` 接口。
6. 建立 40 个 Day 2 测试用例；与 Day 1 的 2 个集成测试合计为 42 项。
7. 经两轮实现期安全返修后，无上下文复建审计又发现“不可用锁记录可能泄漏 Python 原始异常”，并形成第三次安全返修。
8. 最终实现 `9f2ea4c` 经独立复审，规格和代码质量/安全结论均为 `Approved`，Critical、Important、Minor 均为 0。
9. Day 2 没有新增依赖，没有修改 `pyproject.toml` 或 `uv.lock`，没有创建 Day 3 文件。

### 知识成果

使用者已经能够在“支配 AI 实现并审查结果”的目标层级上判断：

- 路径安全必须比较解析后的目录关系，不能做字符串前缀判断；
- 原子写保护的是“旧正式文件或完整新文件”，不是保证所有步骤都不会失败；
- 任务锁的职责是互斥和保守失败，不是任务排队器；
- 只有经过有效元数据、同主机和明确进程不存在三重证明的锁才可恢复；
- 锁记录若在解析或进程检查中出现无法判断所有者状态的异常，必须保守地不恢复：code `5`、不进入任务 body、锁原 bytes 不变；
- 恢复守卫防止遵守协议的并发进程交错执行，但不能被夸大成对所有恶意同用户进程的绝对防护；
- 脱敏要处理整个结构，而不只是日志中的 `message` 字段；
- 验收测试应优先固定可观察结果，不应无必要地锁死内部实现步骤。

本阶段实现与独立审阅已经确认：锁记录触发 JSON 递归上限、超长整数限制或系统调用整数溢出时，系统必须把它保守地视为不可恢复锁，不能泄漏 `RecursionError`、`ValueError` 或 `OverflowError`。使用者已经用自己的话准确复述这一保守合同。当前学习目标要求掌握可观察行为和判断原则，不要求背出三个 Python 异常类名或独立实现底层异常边界。

### 可复用资产

- 工作区内真实路径证明模式；
- 基于已打开目录描述符、`O_NOFOLLOW` 和 `dir_fd` 的安全文件操作模式；
- 同目录临时文件加原子替换的持久化模式；
- 保守失效锁恢复与每任务恢复守卫模式；
- 把不可信持久化数据在解析边界和系统调用边界统一归一化为稳定领域错误的模式；
- 结构化递归脱敏与最长 secret 优先替换模式；
- “测试先行 + 独立安全审阅 + 为审阅问题补回归测试”的交付模式。

## 必须掌握的核心概念

### 1. 写前安全边界

**它是什么？**

在业务状态被写入前，统一经过路径、写入、互斥和脱敏四类基础能力。业务模块不再自行拼路径、自行覆盖文件、自行判断锁或自行过滤秘密。

**它解决什么问题？**

如果每个后续模块各写一套安全逻辑，规则会漂移：一个模块防住 `..`，另一个忘记符号链接；一个模块使用临时文件，另一个直接覆盖；一个模块脱敏 token，另一个把 token 写进异常。

**为什么放在 Day 2？**

Day 1 只有只读根定位和 CLI 骨架。Day 3 起将出现配置、Schema、状态、工具投影和 Mock 记录等持久化数据，所以在第一次业务写入前建立边界最合适。

**如果没有它会怎样？**

后续即使业务测试通过，也可能把内容写出工作区、留下半文件、并发覆盖任务或泄漏凭据。

### 2. 解析后的路径包含关系

**它是什么？**

`resolve_inside(root, candidate)` 先解析工作区根和候选路径，再用 `Path.relative_to(resolved_root)` 证明候选路径属于根目录树。

**它解决什么问题？**

字符串前缀并不表示目录包含。例如 `/workspace/ybs-backup` 以 `/workspace/ybs` 开头，却不是其子目录。符号链接的文本路径看似在根内，真实目标也可能在根外。

**精确规则是什么？**

- 相对候选路径以解析后的 `root` 为基准；
- 绝对候选路径按其自身解析；
- 解析后能对根执行 `relative_to` 才接受；
- `..` 不是一律禁止：归一化后仍在根内就允许；
- 父目录逃逸、符号链接逃逸和符号链接循环都以 `YbsError(code=5)` 失败。

**如果只检查字符串会怎样？**

前缀相似目录会被误收，`..` 和 symlink 也可能绕过表面检查。

### 3. 原子写入

**它是什么？**

`atomic_write(path, content)` 不直接清空正式文件，而是在正式文件所在目录创建本次调用独占的临时文件，写完并持久化后再替换正式文件。

**完整链路是什么？**

```text
确认目标父目录存在
  -> 不跟随符号链接地逐级打开父目录
  -> 在已打开目录中独占创建同目录唯一临时文件
  -> 写完全部 bytes
  -> flush
  -> fsync 临时文件
  -> 在同一个已打开目录内 os.replace
  -> 关闭描述符
```

**为什么临时文件必须在同一目录？**

同目录替换才能使用稳定的目录对象并获得所需的原子替换语义，也避免跨文件系统移动失败。

**失败时怎样处理？**

- 正式旧文件保持原内容；
- 只清理本次调用创建、且设备号/ inode 仍匹配的那个临时文件；
- 不使用通配符，不删除其他进程的临时文件；
- 抛出 `YbsError(code=5)`。

### 4. 目录描述符绑定与 TOCTOU

**它是什么？**

TOCTOU 是“检查时”和“使用时”之间路径被替换的竞态。Day 2 不只在开始时调用 `resolve()`，还把后续写入绑定到已经打开的目录描述符。

**实现边界是什么？**

- 目录逐级以 `O_DIRECTORY | O_NOFOLLOW` 打开；
- 文件以相对 `dir_fd` 的方式打开、读取、替换或删除；
- 已打开根目录要与构造锁时记录的设备号和 inode 一致；
- 路径名被重命名或改成 symlink 后，操作仍指向已打开的原目录对象，或保守失败。

**为什么第一版只做路径解析还不够？**

第一轮安全审阅指出：通过检查后、真正写入前，目录路径仍可能被换成指向外部的符号链接。描述符绑定把检查对象和使用对象连接起来。

### 5. 任务锁与保守失效锁恢复

**它是什么？**

`task_lock(root, task_id)` 是一个上下文管理器。它在 `.ybs/locks/<task-id>.lock` 建立任务级互斥，并在离开上下文时尝试释放自己拥有的锁。

**任务 ID 规则是什么？**

必须匹配：

```text
^[A-Z][A-Z0-9-]{1,63}$
```

不合法 ID 在构造路径前以 code `2` 拒绝，且不能创建 `.ybs/`。

**锁中有什么？**

紧凑 JSON，且键恰好为：

```json
{"pid":12345,"host":"host-name","created_at":"2026-09-14T00:00:00+00:00"}
```

`created_at` 必须是带时区的 UTC ISO-8601 时间。锁文件以独占创建并 `fsync`。

**什么时候可以恢复旧锁？**

只有全部成立时：

1. JSON 结构和三个字段有效；
2. `host` 等于当前主机；
3. `os.kill(pid, 0)` 明确抛出 `ProcessLookupError`；
4. 进入恢复守卫后再次读取，锁的字节、设备号和 inode 仍与观察值一致。

活跃进程、`PermissionError`、其他 `OSError`、远程主机、错误 JSON、深层递归 JSON、超长 JSON 整数、超出系统调用整数范围的 PID 和无效时间戳都不能自动恢复。

锁文件是不可信输入，两个边界都必须保守归一化：

- `json.loads` 产生的 `ValueError`、`RecursionError`，以及解码/读取异常，都表示记录不可用；
- `os.kill(pid, 0)` 产生的 `OverflowError` 表示 PID 不能安全用于存活检查，不是进程死亡证据。

这些情况最终都表现为 `YbsError(code=5)`、不进入任务 body、锁原始字节保持不变。普通坏 JSON、2,000 层嵌套数组、5,000 位正整数 PID 和 `10**100` PID 在一个行为测试中逐案执行，所以测试收集数仍是 24 个 filesystem、40 个 Day 2。

### 6. 恢复守卫与所有权释放

**恢复守卫解决什么问题？**

两个进程可能同时看见同一个死锁，并都认为自己有权删除。每任务的 `.DEMO-101.lock.recovery` 文件配合非阻塞 `flock(LOCK_EX | LOCK_NB)`，把“复查—删除—独占重建”串成一个只允许一个遵守协议的进程进入的区间。

**守卫覆盖哪些删除？**

- 失效锁删除；
- 创建锁失败后的本进程清理；
- 正常离开上下文时的本进程锁释放。

守卫文件可以保留复用；进程关闭文件描述符后，`flock` 自动释放。

**释放为什么还要核对？**

离开上下文时，路径处的锁可能已经被替换。只有锁字节仍等于当前上下文的 owner bytes，并且设备号/inode 仍一致，才允许删除。自己拥有的锁删除失败必须暴露为 `YbsError(code=5)`，不能假装释放成功。

**能力边界是什么？**

这套协议防御遵守协议的并发进程和目录 rename/symlink 替换。`stat` 与 `unlink` 仍是两个系统调用，不声称能抵御一个绕过守卫、恰好在二者之间替换最终目录项的恶意同用户进程。

### 7. 结构化敏感信息脱敏

**它是什么？**

`redact(value, secrets=())` 接收任意原始值，返回适合安全展示的副本或值。

**固定敏感键是什么？**

键名要完整匹配且不区分大小写：

```text
authorization|token|secret|password|api[_-]?key
```

敏感键对应的整个值替换成 `***REDACTED***`。`x-authorization-note` 不属于完整匹配，不会仅因包含单词而整值替换。

**显式 secrets 怎样处理？**

- 空字符串忽略，否则空串会在每个字符间匹配；
- 去重；
- 按长度从长到短替换，避免先替换短前缀或后缀后泄漏剩余部分；
- 字符串值和字符串键中都替换。

**结构和 URL 怎样处理？**

- 递归处理 mapping、list 和 tuple；
- list 与 tuple 类型形状保持；
- 非字符串标量原样通过；
- URL 查询参数被解析并重建，敏感参数整值替换，非敏感参数保留诊断价值；
- URL 编码后的标记字符表现可以不同，只要无秘密残留；
- 畸形 URL 无法解析时退化为字面 secret 替换，而不是泄漏或抛原始异常。

### 8. 稳定错误码与上下文管理器

Day 2 延续 Day 1 的 `YbsError(message, code)`：

- code `2`：调用输入有误，本阶段是非法 task ID；
- code `5`：路径、写入、锁争用、锁恢复不确定、锁释放等操作/安全失败。

`with task_lock(...):` 的精确语义是：

```text
进入 with 前尝试获取锁
  -> 获取失败：不进入任务操作体，抛 code 5
  -> 获取成功：在锁保护下执行任务操作
  -> 离开 with：无论操作体成功或抛错，都尝试释放自己拥有的锁
  -> 释放失败：暴露 code 5
```

它不是“无论如何都会进入任务体”，也不是排队调度器。

### 9. TDD 与独立安全审阅

测试不仅证明正常结果，还要证明失败不会破坏旧数据、删除别人的文件、偷走活锁或残留秘密。独立审阅的价值在 Day 2 得到了直接证据：首个实现虽然 29 项累计测试已通过，仍被找到 2 个 Critical 和 2 个 Important 问题；第一轮修复后，又发现 2 个 Important 和一个无效的并发测试钩子。只有把审阅发现先转成能失败的回归测试，再做最小修复，才把风险变成长期可执行的资产。

## 完整执行链路

### 安全解析一条候选路径

```text
调用 resolve_inside(root, candidate)
  -> root.resolve()
  -> 相对 candidate 拼到 resolved_root；绝对 candidate 保持绝对
  -> candidate.resolve()
  -> candidate.relative_to(resolved_root)
  -> 成功：返回真实 Path
  -> 失败/解析异常：YbsError(code=5)
```

### 原子写入一份状态文件

```text
调用 atomic_write(path, content)
  -> 提取合法目标文件名
  -> O_NOFOLLOW 逐级打开已有父目录
  -> 在该目录独占创建唯一临时文件（0600）
  -> 记录临时文件设备号/inode
  -> 写完 bytes、flush、fsync、关闭
  -> 通过同一 dir_fd 原子替换正式文件
  -> 成功：返回 None
  -> 失败：只尝试删除身份仍匹配的本次临时文件，保留旧正式文件，code 5
```

### 获取、恢复和释放任务锁

```text
调用 task_lock(root, task_id)
  -> 先校验 ID；非法则 code 2 且不建目录
  -> 解析根并记录设备号/inode
  -> 进入 with 时重新以 no-follow 打开根并核对身份
  -> 相对根打开或创建 .ybs/locks
  -> 生成 pid/host/UTC created_at owner bytes
  -> 独占创建并 fsync 锁
     -> 成功：进入任务操作体
     -> 已存在：尝试非阻塞获取每任务恢复守卫
        -> 守卫失败：code 5
        -> 守卫成功：复查有效、同主机、PID 确认死亡、记录未变化
           -> 证据不足：code 5，旧锁不变
           -> 证据充分：删精确旧 inode，独占创建新锁，进入任务体
  -> 离开任务体时获取同一恢复守卫
  -> 核对 owner bytes 与设备号/inode
  -> 只删除仍属于自己的锁；失败按合同暴露
```

### 脱敏一份嵌套结果

```text
调用 redact(value, secrets)
  -> 丢弃空 secret、去重、按长度降序
  -> mapping：脱敏字符串键；敏感完整键的值整块替换；其他值递归
  -> list/tuple：逐项递归并保持容器形状
  -> str：解析 URL 查询参数并脱敏；不可解析时做字面替换
  -> 其他标量：原样返回
  -> 返回不含规定秘密的安全结果
```

## 关键文件地图

| 文件 | 职责 | 主要输入 | 主要输出 | 被谁调用 | 依赖 |
| --- | --- | --- | --- | --- | --- |
| `src/ybs_cli/errors.py` | 保存面向使用者的稳定错误消息和退出码 | `message`、`code` | `YbsError` | filesystem、CLI 与后续领域模块 | Python |
| `src/ybs_cli/filesystem.py` | 路径包含证明、原子写、任务锁及安全文件系统帮助函数 | 根目录、候选路径、目标 bytes、task ID | `Path`、`None` 或 code 2/5 错误 | 后续所有持久化模块 | `pathlib`、`os`、`fcntl`、JSON、主机/进程信息 |
| `src/ybs_cli/redaction.py` | 对结构化值、敏感键、显式 secrets 和 URL 查询做脱敏 | 任意值、secret 序列 | 安全展示值 | 日志、错误、Mock 记录及后续输出层 | `re`、`urllib.parse` |
| `tests/unit/test_filesystem.py` | 以真实临时文件系统验证 24 个路径/写入/锁场景 | `tmp_path`、受控故障和并发 | pytest 断言 | pytest、审阅者 | 真实文件系统；有限 monkeypatch |
| `tests/unit/test_redaction.py` | 以 16 个收集用例验证脱敏输出和无残留秘密 | 嵌套值、URL、显式 secrets | pytest 断言 | pytest、审阅者 | JSON、URL 解析 |
| `docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md` | 给出 15 日计划、Day 2 原始接口与阶段边界 | 已审批设计 | Task 2 实施清单 | 人、AI、审阅流程 | 已审批设计 |
| `.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/task-2-brief.md` | 保存 Day 2 执行任务的聚焦版本 | 总计划 Task 2 | 文件、接口、TDD 和审阅焦点 | 实施者 | 总计划 |
| `.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/task-2-report.md` | 保存 RED/GREEN、两轮审阅修复、验收与提交证据 | 实施和审阅结果 | 可追溯阶段报告 | 资产化作者、审计者 | 实际命令和 Git 历史 |
| `.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/progress.md` | 保存阶段裁决和已关闭范围 | 计划、实现、审阅 | 决策账本 | 后续阶段 | SDD 流程 |

## 关键命令与结果

每次运行 `uv` 前都使用项目内持久化目录：

```sh
export PROJECT_ROOT="$PWD"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
export TMPDIR="$PROJECT_ROOT/.demo/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
```

最终审计复跑前已预先创建被 `.gitignore` 覆盖的 `.demo/tmp`。`TMPDIR`、`TMP`、`TEMP` 使 pytest 的 `tmp_path` 也落在隔离仓库中；它们是无上下文审计发现执行偏差后固化的隔离要求。

| 命令 | 作用 | 2026-09-14 复验结果 | 成功判断 |
| --- | --- | --- | --- |
| `uv --version` | 确认工具版本 | `uv 0.10.7` | 命令可用 |
| `uv run python --version` | 确认项目 Python | `Python 3.11.14` | 满足 `>=3.11` |
| `uv run pytest tests/unit/test_filesystem.py::test_task_lock_never_recovers_unavailable_lock_records -q` | 聚焦四种不可用锁记录 | `1 passed in 0.03s`；测试内部逐案运行 4 轮 | 全部返回 code 5、锁不变 |
| `uv run pytest tests/unit/test_filesystem.py tests/unit/test_redaction.py -q` | 运行 Day 2 专项测试 | `40 passed in 0.05s` | 40 项全部通过，无 skip/xfail |
| `uv run pytest -q` | 运行累计测试 | `42 passed in 0.41s` | Day 1 的 2 项与 Day 2 的 40 项均通过 |
| `uv run ruff check .` | 静态检查仓库适用文件 | `All checks passed!` | exit `0` |
| `uv run ruff format --check src tests` | 检查全部 Python 源码与测试格式 | `10 files already formatted` | exit `0` |
| `git diff --check 2ad8396..HEAD` | 检查 Day 2 提交差异的空白错误 | 无输出，exit `0` | 差异无空白错误 |

运行环境实证为 `Darwin 25.5.0 arm64`。Day 2 没有更改依赖或锁文件。

`uv run ruff format --check .` 在 Ruff 0.16.7 下不是本阶段有效格式门禁：它会尝试格式化已审批计划 Markdown 中的 Python fenced code，并且在未改动的 Day 1 基线 `2ad8396` 上也失败。正确处理是保留审批计划字节不变，继续执行 `ruff check .`，将格式门禁限定为 `src tests`；不能为了让工具变绿而修改哈希固定的审批输入。

## 测试驱动记录

### 1. 接口缺失 RED

测试先于模块创建：

- `tests/unit/test_filesystem.py` 首次收集时报 `ModuleNotFoundError: No module named 'ybs_cli.filesystem'`，exit `2`；
- `tests/unit/test_redaction.py` 首次收集时报 `ModuleNotFoundError: No module named 'ybs_cli.redaction'`，exit `2`。

这只能称为**接口缺失 RED**：它证明模块和接口尚不存在，但没有证明某个已运行的行为断言失败。

### 2. 脱敏行为 RED

为 `redact()` 建立只有签名、直接 `return value` 的 identity stub 后，测试能够正常收集，结果为 `11 failed, 1 passed`。失败输出显示 `abc123`、`top-secret` 等仍出现在结果中。这才是“接口存在但行为不满足合同”的行为 RED。

### 3. 初始 GREEN 与自审回归

- 最初的路径、写入、锁和脱敏实现达到 Day 2 专项 `24 passed`；
- 自审先写无效锁时间戳测试，得到 `1 failed, 12 passed`，修复后通过；
- 畸形 URL 用例先暴露 `ValueError: Invalid IPv6 URL`，修复为字面 secret 替换；
- 符号链接循环先泄漏 `RuntimeError`，修复为 `YbsError(code=5)`；
- 自审结束为 Day 2 专项 `27 passed`、累计 `29 passed`。

### 4. 第一轮独立安全审阅：2 Critical + 2 Important

首个实现已经通过当时全部测试，但独立审阅仍发现：

1. **Critical：并发恢复同一失效锁。** 两个竞争者可能同时判断旧进程死亡、同时删除并进入临界区。
2. **Critical：路径检查与使用之间的 TOCTOU。** 路径通过检查后，父目录或 `.ybs` 仍可能被替换成外部 symlink。
3. **Important：hostname/fstat 异常清理。** 原始 `OSError` 可能泄漏，文件描述符或无法证明身份的锁处理不够保守。
4. **Important：重叠 secrets。** 先替换短 secret 会留下长 secret 的剩余片段。

每项都先增加回归测试并观察失败。第一轮返修加入：

- 描述符相对且 no-follow 的目录/文件操作；
- 每任务非阻塞恢复守卫；
- 统一异常映射和描述符清理；
- secrets 去重并最长优先。

返修后为 Day 2 专项 `36 passed`、累计 `38 passed`。

### 5. 第二轮独立安全审阅：2 Important + 测试有效性问题

重新审阅又发现：

1. 自己拥有的锁在释放时 `unlink` 失败被吞掉，调用方可能误以为任务已解锁；
2. 打开子目录后关闭父目录描述符失败时，子目录描述符可能泄漏；
3. 并发测试仍 hook 旧的 `Path.read_bytes`/`Path.unlink`，而生产代码已改为描述符相对的 `os` 调用，测试并没有真正同步到恢复守卫；
4. 需要让所有遵守协议的删除路径都经过同一恢复守卫，并明确威胁模型。

第二轮返修先通过 RED 证明这些问题存在，再完成：

- 所有权锁释放失败变成可观察 code `5`；
- 父描述符关闭失败时也关闭已打开的子描述符；
- 并发测试同步点移到真实 `fcntl.flock` 调用，并连续运行 5 次；
- 失效锁删除、失败创建清理和正常释放统一走恢复守卫；
- 写明对恶意同用户绕过协议者的残余非目标。

第二轮返修结束时为 Day 2 专项 `40 passed`、累计 `42 passed`，对应提交 `9422739`；此时测试数量已经达到最终口径，但后续资产化复建审计仍发现了未覆盖的输入异常边界。

### 6. 第三次安全返修：无上下文复建审计发现不可用锁记录

首轮无上下文复建审计在独立实现审阅中主动测试了不可信锁记录的极端输入，并暴露三种 Python 原始异常：

1. owner JSON 已成功解析，但 `pid = 10**100` 传给 `os.kill(pid, 0)` 时，真实泄漏 `OverflowError: Python int too large to convert to C long`；
2. 2,000 层嵌套 JSON 数组在 `json.loads` 时，真实泄漏 `RecursionError: maximum recursion depth exceeded while decoding a JSON array`；
3. 独立复审继续手工构造 5,000 位正整数 PID，`json.loads` 在 Python 整数 4,300 位限制处先泄漏 `ValueError: Exceeds the limit (4300 digits)...`。

这三种输入都不是“可以恢复的死锁”，也不应把解释器异常暴露给调用方。返修先保留每个真实 RED，再将原来的普通坏 JSON 测试扩展为一个循环行为测试，在同一项 pytest 收集中依次检查：

- 2,000 层深层 JSON；
- 普通非 JSON bytes；
- 含 5,000 位正整数 PID 的手工 JSON；
- 能被 JSON 解析、但不能传给底层进程检查的 `10**100` PID。

最终实现：

- 在 `json.loads` 边界保守处理 `ValueError` 与 `RecursionError`；
- 在 `os.kill(pid, 0)` 边界保守处理 `OverflowError`；
- 四种记录均转换为 `YbsError(code=5)`，不进入任务 body，锁原字节不变；
- 一个测试函数内部运行四轮，filesystem 仍收集 24 项，Day 2 仍收集 40 项，累计仍为 42 项。

原工作树安全返修提交为 `9f2ea4c4d483f8b7b181fcd572150f6a2d5cb0fa`，父提交为 `9422739e2c323789eab2968b4954540717f71d6c`，只修改 `src/ybs_cli/filesystem.py` 与 `tests/unit/test_filesystem.py`。最终控制端复验为：聚焦不可用锁记录 `1 passed in 0.03s`、Day 2 `40 passed in 0.05s`、累计 `42 passed in 0.41s`、Ruff 通过、10 个 Python 文件格式检查通过、diff check 通过。独立复审最终为 `Approved`，Critical、Important、Minor 均为 0。

### 7. 首轮无上下文复建审计与隔离偏差

审计者只收到规格快照 `/private/tmp/ybs-day2-rebuild-audit.B68knb/Day-02-reconstruction-spec.md`，其 SHA-256 为 `5d220e05fefbff71da2a6a662a069d2dc4a499be128cb7fa12c2488b38dd6f4a`；初始仓库是干净的 `main@2ad8396`，15 个文件和两份审批输入哈希均匹配。审计者没有读取原实现、学习笔记、旧报告或聊天记录。

临时复建仓库是可复验的原始现场，但不是唯一持久证据。`docs/specs/Day-02 复现规格.md` 第 16 节保存了审计输入、TDD、提交边界、执行偏差、返修回灌和最终规格一致性结论，并将随本阶段资产提交长期保留。

审计真实得到两个 `ModuleNotFoundError` interface-missing RED、identity stub 的 `11 failed, 1 passed` 和安全回归非绿，并在独立实现审阅中发现超大 PID/深层 JSON 问题。修复并复审后：

- 重建提交为 `a5b47321ec6b16d3f0fadcb6e46a9125b2fb8739`，父严格为 `2ad8396`；
- 基线后恰有一个提交，只含五个规定文件，模式均为 `100644`，subject/trailers 符合规格，工作树干净；
- Day 2 `40 passed in 0.06s`、累计 `42 passed in 0.19s`，Ruff、10 文件格式、diff 与依赖检查通过；
- 并发测试预建可复用 recovery guard，真实到达 `flock` 并产生一胜一败；
- 未出现阻止安全复建的规格歧义，私有代码结构允许不同。

必须保留一项执行偏差：审计前几轮 pytest 的 `tmp_path` 使用系统默认 `/private/var/.../T/pytest-of-jichengye`；产品文件、Git 和 uv 状态始终隔离，最终复跑才把 `TMPDIR`、`TMP`、`TEMP` 固定到仓库内 `.demo/tmp`。因此可以说功能、提交和源仓隔离复建通过，但不能说全过程每一个 pytest 临时文件都位于仓库内。

该审计使用的是补充不可用锁合同前的规格快照。审计者通过独立代码审阅主动补齐了缺口；当前文档已经把新合同写明，但当前字节版本仍需要控制端执行一次只读一致性复审。

### 8. 为什么保留失败记录

这些失败不是需要从文档里隐藏的“过程噪音”。它们证明三件事：

- 测试通过只代表覆盖到的合同通过，不代表安全设计自动完整；
- 审阅意见只有转化成真实 RED 回归测试，才会成为以后可重复执行的保护；
- 测试本身也可能写错钩子，必须证明故障注入或并发同步真正触达当前生产路径。
- 不可信数据不仅可能“不符合 Schema”，还可能让标准库在解析或系统调用边界抛出 `ValueError`、`RecursionError`、`OverflowError`；这些异常也必须进入稳定错误合同。

## 过关标准

Day 2 的学习目标不是默写 368 行文件系统实现，而是能够支配 AI 完成并审查以下事项：

- 能判断前缀目录、父目录归一化、symlink 和不逃逸 `..` 四类路径；
- 能解释原子写为何使用同目录唯一临时文件，以及失败时能删什么、不能删什么；
- 能区分活锁、确认死亡的本机锁、权限不明锁、远程锁和损坏锁；
- 能说明恢复守卫防止的是“遵守协议的进程交错”，不是让每一步永远成功；
- 能说明释放锁前为什么同时核对 owner bytes 与设备号/inode；
- 能解释 task lock 是 fail-fast 互斥，不是任务调度队列；
- 能定义脱敏的可观察结果：固定输出结构、没有残余 secret，而不是无必要地规定内部循环；
- 能读懂四个公开签名的输入、成功输出、失败方式和副作用边界；
- 能要求 AI 先写安全回归测试，再写最终加固实现，并独立复审；
- 能用 40/42 测试、Ruff、diff、提交范围和错误码证据判断阶段是否完成。

## 过关问题、使用者回答与准确解释

### 1. 为什么先调整教学顺序？

**使用者反馈**

冷启动五题测验被拒绝，因为概念尚未讲授，且当前目标不是从 Python 代码中自行推导陌生概念。

**判断与调整**

反馈合理。教学顺序调整为：**场景 → 风险 → 解决方案 → 测试 → 可选代码映射 → Teach-back**。这符合“会支配 AI、重点理解合同和证据”的目标，不把陌生语法当作先修门槛。

### 2. 字符串前缀陷阱

**题目**

根是 `/workspace/ybs`，候选是 `/workspace/ybs-backup/report.json`，应接受吗？

**使用者回答**

拒绝，因为 `ybs-backup` 不是允许的 `ybs` 工作区。

**判断**

正确。目录包含要靠解析后的路径组件关系证明，不能用字符串 `startswith`。

### 3. 父目录逃逸

**题目**

`/workspace/ybs/tasks/../../private/token.txt` 解析到哪里，是否允许？

**使用者回答**

解析为 `/workspace/private/token.txt`，应拒绝。

**判断**

正确。归一化结果已经离开 `/workspace/ybs`。

### 4. 符号链接逃逸

**题目**

工作区中的 `latest -> /shared/releases`，访问 `latest/result.json` 的真实结果是什么？

**使用者回答**

真实结果是 `/shared/releases/result.json`，应拒绝。

**判断**

正确。安全判断必须发生在 symlink 解析后。

### 5. 不逃逸的 `..`

**题目**

`/workspace/ybs/tasks/../status.yaml` 是否允许？

**使用者回答**

允许，因为解析为 `/workspace/ybs/status.yaml`，仍在工作区中。

**判断**

正确。规则不是“看到任何 `..` 就拒绝”，而是“解析后的真实路径不得离开根”。

### 6. 原子写中断时正式文件应怎样？

**使用者回答**

正式文件保留旧状态。

**判断**

正确。失败结果应是完整旧文件，而不是半份新文件。

### 7. 请复述原子写流程

**使用者回答**

创建临时文件 → 写临时文件 → 替换旧文件。

**补充**

核心正确；完整合同还包括：临时文件位于同一目录且名字唯一，写完后 `flush` 和 `fsync`，替换使用同一已打开目录，失败只清理本次精确临时文件并返回 code `5`。

### 8. 两个 AI 同时写时，A 能清理哪些临时文件？

**使用者回答**

A 只能删自己创建的 `.status.A.tmp`；删除全部 `.tmp` 会影响 AI-B。

**判断**

正确。清理规则必须基于本次操作拥有的精确名字和身份，不能通配。

### 9. AI-A 持有活锁时 AI-B 怎么办？

**使用者回答**

最初提出让 AI-B 排队等待 AI-A。

**纠正**

互斥判断正确，但 Day 2 的 `task_lock` 只负责 fail-fast：AI-B 立即收到 code `5`，不能进入任务体，不能删除或修改活锁。排队、重试和调度属于未来编排层，不在这个锁原语中。

### 10. 本机锁的进程已确认死亡时怎么办？

**使用者回答**

删除旧锁，创建 AI-B 的新锁。

**补充**

方向正确。真实实现顺序是：取得恢复守卫 → 第一次读取并解析锁记录 → 校验元数据与同主机，并调用一次 `os.kill(pid, 0)` 检查 PID → 第二次读取并比较 bytes 与设备号/inode → 删除精确旧 inode → 独占创建并持久化新锁。第二次读取用于确认锁记录未被替换，不会再次调用 `os.kill`。

### 11. 检查进程时出现 `PermissionError` 怎么办？

**使用者回答**

不能恢复，因为无法确认进程是否仍在运行。

**判断**

正确。只有 `ProcessLookupError` 是明确死亡证据；权限不足不是死亡证据。

### 12. 恢复守卫保证什么？

**使用者第一次回答**

保证每一步都执行。

**纠正与再次复述**

守卫不保证系统调用成功，只阻止其他遵守协议的进程在同一把锁的检查、删除、重建期间插入操作。纠正后，使用者准确复述为：整个序列期间，不允许其他进程操作同一把锁。

### 13. 释放锁前为什么验证所有权？

**使用者回答**

AI-A 必须确认锁仍属于 A；否则不能删除，以免删掉另一个进程的锁。

**判断**

正确。最终实现同时比较 owner bytes 和设备号/inode。

### 14. 脱敏只过滤 `Message` 吗？

**使用者初始理解**

重点放在过滤 Message。

**纠正**

`redact()` 的输入是整个结构化值：敏感完整键的值要整体替换；其他字符串中的显式 secret 要做子串替换；列表、元组和嵌套 mapping 都要递归；字符串键本身也可能含显式 secret。

### 15. 为什么重叠 secret 要最长优先？

**使用者回答**

先替换短值会留下长值的后半部分，更容易被破解；应先替换最长值。

**判断**

正确。例如 secret 同时有 `top` 和 `top-secret` 时，先替换 `top` 会残留 `-secret`。

### 16. URL 脱敏后的逻辑结果是什么？

**使用者回答**

`https://api.example/run?token=***REDACTED***&mode=check`，保留非敏感诊断参数。

**判断与边界**

正确。URL 重建时 `*` 等字符可能被百分号编码，字节表现不是合同；token 不残留、`mode=check` 仍可诊断才是合同。

### 17. 原子写的 Given/When/Then 怎样更精确？

**使用者表述**

写入失败时“删除创建的新文件，保留原文件”。

**纠正**

应写成：删除**本次操作创建并仍能证明属于本次操作的精确临时文件**；保留其他进程的临时文件；正式旧文件内容不变；抛出 code `5`。不能把临时文件称作已经创建的“新正式文件”。

### 18. 活锁的 Given/When/Then 怎样更精确？

**使用者表述**

要求立即 code `5`，同时提到放入后续调度队列。

**纠正**

code `5` 正确。Day 2 可观察结果只包括：不删除、不修改活锁，不进入任务操作体并返回 code `5`；是否排队不是本模块合同。

### 19. 死锁恢复的 Given/When/Then 怎样更精确？

**使用者表述**

AI-B 创建自己的锁替换旧锁。

**补充**

必须包含恢复守卫、记录复查、确认仍为同一死亡所有者、删除精确旧文件、独占创建新锁，最后才进入任务体。

### 20. 脱敏验收应规定内部步骤吗？

**使用者初始表述**

规定了两步内部处理顺序。

**纠正与结论**

验收优先固定可观察结果：安全输出的结构和值，以及任何序列化结果都不含 secret。只要输出合同一致，循环替换或最长优先正则都可以。使用者正确判断：实现 B 若达到同样脱敏效果就应通过，不必锁死无必要内部步骤。

### 21. 如何读 `resolve_inside` 的签名？

**使用者回答**

输入根目录和候选路径，返回工作区内解析后的真实路径。

**补充**

正确。`-> Path` 只表示成功返回类型；候选越界或无法安全解析时，不返回 Path，而是抛 `YbsError(code=5)`。

### 22. 如何理解 `with task_lock(...)`？

**使用者回答**

进入时获取，执行任务，离开时释放，无论成功失败都释放。

**纠正**

应说“在锁保护下执行任务操作”。获取可能在进入 body 前失败；离开时总会**尝试**释放自己拥有的锁，但释放系统调用也可能失败并以 code `5` 暴露。

### 23. 如何读 `redact(value, secrets=()) -> object`？

**使用者第一次回答**

把 `value` 和替换值的含义说反了。

**纠正后的回答**

`value` 是要脱敏的原始数据，`secrets` 是需要替换的秘密列表或数据，结果是 `value` 的脱敏形式。

**判断**

纠正后准确。`***REDACTED***` 是模块内部固定标记，不由 `value` 参数提供。

### 24. 5,000 位 PID 导致解析或进程检查异常时怎么办？

**题目**

一份锁记录包含 5,000 位 PID，或者类似不可用记录在 JSON 解析、PID 存活检查阶段触发底层异常。系统能否把它当作死锁恢复？对锁文件、任务操作体和错误码分别应该怎样处理？

**使用者回答**

> 不能把这个锁文件当做死锁；要保留原锁，不能进行删除或修改；不让当前AI去操作任务区；抛出异常YbsError(code=5)；

**判断：通过**

回答准确覆盖了保守合同的四个可观察结果：证据不足时不能判定为死锁；原锁不删除、不修改；当前 AI 不进入任务 body；公开结果为 `YbsError(code=5)`。

5,000 位整数字面量可能在 `json.loads` 触发 `ValueError`，2,000 层 JSON 可能触发 `RecursionError`，能够解析但超出底层进程接口范围的 PID 可能在 `os.kill` 触发 `OverflowError`。这些是实现与排错时有用的底层表现；本阶段掌握标准是能坚持“无法确认死亡就保守拒绝”的合同，不要求使用者背异常名，也不据此声称已能独立编写 Python 异常处理代码。

## 常见误区

1. **用字符串前缀判断路径安全。** 目录名相似不等于目录包含。
2. **见到 `..` 就一律拒绝。** 应判断解析后的真实结果是否越界。
3. **只在写前 `resolve()` 一次就认为没有竞态。** 检查后路径仍可能被换；关键操作要绑定已打开目录。
4. **把原子写理解成“所有步骤不会失败”。** 它保证失败不会把半内容变成正式文件，并给出可恢复结果。
5. **失败时删除目录中所有 `.tmp`。** 这可能删除另一个进程的文件。
6. **把所有旧锁都当成死锁。** 远程、损坏、权限不明或时间无效都必须保守拒绝。
7. **把 `PermissionError` 当作进程不存在。** 它只说明当前进程无权确认。
8. **把任务锁当作队列。** 本原语只互斥、fail-fast 和安全恢复。
9. **只比较锁 JSON，不比较文件身份。** 同一路径可能已被换成另一文件。
10. **认为 recovery guard 让每一步必定成功。** 它只防止合作进程交错。
11. **先替换短 secret。** 会残留长 secret 的前缀或后缀信息。
12. **只脱敏字典值，不脱敏键和 URL 查询。** secret 仍可能出现在键、路径片段或非敏感参数值中。
13. **为通过安全测试而 Mock 公共函数。** 这只能证明 Mock 输出，不能证明真实文件系统行为。
14. **认为 `json.loads` 只会抛 `JSONDecodeError`。** 深层结构会触发 `RecursionError`，超长整数字面量会触发 `ValueError`；解析成功的超大 PID 还可能在 `os.kill` 触发 `OverflowError`。
15. **只跑测试，不做独立安全审阅。** Day 2 的多轮审阅已经证明绿色测试集仍可能漏掉严重风险。
16. **为了全仓格式命令变绿去修改审批计划。** 基线已有的 Markdown fenced-code 格式差异不是 Day 2 代码问题。

## Teach-back 结论

| 维度 | 判断 | 证据与边界 |
| --- | --- | --- |
| 工程验收 | 通过 | `9f2ea4c` 上聚焦不可用锁记录、Day 2 专项 40 项、累计 42 项测试，Ruff、Python 格式和 Git 差异检查均实际通过；最终独立规格与代码质量/安全复审均为 Approved，Critical/Important/Minor 为 0。 |
| 概念解释 | 在“支配 AI 完成”的学习目标上通过 | 使用者能够判断路径逃逸、原子失败、锁恢复、守卫边界、最长 secret 优先和不可用锁记录的保守处理，并在纠正后准确说明模块职责。 |
| 验收规格编写 | 在记录纠正后通过 | 使用者能写 Given/When/Then；已纠正把调度混入锁模块、把实现步骤当验收合同、临时文件表述不精确等问题。 |
| 接口阅读 | 四个公开合同通过 | 能解释 `resolve_inside`、`atomic_write`、`task_lock`、`redact` 的输入、成功结果和关键失败；不声称已掌握内部 Python、文件描述符或并发实现语法。 |
| 实践操作 | 按既定“直接使用 AI 与审阅证据”模式通过 | 验收命令由控制端/AI 真实运行，使用者完成行为判断与复述；没有单独证据证明使用者亲自在终端逐条重复，这在已批准学习目标下不构成阻塞。 |
| 新增异常边界 Teach-back | 通过 | 使用者准确要求：不能把不可用锁当成死锁；保留原锁且不删除/修改；不进入任务区；抛 `YbsError(code=5)`。掌握合同即可，不要求背底层异常名。 |

Day 2 的工程实现、测试、复现规格和新增异常边界 Teach-back 均已通过；复现规格最终送审版本已获 `Approved`，Critical、Important、Minor 均为 0。Day 2 学习状态与整个阶段资产化可以判定闭合。真正掌握的标准是：使用者能够向 AI 说清风险、合同、测试和证据，并识别 AI 是否越过模块边界或夸大安全保证；不是要求脱离 AI 默写底层 Python 与 POSIX 系统调用。

## 证据索引

- 最终源码：`src/ybs_cli/errors.py`、`src/ybs_cli/filesystem.py`、`src/ybs_cli/redaction.py`
- 最终测试：`tests/unit/test_filesystem.py`、`tests/unit/test_redaction.py`
- 已审批计划：`docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md` 的 Task 2 与 Day 3 边界
- 执行 brief：`.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/task-2-brief.md`
- 阶段报告：`.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/task-2-report.md`
- 决策账本：`.superpowers/sdd/2026-09-13-ybs-workspace-learning-demo/progress.md`
- 初始实现提交：`2308959a29a93b3f581ba9c8625e6b438639c7dd`
- 第一轮安全返修：`cfe985de22ca16996481f9edee580a0e6f50dd3d`
- 第二轮安全返修：`9422739e2c323789eab2968b4954540717f71d6c`
- 第三轮不可用锁记录返修：`9f2ea4c4d483f8b7b181fcd572150f6a2d5cb0fa` — `fix(filesystem): reject unusable lock records safely`；父为 `9422739`，只改 filesystem 源码与测试，trailers 为 Confidence high / Scope-risk narrow
- 首轮无上下文复建规格快照：`/private/tmp/ybs-day2-rebuild-audit.B68knb/Day-02-reconstruction-spec.md`，SHA-256 `5d220e05fefbff71da2a6a662a069d2dc4a499be128cb7fa12c2488b38dd6f4a`
- 首轮无上下文复建提交：`a5b47321ec6b16d3f0fadcb6e46a9125b2fb8739`；功能、提交和源仓隔离复建通过，但早期 pytest 临时文件未全部位于仓库内
- 持久审计摘要：`docs/specs/Day-02 复现规格.md` 第 16 节；该文档将随本阶段资产提交保存，临时复建仓库不是唯一证据
- 最终控制端复验：Darwin 25.5.0 arm64、uv 0.10.7、Python 3.11.14；聚焦 `1 passed in 0.03s`、专项 `40 passed in 0.05s`、全量 `42 passed in 0.41s`、Ruff 与 10 文件格式检查通过、`git diff --check 2ad8396..HEAD` 通过
- 规格审阅结论：最终送审版本已获 `Approved`，Critical、Important、Minor 均为 0；复现规格状态闭合
- 新增 Teach-back：使用者已通过不可用锁记录的保守处理问题；没有把底层异常名记忆或独立 Python 编码能力纳入通过声明
- 当前资产结论：工程、复建、规格和学习掌握均通过；Day 2 最终学习状态与整个阶段资产化闭合
