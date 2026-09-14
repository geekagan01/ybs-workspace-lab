# Day-02 复现规格

> 阶段标识：`Day-02`
> 阶段名称：安全路径、原子写入、任务锁与敏感信息脱敏
> 项目：`ybs-workspace-lab`
> 初始 Git 基线：`2ad8396def0cbcae838f066eb0aff478a56c1e52`
> 目标分支：`feat/day-02-safety-boundary`
> 参考最终实现：`9f2ea4c4d483f8b7b181fcd572150f6a2d5cb0fa`
> 下一阶段：Day-03 — 严格配置模型与 JSON Schema（本规格禁止开始）

## 1. 复现目标

本规格面向一个没有当前聊天记录、没有 Day 2 原实现、只得到本文件和规定初始仓库的 AI 执行者。执行者必须从 Day 1 已完成基线建立独立分支，通过测试驱动方式实现以下四个公开接口：

```python
resolve_inside(root: Path, candidate: str | Path) -> Path
atomic_write(path: Path, content: bytes) -> None
task_lock(root: Path, task_id: str) -> ContextManager[None]
redact(value: object, secrets: Sequence[str] = ()) -> object
```

最终结果必须具备：

- 解析真实路径后的工作区包含证明；
- 抵御父目录逃逸、symlink 逃逸和目录 rename/symlink 替换；
- 同目录、完整写入、持久化和原子替换；
- 任务 ID 验证、独占任务锁、保守失效锁恢复和所有权释放；
- 对合作并发进程的恢复/删除串行化；
- 对 mapping、list、tuple、字符串、URL 查询和显式 secret 的递归脱敏；
- 非法输入 code `2`，路径/写入/锁/恢复/释放类失败 code `5`；
- Day 2 专项 40 项测试、累计 42 项测试全部通过；
- 一次边界精确的本地 Day 2 实现提交；
- 不可用锁记录不能把 `ValueError`、`RecursionError` 或 `OverflowError` 泄漏到公开接口；
- 记录一次由新审计者完成的无上下文功能复建审计，并接受当前修订文档的只读一致性复审。

这里的“复现”是功能、接口、安全边界、测试证据和提交范围等价，不要求 Python 源码逐字节相同，也不要求提交 SHA 或参考历史的提交数量相同。

## 2. 初始状态

### 2.1 仓库来源与位置边界

任务提供方必须给执行者一个可写、隔离的 Day 1 基线仓库。执行者将该目录称为 `PROJECT_ROOT`。该目录不能是：

- 任务提供方用于保留 `main` 的活动检出；
- 外部只读参考项目 `ybs-workspace/`；
- 另一个正在执行任务的 worktree；
- 用户主目录、工作区集合根或其他宽泛路径。

进入该目录后，所有创建、修改、测试缓存和 Git 操作只能作用于这个隔离仓库。不得修改外部 `ybs-workspace/` 或任何其他检出。

### 2.2 Git 初态

初始仓库必须满足：

```text
分支：main
HEAD：2ad8396def0cbcae838f066eb0aff478a56c1e52
工作树：干净
暂存区：空
```

是否已有远端不影响复现；不得新增、删除或修改远端，也不得推送。

初始 Git 树必须恰好包含以下 15 个跟踪文件：

```text
.gitignore
.python-version
bin/ybs
docs/learning/Day-01 掌握什么.md
docs/specs/Day-01 复现规格.md
docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
pyproject.toml
src/ybs_cli/__init__.py
src/ybs_cli/__main__.py
src/ybs_cli/cli.py
src/ybs_cli/errors.py
src/ybs_cli/root.py
tests/integration/test_cli_entrypoint.py
uv.lock
```

以下 Day 2 实现/测试路径在初态必须不存在：

```text
src/ybs_cli/filesystem.py
src/ybs_cli/redaction.py
tests/unit/test_filesystem.py
tests/unit/test_redaction.py
```

执行者会从任务提供方单独收到本规格。本规格推荐保存在项目外；若平台只能把它放在项目内，则只允许它以未跟踪的 `docs/specs/Day-02 复现规格.md` 出现，并且不能进入 Day 2 实现提交。初态不要求存在 `docs/learning/Day-02 掌握什么.md`。

### 2.3 已审批输入完整性

两个已审批输入必须存在、非空并与以下 SHA-256 一致：

```text
docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
ea302b81fff4d5a5edaec4bf3c33dc341d4f3838c368b18d60468644a1b966d5

docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
f8f60db0599604697bd1d4b52dc895843f65023cdf360ff33f7e145f7168b799
```

执行者不能重写、格式化或“修正”这两个输入。

### 2.4 初态检查命令

在复现目录运行：

```sh
export PROJECT_ROOT="$(pwd -P)"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
mkdir -p "$PROJECT_ROOT/.demo/tmp"
export TMPDIR="$PROJECT_ROOT/.demo/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"

test "$(git branch --show-current)" = "main"
test "$(git rev-parse HEAD)" = "2ad8396def0cbcae838f066eb0aff478a56c1e52"
test -z "$(git diff --name-only)"
test -z "$(git diff --cached --name-only)"

git ls-tree -r --name-only HEAD

test -s docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md
test -s docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md
test "$(shasum -a 256 docs/superpowers/plans/2026-09-13-ybs-workspace-learning-demo.md | awk '{print $1}')" = "ea302b81fff4d5a5edaec4bf3c33dc341d4f3838c368b18d60468644a1b966d5"
test "$(shasum -a 256 docs/superpowers/specs/2026-09-13-ybs-workspace-learning-demo-design.md | awk '{print $1}')" = "f8f60db0599604697bd1d4b52dc895843f65023cdf360ff33f7e145f7168b799"

test ! -e src/ybs_cli/filesystem.py
test ! -e src/ybs_cli/redaction.py
test ! -e tests/unit/test_filesystem.py
test ! -e tests/unit/test_redaction.py
test ! -e docs/learning/Day-02\ 掌握什么.md
```

必须人工或由控制脚本把 `git ls-tree` 输出与第 2.2 节的 15 行逐项比较。若项目内放置了未跟踪的本规格，`git status --short --untracked-files=all` 只可额外显示：

```text
?? docs/specs/Day-02 复现规格.md
```

任何其他修改、暂存或未跟踪文件都必须先停止并报告，不能使用 `git clean`、`git reset --hard` 或覆盖操作处理。

## 3. 范围与非范围

### 3.1 本阶段允许修改

只允许创建或修改以下五个产品/测试文件：

```text
src/ybs_cli/errors.py
src/ybs_cli/filesystem.py
src/ybs_cli/redaction.py
tests/unit/test_filesystem.py
tests/unit/test_redaction.py
```

其中 `errors.py` 只允许改变类说明文字，不能改变公开构造器和字段。

### 3.2 本阶段禁止修改

- `pyproject.toml`、`uv.lock`、`.python-version`、`.gitignore`；
- Day 1 源码、集成测试和资产文档；
- 已审批 design/plan；
- CLI 命令树、配置、JSON Schema、状态机、任务目录、适配器、Mock 记录；
- 外部参考仓库、其他 worktree、远端和 Git 全局配置。

### 3.3 非目标

- 不实现等待队列、重试策略或任务调度；锁争用直接 code `5`；
- 不实现原生 Windows 支持；当前合同依赖 POSIX `fcntl.flock`、`dir_fd` 和 `O_NOFOLLOW`；
- 不自动修复远程锁、损坏锁、时间戳无效锁、权限不明锁或其他不确定锁；
- 不保证抵御一个绕过恢复守卫、能在最终 `stat`/`unlink` 间隙替换目录项的恶意同用户进程；
- 不开始 Day-03 的 Pydantic 配置模型或 JSON Schema；
- 不为了复刻参考 Git 历史而故意实现已知有漏洞的中间版本。

## 4. 环境与依赖

### 4.1 支持环境

参考验证环境：

```text
OS: Darwin 25.5.0 arm64
Python: 3.11.14
uv: 0.10.7
```

功能目标支持具备以下能力的 macOS/Linux：

- Python `>=3.11`；
- `uv`；
- Git；
- POSIX 文件描述符语义；
- Python `fcntl.flock`；
- `os.O_NOFOLLOW`、`os.O_DIRECTORY`；
- `dir_fd` 形式的 `open/stat/unlink/replace/mkdir`；
- `shasum` 用于固定输入 SHA-256 检查。

若任一 POSIX 能力不可用，必须将环境标为不支持并停止，不能用削弱 symlink/并发保护的实现换取测试通过。

### 4.2 项目内 uv 环境

每个新 Shell 进入 `PROJECT_ROOT` 后都必须执行：

```sh
export PROJECT_ROOT="$(pwd -P)"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
mkdir -p "$PROJECT_ROOT/.demo/tmp"
export TMPDIR="$PROJECT_ROOT/.demo/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"

test "$UV_CACHE_DIR" = "$PROJECT_ROOT/.demo/uv-cache"
test "$UV_PYTHON_INSTALL_DIR" = "$PROJECT_ROOT/.demo/uv-python"
test "$TMPDIR" = "$PROJECT_ROOT/.demo/tmp"
test "$TMP" = "$PROJECT_ROOT/.demo/tmp"
test "$TEMP" = "$PROJECT_ROOT/.demo/tmp"
```

所有 `uv`、pytest 子进程和任何由测试启动的子进程必须继承这些变量。`.demo/` 已由 Day 1 忽略。若 `uv` 下载 Python，下载位置也必须在 `.demo/uv-python`；pytest 的 `tmp_path` 必须位于 `.demo/tmp`。如果工具为每条命令启动新 Shell，必须为每次调用重新设置全部变量。

### 4.3 依赖合同

Day 2 不增加任何依赖，也不更新锁。开始实现前运行：

```sh
uv lock --check
lock_before="$(shasum -a 256 uv.lock | awk '{print $1}')"
uv sync --frozen
lock_after="$(shasum -a 256 uv.lock | awk '{print $1}')"
test "$lock_before" = "$lock_after"
```

所有命令必须 exit `0`。最终还必须确认：

```sh
git diff --exit-code 2ad8396 -- .python-version pyproject.toml uv.lock
```

该命令不得输出差异。

## 5. 最终目录和文件清单

Day 2 完成后，相对初始基线只允许以下变化：

```text
M  src/ybs_cli/errors.py
A  src/ybs_cli/filesystem.py
A  src/ybs_cli/redaction.py
A  tests/unit/test_filesystem.py
A  tests/unit/test_redaction.py
```

五个文件 Git 模式都必须为 `100644`。运行态允许出现被忽略的 `.venv/`、`.demo/`、`.pytest_cache/`、`.ruff_cache/` 和 `__pycache__/`；它们不得加入提交。

最终职责分类：

| 路径 | 类型 | 职责 | 是否进入 Day 2 实现提交 |
| --- | --- | --- | ---: |
| `src/ybs_cli/errors.py` | 事实源 | 稳定用户错误类型 | 是 |
| `src/ybs_cli/filesystem.py` | 事实源 | 路径、原子写和任务锁安全原语 | 是 |
| `src/ybs_cli/redaction.py` | 事实源 | 敏感信息脱敏原语 | 是 |
| `tests/unit/test_filesystem.py` | 验证资产 | 真实文件系统和受控故障回归 | 是 |
| `tests/unit/test_redaction.py` | 验证资产 | 结构化/URL/secret 脱敏回归 | 是 |
| `.ybs/locks/*.lock` | 运行态 | 任务所有权记录 | 否 |
| `.ybs/locks/.*.recovery` | 运行态 | 可复用的每任务恢复守卫文件 | 否 |
| 同目录 `.*.tmp` | 临时态 | 原子写临时文件 | 否 |

## 6. 文件级规格

### 6.1 `src/ybs_cli/errors.py`

最终内容必须功能等价于：

```python
class YbsError(Exception):
    """An expected user-facing failure with a stable process exit code."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
```

Day 2 只把描述从 operational failure 扩展为 user-facing failure。构造参数、`.message`、`.code`、`str(error)` 和 Day 1 行为不能变化。

### 6.2 `src/ybs_cli/filesystem.py`：常量和公开接口

模块至少包含功能等价常量：

```python
_TASK_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,63}$")
_DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
```

必须导入并使用 `YbsError`。公开接口只有本阶段规定的三个函数；私有帮助函数名称可以不同。

### 6.3 `resolve_inside(root, candidate)`

算法合同：

1. 在一个异常边界中执行 `resolved_root = root.resolve()`；
2. 把 `candidate` 转为 `Path`；
3. 绝对 candidate 直接 `resolve()`；相对 candidate 使用 `(resolved_root / candidate).resolve()`；
4. 通过 `resolved_candidate.relative_to(resolved_root)` 证明包含；
5. 成功返回 `resolved_candidate`；
6. 包含证明失败时抛 `YbsError("path is outside workspace: <candidate>", 5)` 或包含相同稳定短语的等价错误；
7. `resolve()` 的 `OSError` 或符号链接循环 `RuntimeError` 映射为含 `cannot resolve workspace path` 的 `YbsError(code=5)`。

禁止使用 `str(path).startswith(str(root))` 作为包含证明。

### 6.4 安全打开目录

`atomic_write` 与 `task_lock` 使用的目录打开帮助逻辑必须满足：

1. 绝对路径从其 anchor 开始，相对路径从 `.` 开始；
2. 每一级以 `O_RDONLY | O_DIRECTORY | O_NOFOLLOW` 和上一层 `dir_fd` 打开；
3. 忽略 anchor、空组件和 `.`；显式拒绝 `..`；
4. 每取得子目录描述符后才关闭父描述符；
5. 若关闭父描述符失败，必须先关闭刚取得的子描述符，再向外传播；
6. 任一异常路径都保守关闭当前持有描述符；
7. 关闭清理本身可以抑制重复关闭错误，但不能泄漏新开的子描述符。

创建 `.ybs` 或 `locks` 时，先在父 `dir_fd` 下以 mode `0700` 尝试 `mkdir`；只忽略 `FileExistsError`，随后仍以 `O_DIRECTORY | O_NOFOLLOW` 打开，确保已有同名 symlink 或非目录不能通过。

### 6.5 `atomic_write(path, content)`

输入和路径规则：

- `path.name` 不能是空、`.` 或 `..`；
- `path.parent` 必须已经存在；函数不能自动创建父目录树；
- 父目录路径中的 symlink 必须拒绝；
- `content` 按 `bytes` 写入，不做编码转换。

临时文件规则：

- 在已打开的目标父目录中创建；
- 名称模式功能等价于 `.<target-name>.<16-hex-random>.tmp`；
- 使用 `O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW`，mode `0600`；
- 名称冲突时最多重试 100 次，耗尽后以 `OSError(EEXIST)` 进入 code `5` 错误边界；
- 创建后立即用 `fstat` 保存 `(st_dev, st_ino)`。

写入与替换规则：

1. 写完全部 bytes；若使用 `os.write`，必须循环处理短写且零进度视为错误；若使用 file object，行为必须等价；
2. `flush()`；
3. `os.fsync()` 临时文件；
4. 关闭临时文件；
5. 调用 `os.replace(temp_name, target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)`；
6. 最终关闭父目录描述符。

失败规则：

- 任一 `OSError` 映射为含 `atomic write failed for <path>` 的 `YbsError(code=5)`；
- 替换失败时正式旧文件保持原 bytes；
- 只在临时名称、临时身份和父描述符均已取得时尝试清理；
- 清理前以 `os.stat(..., follow_symlinks=False, dir_fd=parent_fd)` 比较设备号/inode；
- 身份不匹配时不删；身份匹配时只 `unlink` 该临时名称；
- 清理失败不能覆盖原始写失败；
- 不得扫描或通配删除目录中的其他 `.tmp`。

若父目录路径在打开后被重命名并以 symlink 替换，`os.replace` 仍必须作用于已打开的原目录，不能写入 symlink 指向的外部目录。

### 6.6 `task_lock(root, task_id)` 的构造阶段

构造函数在返回 context manager 前必须：

1. 完整匹配 task ID 正则；失败抛含 `invalid task id` 的 `YbsError(code=2)`，且不能创建 `.ybs`；
2. `root.resolve()`；
3. 对 resolved root 执行 `stat()` 并记录 `(st_dev, st_ino)`；
4. 将 `OSError` 或 symlink-loop `RuntimeError` 映射为含 `task lock unavailable: <task-id>` 的 `YbsError(code=5)`；
5. 返回一个进入时才真正获取锁的 `ContextManager[None]`。

### 6.7 `task_lock` 的进入阶段

进入 `with` 时执行：

1. 用第 6.4 节方法重新打开 resolved root；
2. `fstat` 打开的根，并与构造阶段身份比较；不一致以 `ESTALE` 类操作失败结束；
3. 相对根安全打开或创建 `.ybs/locks`；
4. 生成 owner bytes；
5. 先尝试一次独占创建锁；
6. 只有锁已存在时，进入一次带恢复守卫的“重新创建或恢复后创建”流程；
7. 获取失败抛 `YbsError(code=5)`，且 `with` body 不执行；
8. 获取成功后 `yield None`，让 body 在锁保护下执行。

锁文件名：

```text
<task-id>.lock
```

项目相对路径：

```text
.ybs/locks/<task-id>.lock
```

### 6.8 owner record 和独占创建

owner record 序列化前的数据必须恰好有三个键：

```python
{
    "pid": os.getpid(),
    "host": socket.gethostname(),
    "created_at": datetime.now(UTC).isoformat(),
}
```

JSON 使用紧凑 separators 编码为 bytes。`created_at` 必须可由 `datetime.fromisoformat` 解析，带时区且 UTC offset 为零。

锁创建使用：

```text
O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW
mode 0600
相对 locks 目录描述符
```

创建成功后：

1. `fstat` 保存设备号/inode；
2. 循环 `os.write` 直到 owner bytes 全部写完；
3. 零字节写入进度视为失败；
4. `fsync`；
5. 关闭文件描述符。

`FileExistsError` 只表示未创建，交给恢复流程。其他创建、写、`fstat`、`fsync` 或关闭错误映射为 `YbsError(code=5)`。

若文件已经创建但后续失败：

- 没有取得 inode 身份时，保留文件，不能猜测删除；
- 已取得身份时，在每任务恢复守卫内核对设备号/inode后才删除；
- 若调用方已经持有同一恢复守卫，不得再次非重入获取；
- 守卫不可用时保留文件并保持 code `5`。

### 6.9 每任务恢复守卫

恢复守卫文件名：

```text
.<task-id>.lock.recovery
```

在 `locks` 目录描述符下以 `O_RDWR | O_CREAT | O_NOFOLLOW`、mode `0600` 打开，随后调用：

```python
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
```

守卫必须是非阻塞的。无法立即取得守卫时，当前获取/恢复/释放操作按 code `5` 失败或保守保留文件，不能等待、轮询或排队。无论成功或失败都关闭守卫 fd；守卫文件本身允许保留复用。

以下所有合作式删除路径必须经过同一个每任务恢复守卫：

- 确认死亡的旧锁删除；
- 创建锁失败后的本次锁清理；
- context 正常/异常退出时的自己拥有锁释放。

### 6.10 失效锁恢复

守卫内的恢复流程必须按顺序：

1. 再尝试一次独占创建；若锁恰好已经消失且创建成功，直接取得所有权；
2. 若仍存在，通过相对 `dir_fd` 和 `O_RDONLY | O_NOFOLLOW` 打开；
3. 读取全部 bytes 并保存设备号/inode；
4. UTF-8/JSON 解析失败则不可恢复；读取/解码/解析边界必须保守处理 `OSError`、`UnicodeDecodeError`、`ValueError` 和 `RecursionError`，不能把标准库原始异常泄漏出去；
5. 元数据必须是 dict，键集合恰为 `pid`、`host`、`created_at`；
6. `pid` 必须是 `type(pid) is int` 且大于 0，不能把 bool 当 int；
7. `host` 必须是非空 str；
8. `created_at` 必须是非空 str、可解析、带时区且 UTC offset 为零；
9. host 必须等于当前 `socket.gethostname()`；远程锁不可恢复，也不能探测其 PID；
10. 调用 `os.kill(pid, 0)`：只有 `ProcessLookupError` 表示确认死亡；成功、`PermissionError`、其他 `OSError` 和 PID 超出底层 C long 范围导致的 `OverflowError` 都不可恢复；
11. 再读一次当前锁；bytes 与设备号/inode 都必须和第一次观察一致；
12. 使用 `stat(..., follow_symlinks=False)` 再核对设备号/inode后删除；
13. 重新以 `O_EXCL` 创建当前 owner 的锁并完整写入、`fsync`；
14. 任一步证据不足时不删除当前锁，最终以 code `5` 拒绝进入 body。

两个进程同时恢复时，只允许一个取得守卫、删除旧锁和进入 body；另一个必须 code `5`，临界区不能重叠。

以下四类不可用记录必须统一走“不可恢复”路径：

1. 2,000 层嵌套 JSON 数组，`json.loads` 可能产生 `RecursionError`；
2. 普通非 JSON bytes；
3. owner JSON 中包含 5,000 位正整数 PID，`json.loads` 可能因 Python 的 4,300 位整数转换限制产生 `ValueError`；
4. 合法解析的 owner JSON，但 PID 为 `10**100`，`os.kill` 可能产生 `OverflowError`。

四种情况都必须以 `YbsError(code=5)` 拒绝，不进入 `with` body，锁文件原始 bytes 不变。不得仅依赖 `json.JSONDecodeError`，因为它不足以覆盖递归深度和超长整数字面量。

### 6.11 锁释放

离开 `with` 时，无论 body 正常返回还是抛错，都必须尝试：

1. 获取同一每任务恢复守卫；
2. 相对 `dir_fd` 读取当前锁 bytes 和设备号/inode；
3. 若文件不存在，视为没有可释放内容并返回；
4. 若 bytes 不等于本上下文 owner bytes，不删除；
5. bytes 相等时再用 no-follow `stat` 比较设备号/inode；
6. 身份一致才删除；身份不一致不删除；
7. 自己拥有的锁在 stat、守卫或 unlink 时出现 `OSError`，抛含 `task lock release failed` 的 `YbsError(code=5)`；
8. 最终关闭 locks、`.ybs` 和 root 目录描述符。

不能吞掉自己锁的删除失败，也不能删除被别人替换的 owner record。

### 6.12 文件系统威胁模型

必须在代码注释、测试名称或阶段文档中保持以下边界：

- 防御遵守 `task_lock` 协议的并发进程；
- 防御目录路径在检查后被 rename 或替换为 symlink 而把操作重定向到工作区外；
- owner bytes 与设备号/inode 双重核对降低错误删除风险；
- `stat` 与 `unlink` 不是一个原子比较删除系统调用；
- 不声称抵御一个同用户恶意进程绕过恢复守卫，并精确在最终 `stat`/`unlink` 间隙替换目录项。

禁止把“合作进程互斥”写成“绝对不会被任何本机进程攻击”。

### 6.13 `src/ybs_cli/redaction.py`

固定替换标记：

```python
_REDACTED = "***REDACTED***"
```

敏感完整键正则功能等价于：

```python
re.compile(r"(?:authorization|token|secret|password|api[_-]?key)", re.I)
```

只有 `fullmatch` 才把整个 value 替换；`x-authorization-note` 不能被当作完整敏感键。

`redact(value, secrets=())`：

1. 删除空字符串 secret；
2. 去重；
3. 保持相同长度项的稳定输入顺序；
4. 按长度降序形成替换列表；
5. 递归处理 value。

递归规则：

- `Mapping`：返回普通 dict；字符串键先替换显式 secrets；若原始字符串键完整匹配敏感正则，值直接为 marker，不递归保留原值；其他值递归；非字符串键保持；
- `list`：返回 list，逐项递归；
- `tuple`：返回 tuple，逐项递归；
- `str`：进入文本/URL 规则；
- 其他对象：原样返回，允许对象身份保持。

字符串规则：

1. 尝试 `urlsplit(value)`；
2. `urlsplit` 抛 `ValueError` 时做最长优先的字面 secret 替换；
3. 没有 query 时也做字面替换；
4. 有 query 时用 `parse_qsl(..., keep_blank_values=True)`；
5. 查询键中的显式 secret 做字面替换；
6. 原始查询键完整匹配敏感正则时，查询值整块替换；其他查询值做字面替换；
7. 用 `urlencode` 重建 query；
8. scheme、netloc、path、fragment 中也替换显式 secret；
9. `urlunsplit` 返回结果。

marker 在 URL 中可能被编码为 `%2A%2A%2AREDACTED%2A%2A%2A`；验收比较解析后的查询值和“无秘密残留”，不要求 URL 字节与手写展示完全相同。

### 6.14 资源和异常清理

所有文件描述符必须在成功与失败路径关闭。以下行为是硬合同：

- 父目录 fd 关闭失败时，已打开子目录 fd 也关闭；
- 锁文件 `fstat` 失败时，锁 fd 关闭；因为未知 inode，刚创建的空锁保守保留；
- hostname 获取失败映射为 code `5`，并关闭已打开目录 fd；
- 锁 JSON 的 `ValueError`、`RecursionError` 归一化为“记录不可恢复”，最终由公开锁接口返回 code `5`；
- PID 存活检查的 `OverflowError` 归一化为“记录不可恢复”，不能泄漏解释器异常或误判为死亡；
- release unlink 失败映射为 code `5`，锁保留；
- 原子写 cleanup 失败不覆盖原始 `atomic write failed`；
- 关闭重复失败可以在 finally 清理中抑制，不能把底层原始 `OSError` 直接泄漏给公开调用者。

## 7. 接口与行为契约

### 7.1 `resolve_inside(root, candidate) -> Path`

| 项 | 合同 |
| --- | --- |
| 输入 | 根 `Path`；相对或绝对候选 `str | Path` |
| 成功 | 返回 resolve 后的绝对 `Path`，且可 relative_to resolved root |
| 越界 | `YbsError`，message 含 `outside workspace`，code `5` |
| 解析失败 | `YbsError`，message 含 `cannot resolve workspace path`，code `5` |
| 写入副作用 | 无 |
| 幂等性 | 文件系统拓扑不变时重复调用结果相同 |

### 7.2 `atomic_write(path, content) -> None`

| 项 | 合同 |
| --- | --- |
| 输入 | 已有真实父目录下的目标 `Path`；完整 `bytes` |
| 成功 | 正式目标含完整新 bytes；不残留本次临时文件；返回 `None` |
| 替换前失败 | 旧目标保持；只清理可证明属于本次的临时文件；code `5` |
| 缺父目录/symlink 父目录 | 不创建目录、不写外部目标；code `5` |
| 并发清理 | 不删除其他调用的临时文件 |
| 幂等性 | 相同 bytes 重复写的最终内容相同；每次仍执行一次安全替换 |

### 7.3 `task_lock(root, task_id) -> ContextManager[None]`

| 项 | 合同 |
| --- | --- |
| 非法 ID | 构造阶段 code `2`，不创建 `.ybs` |
| 无锁 | 独占创建并 fsync owner record，进入 body |
| 活跃本机锁 | code `5`，不改锁，不进入 body |
| 确认死亡本机锁 | 守卫内复查、删除、独占重建后进入 body |
| 远程/损坏/递归过深/超长或溢出 PID/时间无效/权限不明 | code `5`，不进入 body，原锁 bytes 保持 |
| 并发恢复 | 一个进入，另一个 code `5`，无重叠 |
| 退出 | 取得守卫，验证 bytes 与身份，只删除自己的锁 |
| 释放失败 | code `5` 且锁保留 |
| 调度语义 | 无等待、无排队、无重试 |

### 7.4 `redact(value, secrets=()) -> object`

| 项 | 合同 |
| --- | --- |
| 输入 | 任意对象和字符串 secret 序列 |
| 敏感键 | 完整匹配时值整块替换，不保留嵌套内容 |
| 显式 secrets | 忽略空值、去重、最长优先，在字符串值和字符串键中替换 |
| 容器 | mapping 返回 dict；list/tuple 保持各自形状并递归 |
| 标量 | 非字符串原样通过 |
| URL | 解析/重建查询；敏感 query 值整块替换；非敏感诊断参数保留 |
| 畸形 URL | 不泄漏原始解析异常；执行字面 secret 替换 |
| 成功条件 | 序列化或文本结果中不含任何规定 secret |

### 7.5 错误码

- `2`：task ID 不满足输入语法；
- `5`：路径越界/解析失败、原子写失败、锁争用、锁状态不确定、锁恢复/获取/释放失败。

本阶段函数不把预期失败转换成成功值或布尔值。错误消息必须提供稳定短语并保留有用上下文，但不得含待脱敏 secret。

## 8. 实施顺序：TDD RED 到最终安全 GREEN

### 8.1 复现策略

参考实现历史包含一个功能提交和三次安全修复：

```text
2308959 feat: add safe atomic storage locking and redaction
cfe985d fix(filesystem): bind writes and serialize lock recovery
9422739 fix(filesystem): harden lock cleanup and descriptor handoff
9f2ea4c fix(filesystem): reject unusable lock records safely
```

复现执行者必须吸收四次提交的最终合同，但只做一个最终实现提交。不得为了得到相同提交数而故意写入已知 TOCTOU、并发恢复、清理漏洞或不可用锁记录异常泄漏。TDD 仍要求测试先于对应最终行为；可以在未提交状态中分批建立全部回归测试，然后一次实现最终加固版本。

### 步骤 0：验证基线并创建隔离分支

1. 运行第 2.4 节初态检查和第 4.3 节冻结同步；
2. 确认目标分支不存在：

   ```sh
   test -z "$(git branch --list feat/day-02-safety-boundary)"
   ```

3. 创建分支：

   ```sh
   git switch -c feat/day-02-safety-boundary
   ```

4. 验证：

   ```sh
   test "$(git branch --show-current)" = "feat/day-02-safety-boundary"
   test "$(git rev-parse HEAD)" = "2ad8396def0cbcae838f066eb0aff478a56c1e52"
   ```

本步骤不创建产品文件，不提交。

### 步骤 1：建立最初文件系统测试并取得接口缺失 RED

先创建 `tests/unit/test_filesystem.py`，首批包含以下 12 个函数级用例：

1. 接受根内相对与绝对路径；
2. 拒绝 parent escape；
3. 拒绝 symlink escape；
4. 原子写成功替换且无临时残留；
5. replace 失败保留旧文件、保留无关 `.tmp`；
6. 缺失父目录时 code `5` 且不创建目录；
7. 非法 task ID 在建目录前 code `2`；
8. 活跃本机 PID 锁不能被偷；
9. 确认死亡本机 PID 锁可以恢复；
10. 远程主机锁不恢复；
11. 非 JSON 锁不恢复；
12. 释放时保留被替换的 owner record。

文件导入真实公开接口，不创建 `src/ybs_cli/filesystem.py`。运行：

```sh
uv run pytest tests/unit/test_filesystem.py -q
```

有效 RED 必须是收集阶段 `ModuleNotFoundError: No module named 'ybs_cli.filesystem'`，exit `2`。pytest 缺失、测试语法错误或环境损坏不算有效 RED。

### 步骤 2：建立最初脱敏测试、接口缺失 RED 和行为 RED

创建 `tests/unit/test_redaction.py`，首批包含 6 个函数，参数化后收集 12 项：

1. 嵌套 header/query/显式 secrets；
2. 7 个完整敏感键：`authorization`、`AUTHORIZATION`、`token`、`secret`、`password`、`api_key`、`API-key`；
3. `x-authorization-note` 不按完整敏感键分类；
4. list/tuple 形状和非字符串标量；
5. 字符串 mapping key 中的显式 secret；
6. URL 查询解析与重建。

先运行：

```sh
uv run pytest tests/unit/test_redaction.py -q
```

有效接口缺失 RED 为 `ModuleNotFoundError: No module named 'ybs_cli.redaction'`，exit `2`。

随后只创建一个 identity stub：

```python
from collections.abc import Sequence


def redact(value: object, secrets: Sequence[str] = ()) -> object:
    return value
```

再次运行同一命令。必须收集成功并得到：

```text
11 failed, 1 passed
```

代表性失败必须能看到输入 secret 仍残留；这是行为 RED。不得直接把测试改成接受原始值。

### 步骤 3：在最终实现前补齐全部安全回归测试

保持 `filesystem.py` 不存在、`redaction.py` 仍为 identity stub，按以下四组加入或扩展剩余测试。每组安全回归建立后、对应最终行为实现前都实际运行测试并记录非绿色结果。filesystem 组此时仍应表现为 `ModuleNotFoundError` 的接口缺失 RED；这证明最终断言先于实现，但不能声称已经运行到函数内部的异常分支。redaction 组可以在 identity stub 上表现为行为断言 RED。失败不能来自测试语法或依赖错误。

自审组新增 3 个收集用例：

- 文件系统：symlink loop 映射为 code `5`；
- 文件系统：时间戳无效的锁不可恢复；
- 脱敏：畸形 URL-like 文本退化为字面 secret 替换。

第一轮安全审阅组新增 9 个收集用例：

- 两个竞争者恢复同一死锁时只有一个进入；
- atomic_write 拒绝 symlink 父目录；
- 父目录路径被换后仍绑定已打开原目录；
- `.ybs` 在 context entry 前被换成 symlink 时拒绝；
- hostname 失败映射并清理；
- lock `fstat` 失败关闭 fd 且保守保留锁；
- overlapping secrets 三个参数：短前缀、短后缀、重复长 secret。

第二轮安全审阅组新增 4 个收集用例，并修正并发测试同步点：

- owned-lock release unlink 失败必须 code `5`；
- 父 fd close 失败时关闭已打开 child fd；
- 外部持有 recovery guard 时 release 不删除锁；
- 外部持有 recovery guard 时 failed-create cleanup 不删除锁；
- 两竞争者测试必须包裹真实 `fcntl.flock(LOCK_EX | LOCK_NB)`，不能再 hook 已不被生产代码调用的 `Path.read_bytes`/`Path.unlink`。

无上下文审计组扩展 1 个已有收集用例，不增加收集数：

- 把“普通坏 JSON 不恢复”测试扩展为四轮循环，固定覆盖 2,000 层 JSON、普通坏 JSON、5,000 位正整数 PID JSON、`10**100` PID JSON；
- 最终断言每一轮都得到 `YbsError(code=5)`、不进入 body、原锁 bytes 不变。

新复建在 `filesystem.py` 缺失状态运行包含四轮最终断言的测试，实际结果仍是 interface-missing RED；随后直接实现第 6.10、6.14 节的最终安全合同。`RecursionError`、超长整数字面量 `ValueError` 和 `os.kill` `OverflowError` 的原生异常 RED 是参考实现/首轮审计返修的历史证据，不要求新的干净复建故意实现漏洞来重演。

最终测试收集数必须为：

```text
filesystem: 24
redaction: 16
合计: 40
```

四轮不可用记录位于同一个 pytest 测试函数的普通循环中，不使用 `pytest.mark.parametrize`，所以仍只收集一个 filesystem 项。该口径是固定合同。

### 步骤 4：直接实现最终加固版本

1. 按第 6.1 节修改 `errors.py` 说明文字；
2. 按第 6.2–6.12 节创建完整 `filesystem.py`；
3. 用第 6.13 节完整实现替换 identity stub；
4. 不创建队列、配置、状态或 CLI 命令；
5. 运行专项测试：

   ```sh
   uv run pytest tests/unit/test_filesystem.py tests/unit/test_redaction.py -q
   ```

6. 预期为 `40 passed`；
7. 若失败，只修复合同相关最小实现，不能降低断言、skip/xfail 或 Mock 公共接口。

### 步骤 5：累计验证与独立实现审阅

运行第 10 节全部提交前验收。然后给一名没有参与实现的审阅者以下输入：

- 本规格；
- 五个待提交文件差异；
- 40/42 测试、Ruff、格式和 diff 输出。

审阅重点：

- resolved containment；
- descriptor-relative/no-follow 是否覆盖检查到使用；
- 原子写只清理精确临时文件；
- 并发恢复是否真正经过 flock；
- 所有合作删除是否在同一 guard 内；
- owner bytes 与设备号/inode 双重验证；
- 文件描述符和异常清理；
- 深层 JSON、超长 JSON 整数和超出 `os.kill` 范围的 PID 是否归一化为稳定 code `5`；
- overlapping secrets 和畸形 URL；
- 威胁模型是否如实、没有夸大。

有 Critical、Important 或 Minor 未关闭时不能提交。每个行为问题先补能观察到 RED 的回归测试，再做最小修复并重跑全部门禁。

### 步骤 6：形成一个本地实现提交

独立实现审阅通过后，严格按第 11 节暂存和提交。参考历史的三个 fix 已被最终合同吸收；复现仓库只需要一个最终安全实现提交。

### 步骤 7：交给无上下文复现审计

每次新的无上下文重建在提交后都由新审计者按第 16 节执行，资产作者和实现者不能自审自批。当前资产化已经完成一次基于补充前规格快照的功能复建；该审计主动发现并补齐不可用锁记录合同。当前修订版还必须由控制端完成一次只读文档一致性复审，才能关闭最终文档状态。

## 9. 测试规格

### 9.1 文件系统 24 项

| # | 测试名/场景 | 固定设置 | 必须断言 |
| ---: | --- | --- | --- |
| 1 | `resolve_inside_accepts_relative_and_absolute_paths_inside_root` | `nested/status.yaml` 的相对和绝对形式 | 两者都返回根内相同目标 |
| 2 | `resolve_inside_rejects_parent_escape` | `../secret.txt` | message 含 `outside workspace`，code `5` |
| 3 | `resolve_inside_rejects_symlink_escape` | 根内 link 指向外部目录 | code `5`，不接受外部路径 |
| 4 | `resolve_inside_maps_symlink_loop_to_operational_error` | `loop -> loop` | message 含 `cannot resolve workspace path`，code `5` |
| 5 | `atomic_write_replaces_file_without_leaving_temporary_files` | 旧 `stage: intake`，写 `stage: clarify` | 新 bytes 完整；目录只剩 target |
| 6 | `atomic_write_preserves_old_file_when_replace_fails` | Mock `os.replace` 抛 `OSError("boom")`；放无关 `.keep.tmp` | code `5`；旧 target 和无关 tmp 不变；本次 tmp 消失 |
| 7 | `atomic_write_requires_existing_parent_directory` | `missing/status.yaml` | code `5`；`missing/` 不创建 |
| 8 | `atomic_write_rejects_symlink_target_directory` | `linked -> outside` | code `5`；outside 无目标 |
| 9 | `atomic_write_stays_bound_to_open_parent_when_path_is_swapped` | replace 前把 `state/` 改名并用 symlink 指向 outside | 原打开目录中的文件更新；outside 文件不变 |
| 10 | `atomic_write_closes_child_directory_when_parent_descriptor_close_fails` | 记录真实目录 fd，首次关闭父 fd 注入失败 | code `5`；父/子两个 fd 事后真实 `fstat` 都为 `EBADF` |
| 11 | `task_lock_rejects_invalid_task_id_before_creating_lock_directory` | `../../escape` | code `2`；`.ybs` 不存在 |
| 12 | `task_lock_rejects_ybs_directory_swapped_to_symlink_before_entry` | 构造 context 后把 `.ybs` 换为 outside symlink | code `5`；outside 下不建 locks |
| 13 | `task_lock_maps_hostname_failure_to_operational_error` | `socket.gethostname` 抛 `OSError` | code `5`；无 task lock 文件 |
| 14 | `task_lock_closes_descriptor_and_keeps_lock_when_fstat_fails` | 对新锁 fd 的 `fstat` 注入失败 | code `5`；fd 为 `EBADF`；锁路径保留 |
| 15 | `task_lock_active_same_host_pid_cannot_be_stolen` | 外层真实持锁，内层同 task 获取 | 元数据键恰好三个；PID/host/UTC 正确；内层 code `5` 且记录不变；外层退出后锁消失 |
| 16 | `task_lock_recovers_confirmed_dead_same_host_pid` | 有效本机 owner PID 12345；`os.kill` 对该 PID 抛 `ProcessLookupError` | body 内 owner 变为当前进程；退出后锁消失 |
| 17 | `task_lock_serializes_two_contenders_recovering_same_stale_lock` | 两真实线程；只把旧 PID 判死；barrier 包裹真实 nonblocking flock | 两次到达 guard；一个进入、一个 code `5`；无重叠；线程结束 |
| 18 | `task_lock_never_recovers_remote_host_lock` | host=`remote.example`；若调用 kill 则测试失败 | code `5`；不调用 kill；原 bytes 不变 |
| 19 | `task_lock_never_recovers_unavailable_lock_records` | 一个循环依次写入：2,000 层 JSON、`not-json`、5,000 位正整数 PID JSON、`10**100` PID JSON | 四轮都 code `5`；不进入 body；每轮原 bytes 不变；该函数只收集为 1 项 |
| 20 | `task_lock_never_recovers_invalid_timestamp_metadata` | 本机 PID、`created_at="old"`，即使 kill 报死亡 | code `5`；原 bytes 不变 |
| 21 | `task_lock_release_preserves_replaced_owner_record` | body 中把 lock bytes 换成另一个 owner | 退出后 replacement bytes 仍存在 |
| 22 | `task_lock_release_maps_owned_lock_unlink_failure_to_operational_error` | 只对最终 task lock unlink 注入 `PermissionError` | message 含 `task lock release failed`，code `5`；锁保留 |
| 23 | `task_lock_release_does_not_delete_while_recovery_guard_is_held` | 外部 fd 已独占 flock recovery guard | body 获取普通新锁；release code `5`；锁保留 |
| 24 | `task_lock_failed_create_does_not_delete_while_recovery_guard_is_held` | 外部持 guard；锁写入注入 `OSError` | acquire code `5`；部分锁保留，未绕过 guard 删除 |

### 9.2 脱敏 16 项

| 收集数 | 测试名/场景 | 必须断言 |
| ---: | --- | --- |
| 1 | 嵌套 Authorization、token URL、api_key、message 显式 secrets | JSON 序列化后无 `abc123`、`top-secret`，含 marker |
| 7 | 完整敏感键参数化 | 每个键的整个嵌套值都变为 marker |
| 1 | compound 非敏感键 | `x-authorization-note: visible` 不整值脱敏 |
| 1 | list/tuple/标量 | list 与 tuple 形状保持；42、None、object 原样；字符串 secret 替换；空 secret 忽略 |
| 1 | mapping 字符串键 | `label-needle` 变 `label-***REDACTED***` |
| 1 | URL 查询解析/重建 | fragment 保留；Api-Key 值为 marker；safe 值只替换 secret；无原 secret |
| 1 | 畸形 URL-like | `http://[broken/needle` 返回含 marker 的字面替换，不抛 `ValueError` |
| 3 | overlapping secrets 参数化 | `top`+`top-secret`、`secret`+`top-secret`、含重复长 secret 都得到 `Bearer ***REDACTED***` |

合计：`1 + 7 + 1 + 1 + 1 + 1 + 1 + 3 = 16`。

### 9.3 Mock/monkeypatch 边界

允许：

- 让 `os.replace`、`os.write`、`os.fstat`、`os.close`、`os.unlink` 或 hostname 在精确点失败；
- 为进程存活检查返回 active、`ProcessLookupError`、`PermissionError` 或其他错误；
- 包裹真实 `fcntl.flock` 设置 barrier，证明并发到达与输赢；
- 记录真实系统调用取得的 fd，并在恢复真实函数后验证 `EBADF`；
- 在测试回调中对真实目录做受控 rename/symlink 交换。

禁止：

- Mock `resolve_inside`、`atomic_write`、`task_lock` 或 `redact` 自身；
- Mock 最终文件内容、锁内容或脱敏返回值；
- 用纯内存假文件系统代替 `tmp_path` 的真实文件系统；
- 把 `Path.relative_to`、真实 symlink 行为、`O_EXCL` 或真实 `flock` 输赢替换成固定成功；
- 为让测试通过而删除安全断言、skip、xfail 或降低用例数。

### 9.4 通过标准

专项：

```text
........................................                                 [100%]
40 passed in <可变耗时>s
```

累计：

```text
..........................................                               [100%]
42 passed in <可变耗时>s
```

耗时可变化；`40`、`42`、零失败和零跳过是固定合同。

## 10. 验收命令

### 10.1 每个 Shell 的前置环境

```sh
cd "<任务提供方给出的隔离复现目录>"
export PROJECT_ROOT="$(pwd -P)"
export UV_CACHE_DIR="$PROJECT_ROOT/.demo/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.demo/uv-python"
mkdir -p "$PROJECT_ROOT/.demo/tmp"
export TMPDIR="$PROJECT_ROOT/.demo/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
test "$UV_CACHE_DIR" = "$PROJECT_ROOT/.demo/uv-cache"
test "$UV_PYTHON_INSTALL_DIR" = "$PROJECT_ROOT/.demo/uv-python"
test "$TMPDIR" = "$PROJECT_ROOT/.demo/tmp"
test "$TMP" = "$PROJECT_ROOT/.demo/tmp"
test "$TEMP" = "$PROJECT_ROOT/.demo/tmp"
```

尖括号内容必须替换为实际目录，不能把参考机器绝对路径硬编码到产物。

### 10.2 提交前功能和质量验收

```sh
uv lock --check
lock_before="$(shasum -a 256 uv.lock | awk '{print $1}')"
uv sync --frozen
lock_after="$(shasum -a 256 uv.lock | awk '{print $1}')"
test "$lock_before" = "$lock_after"

uv run pytest tests/unit/test_filesystem.py::test_task_lock_never_recovers_unavailable_lock_records -q
uv run pytest tests/unit/test_filesystem.py tests/unit/test_redaction.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check src tests
git diff --check

test "$(git branch --show-current)" = "feat/day-02-safety-boundary"
git diff --exit-code 2ad8396 -- .python-version pyproject.toml uv.lock
git status --short --untracked-files=all
```

预期：

| 检查 | 结果 |
| --- | --- |
| `uv lock --check` | exit `0` |
| `uv sync --frozen` | exit `0`；lock SHA 不变 |
| 不可用锁记录 focused pytest | `1 passed`；测试内部四轮均安全拒绝 |
| Day 2 pytest | `40 passed` |
| 全量 pytest | `42 passed` |
| Ruff check | `All checks passed!` |
| Ruff format | `10 files already formatted` 或功能等价的当前文件数，exit `0` |
| `git diff --check` | exit `0`、无输出 |
| 依赖差异 | `.python-version`、`pyproject.toml`、`uv.lock` 无差异 |
| status | 只出现五个 Day 2 文件和可能的未跟踪本规格；无 Day 3/无关文件 |

参考实现最终安全返修 `9f2ea4c` 在 Darwin 25.5.0 arm64、uv 0.10.7、Python 3.11.14 上由控制端实测：`uv lock --check` exit `0`、`uv sync --frozen` exit `0`、不可用锁记录 `1 passed in 0.03s`、专项 `40 passed in 0.05s`、累计 `42 passed in 0.41s`、Ruff `All checks passed!`、`10 files already formatted`、范围 diff check exit `0`。最终独立复审为 Approved，Critical、Important、Minor 均为 0。

### 10.3 提交后范围与 Git 验收

```sh
test "$(git branch --show-current)" = "feat/day-02-safety-boundary"
test "$(git rev-parse HEAD^)" = "2ad8396def0cbcae838f066eb0aff478a56c1e52"
test "$(git rev-list --count 2ad8396..HEAD)" -eq 1

git diff --name-status 2ad8396..HEAD
git show -s --format='%s%n%b' HEAD
git ls-tree HEAD \
  src/ybs_cli/errors.py \
  src/ybs_cli/filesystem.py \
  src/ybs_cli/redaction.py \
  tests/unit/test_filesystem.py \
  tests/unit/test_redaction.py
git diff --check 2ad8396..HEAD
git status --short --untracked-files=all
```

预期：

- `2ad8396..HEAD` 恰好一个提交；
- name-status 恰好为第 5 节的五行；
- subject 和 trailers 符合第 11.2 节；
- 五个路径模式均为 `100644`；
- 实现/测试无未提交修改；
- 项目内的本规格若存在，可保持未跟踪；
- 无 Day 3 文件。

## 11. Git 与提交边界

### 11.1 授权范围

本规格只授权在隔离复现仓库的 `feat/day-02-safety-boundary` 分支创建一个本地实现提交。它不授权：

- 修改 `main`；
- push；
- add/remove/change remote；
- amend、rebase、reset、clean、force 操作；
- 修改 Git 全局配置；
- 提交本规格、学习笔记、运行态目录或任何非五文件路径。

平台若要求提交审批，执行者必须在所有验收和审阅通过后暂停请求授权，不能规避审批。

### 11.2 唯一实现提交

显式暂存：

```sh
git add \
  src/ybs_cli/errors.py \
  src/ybs_cli/filesystem.py \
  src/ybs_cli/redaction.py \
  tests/unit/test_filesystem.py \
  tests/unit/test_redaction.py
```

检查暂存区：

```sh
git diff --cached --name-status
git diff --cached --check
```

只能出现：

```text
M	src/ybs_cli/errors.py
A	src/ybs_cli/filesystem.py
A	src/ybs_cli/redaction.py
A	tests/unit/test_filesystem.py
A	tests/unit/test_redaction.py
```

提交：

```sh
git commit -m "feat: add safe atomic storage locking and redaction" \
  -m "Confidence: high
Scope-risk: narrow"
```

subject 必须精确为：

```text
feat: add safe atomic storage locking and redaction
```

正文必须含：

```text
Confidence: high
Scope-risk: narrow
```

新提交 SHA、作者和时间允许变化。

### 11.3 与参考历史的差异

参考仓库分四次提交达到最终状态：

1. `2308959` 初始实现；
2. `cfe985d` 绑定目录写入并串行化锁恢复；
3. `9422739` 加固锁清理和描述符交接；
4. `9f2ea4c4d483f8b7b181fcd572150f6a2d5cb0fa` 拒绝不可用锁记录并归一化解析/系统调用异常；父为 `9422739e2c323789eab2968b4954540717f71d6c`，只改 `src/ybs_cli/filesystem.py` 与 `tests/unit/test_filesystem.py`，subject 为 `fix(filesystem): reject unusable lock records safely`，trailers 为 Confidence high / Scope-risk narrow。

无上下文重建从本规格直接获得最终安全知识，所以只建立一次最终提交。功能等价不要求重新制造三次安全缺陷，也不要求新 SHA 与任何参考 SHA 相同。

### 11.4 额外内容处理

若暂存区出现清单外文件，只允许用：

```sh
git restore --staged -- <精确清单外路径>
```

取消该路径暂存。不能删除或覆盖内容。若工作区出现来源不明的修改，停止并报告，不能继续提交。

## 12. 错误处理与恢复

### 12.1 `uv`、Git 或 `shasum` 缺失

表现：工具检查或命令启动失败。

恢复：停止并报告缺失工具。由环境所有者安装；不能用全局 `pip`、手写锁或跳过哈希检查替代。

### 12.2 Python 或依赖环境失败

表现：Python 不是 3.11+，或 `uv sync --frozen` 失败。

恢复：保持项目内 uv 与临时目录变量，检查 `.python-version` 和网络/缓存政策。若允许下载，`uv` 只能把 Python 和缓存写入 `.demo/uv-python`、`.demo/uv-cache`；pytest 临时文件必须写入 `.demo/tmp`。不能降低 Python 约束或修改依赖范围。

### 12.3 缺少 POSIX 安全能力

表现：没有 `fcntl`、`O_NOFOLLOW`、`O_DIRECTORY` 或需要的 `dir_fd` 支持。

恢复：将当前平台标记为不支持，切换到受支持 macOS/Linux 环境重新执行。不能降级为只用 `Path.resolve()` 后普通路径写入，也不能跳过并发守卫测试。

### 12.4 输入基线或审批哈希不符

表现：HEAD、15 文件清单、plan/design SHA 不匹配。

恢复：停止，让任务提供方重新提供干净 Day 1 基线。不能从聊天记忆拼写审批文件，也不能 checkout/重置一个有用户修改的目录。

### 12.5 接口缺失 RED 不符合预期

表现：失败来自 pytest 未安装、测试语法、错误 import 路径或已有 Day 2 模块。

恢复：先修复环境或初态；只有 `ybs_cli.filesystem`/`ybs_cli.redaction` 不存在造成的 collection error 才是有效接口 RED。不得把伪红记录为 TDD 证据。

### 12.6 测试失败

表现：最终不是 40/42 通过。

恢复：保存首个失败、退出码和相关输出，按路径、写入、锁、脱敏或测试有效性分类。若泄漏 `ValueError`、`RecursionError` 或 `OverflowError`，先确认输入属于第 6.10 节四类不可用锁记录，再在解析或 `os.kill` 边界做保守归一化；不能把它误判成死亡锁并删除。只修最小合同；不能 Mock 公共函数、降低断言、删测试、skip 或 xfail。修复后重跑聚焦不可用记录、专项、累计、Ruff、格式和 diff gate。

### 12.7 写入或编辑中断

表现：新增 Python 文件不完整或语法错误。

恢复：只核对第 5 节五个精确文件；使用本规格重建不完整文件；保留任何不属于本任务的用户文件。不得递归删除源码、测试或仓库目录。

### 12.8 测试留下临时锁

正常测试使用 `tmp_path`，失败目录由 pytest 管理。真实项目根若意外出现 `.ybs/locks`：

- 不得直接删除未知 `.lock`；
- 读取并判断 owner JSON、主机和 PID；
- `PermissionError`、远程、损坏或不确定状态都停止报告；
- 只有能证明为本轮测试创建、且对应进程明确结束的精确路径，才由环境所有者按审计流程清理；
- 禁止递归删除 `.ybs/` 或使用通配符清理锁。

### 12.9 工作区不干净

表现：五个任务路径和可选未跟踪规格之外还有状态。

恢复：停止，列出精确路径和来源。允许通过显式暂存清单排除不相关文件，但不能 `git clean`、`git reset --hard`、`git checkout --` 或覆盖用户内容。

### 12.10 提交失败

表现：缺作者身份、钩子或审批阻止提交。

恢复：保留暂存区，报告错误。作者身份只能由用户进行仓库级配置；不得修改 global config。解决后重试相同提交，不能 amend 已成功提交或 push。

### 12.11 Ruff Markdown 基线差异

表现：`uv run ruff format --check .` 报审批计划中的 Python fenced code 需要格式化。

恢复：确认相同失败能在未改动的 `2ad8396` 基线上复现；不修改审批 plan 或 `pyproject.toml`。有效门禁是：

```sh
uv run ruff check .
uv run ruff format --check src tests
```

### 12.12 独立审阅发现问题

表现：审阅者报告 Critical、Important 或 Minor。

恢复：不提交；为可观察行为问题先写回归测试并取得 RED，再做最小修复。若意见要求超出本规格威胁模型或进入 Day 3，记录为范围问题并交任务所有者裁决，不能自行扩展阶段。

## 13. 验收矩阵

| 阶段目标 | 证据 | 命令/检查 | 必须结果 |
| --- | --- | --- | --- |
| 基线准确 | Git | `git rev-parse HEAD`（建分支前） | `2ad8396...` |
| 隔离分支 | Git | `git branch --show-current` | `feat/day-02-safety-boundary` |
| 审批输入未变 | SHA-256 | 第 2.3 节两条哈希断言 | 两个固定值 |
| 项目内运行态 | 环境 | 第 4.2 节路径断言 | cache、Python 和 pytest 临时文件均在 `.demo/` |
| 无依赖变化 | Git/lock | lock 前后 hash；`git diff` | lock 不变；三文件无差异 |
| 路径包含正确 | 单测 | filesystem #1–4 | 根内接受；越界/循环 code `5` |
| 原子写成功 | 单测 | filesystem #5 | 新 bytes 完整，无 temp |
| 原子失败安全 | 单测 | filesystem #6–10 | 旧文件/外部/其他 temp 安全；fd 关闭 |
| ID 输入错误 | 单测 | filesystem #11 | code `2`，不建 `.ybs` |
| 锁路径绑定 | 单测 | filesystem #12 | symlink swap 拒绝，不写外部 |
| 设置错误清理 | 单测 | filesystem #13–14 | code `5`，fd/锁保守状态正确 |
| 活锁不偷 | 单测 | filesystem #15 | code `5`，记录不变 |
| 死锁安全恢复 | 单测 | filesystem #16–17 | 只明确死亡；并发一个进入 |
| 不确定锁保留 | 单测+代码审阅 | filesystem #18–20；PermissionError 分支 | 远程、坏 JSON、递归过深、超长/溢出 PID、时间无效、权限不明均 code `5` 且不删 |
| 不可信记录异常归一化 | 聚焦单测 | filesystem #19 内四轮 | `ValueError`、`RecursionError`、`OverflowError` 不泄漏；原 bytes 不变 |
| 释放所有权安全 | 单测 | filesystem #21–24 | 不删别人锁；失败可见；删除都受 guard |
| 结构化脱敏 | 单测 | redaction 16 项 | 无 secret，结构和诊断数据符合合同 |
| 专项回归 | pytest | focused command | 40 passed，零跳过 |
| Day 1 不回归 | pytest | full command | 42 passed，零跳过 |
| 静态质量 | Ruff | `ruff check .` | exit `0` |
| Python 格式 | Ruff | `ruff format --check src tests` | exit `0` |
| 差异质量 | Git | `git diff --check` | exit `0` |
| 文件模式 | Git tree | `git ls-tree HEAD <五路径>` | 全部 `100644` |
| 提交边界 | Git | `git diff --name-status 2ad8396..HEAD` | 只有五文件 |
| 提交消息 | Git | `git show -s --format=...` | 固定 subject/trailers |
| 未进入 Day 3 | 路径/Git | `git diff --name-only`、`git status` | 无配置/Schema/Day 3 文件 |
| 首轮无上下文功能复建 | 审计报告 | 第 16.2 节 | 补充前规格快照已实际通过，并主动发现/修复不可用记录缺口 |
| 当前文档一致性 | 只读复审 | 第 16.3 节 | 控制端复审完成后才关闭最终资产状态 |

任一矩阵项未执行必须标为“未验证”；代码阅读不能替代要求实际执行的命令。

## 14. 功能等价判定

### 14.1 必须一致

- 四个公开接口名称、参数顺序、默认值和成功返回类型；
- task ID 正则、锁路径、owner JSON 三个精确字段和 UTC aware 时间；
- code `2` 与 code `5` 的边界；
- resolve 后用目录组件关系证明包含；
- descriptor-relative/no-follow 的写入和锁操作；
- 同目录唯一临时文件、完整写、flush/fsync、原子 replace 和精确清理；
- 失效锁只在有效、同主机、明确 `ProcessLookupError` 时恢复；
- 深层 JSON、超长 JSON 整数和 `os.kill` PID 溢出均保守归一化为 code `5`，不改锁；
- 恢复前双读复查和设备号/inode 核对；
- recovery guard 覆盖全部合作删除路径；
- release owner bytes 与身份验证，owned unlink 失败可见；
- 脱敏敏感键、显式 secret 最长优先、结构递归和 URL 规则；
- 24 个 filesystem + 16 个 redaction 收集用例的固定行为；
- 专项 40、累计 42、零 skip/xfail、Ruff 和 diff 门禁；
- 只有五个 Day 2 文件进入一个本地实现提交；
- 不修改依赖、Day 1、审批输入、远端或 Day 3；
- 威胁模型不夸大；
- 首轮独立无上下文功能复建通过，且当前修订文档通过后续只读一致性复审。

### 14.2 允许不同

- 私有帮助函数名称和内部代码分段；
- 随机临时文件的具体 16 位十六进制值；
- owner record 的实际 PID、hostname 和时间；
- pytest 耗时；
- Python 3.11 补丁版本；
- 新提交 SHA、作者、时间；
- 只要可观察值相同，JSON/URL 内部实现方式可不同；
- 满足同样 safety contracts 的等价短写处理；
- 复现目录绝对路径。

### 14.3 不足以判定等价的做法

- 只检查四个函数存在；
- 只跑 happy-path；
- 只跑 40 项专项测试但不跑累计、Ruff、格式和 Git 边界；
- 用 Mock 替代真实公开接口或真实文件系统；
- 通过 skip/xfail 降低收集数；
- 只比较参考源码文本或提交 SHA；
- 由同一实现者自行宣布安全审计通过。

### 14.4 最终判定算法

只有全部成立才可判定功能等价：

1. 初始基线、审批哈希和隔离分支有效；
2. 接口缺失 RED 与 identity-stub `11 failed, 1 passed` 有实际记录；
3. 所有最终安全回归测试在实现前建立；
4. 第 13 节矩阵没有失败、跳过或无说明的未验证项；
5. 依赖和 Day 1 文件无变化；
6. 实现提交恰好包含五个路径且消息正确；
7. 没有 Day 3 内容或外部仓库修改；
8. 新审计者只使用规格快照与规定初态完成实际复现/走查，并给出无阻塞歧义的通过结论；
9. 审计主动发现的不可用锁记录合同已固化在当前版本，并经控制端只读一致性复审确认文档、最终源码和测试相符。

## 15. 已知限制与后续阶段边界

1. 文件系统实现依赖 macOS/Linux POSIX 能力，没有原生 Windows 合同。
2. `fcntl.flock` 是合作式锁；绕过协议的同用户进程不受它强制约束。
3. `stat` 与 `unlink` 之间仍有非原子窗口，不对恶意同用户精确替换最终目录项作保证。
4. 失效锁恢复刻意保守；远程主机、权限不足、损坏元数据和其他不确定状态需要人工处理。
5. recovery guard 文件会持久保留复用，不应被误认为未释放的 task lock。
6. `atomic_write` 不自动创建父目录；调用者必须先安全准备目录。
7. `atomic_write` 只 `fsync` 新文件；本阶段没有额外规定对替换后的父目录做目录 `fsync`。
8. `redact()` 返回普通 dict，不承诺保留自定义 Mapping 子类。
9. 敏感键必须完整匹配固定模式；其他组织自定义敏感字段需通过显式 secrets 或后续合同扩展。
10. URL 重建可能规范化 percent encoding 或查询表达形式；无泄漏和语义保留是合同。
11. Day 2 未将四个函数接入任何新的 CLI 命令；它们是后续写入模块的基础库。
12. Day 3 才实现严格 Pydantic 配置模型、YAML/JSON 输出和 JSON Schema；本阶段禁止提前创建。

这些限制是明确设计边界，不是允许执行者顺手扩展范围的待办。

## 16. 无上下文复现审计

### 16.1 作者自检

- 已给出固定初始 commit、15 文件清单、审批输入哈希和 Day 2 缺失路径；
- 已规定隔离分支、项目内 uv/pytest 临时目录、POSIX 依赖和禁止修改范围；
- 已给出四个公开合同、错误码、文件描述符/并发/清理细节、不可用锁记录归一化和威胁模型；
- 已列出全部 40 个收集用例及 42 项累计目标；
- 已区分接口缺失 RED、行为 RED、最终 GREEN、三次安全返修和参考历史审阅失败；
- 已要求直接实现最终安全行为，不复刻已知漏洞；
- 已给出一个提交的文件边界、消息、trailers 和禁止 Git 动作；
- 已给出环境、POSIX、测试、写入、锁、dirty tree、提交和 Ruff 基线差异恢复方式；
- 未写入 Day 3 实施内容。

### 16.2 首轮独立无上下文功能复建审计

首轮审计使用的输入规格快照是：

```text
路径：/private/tmp/ybs-day2-rebuild-audit.B68knb/Day-02-reconstruction-spec.md
SHA-256：5d220e05fefbff71da2a6a662a069d2dc4a499be128cb7fa12c2488b38dd6f4a
```

该快照早于本版对四类不可用锁记录和三种异常归一化的显式补充，因此不能声称它与当前文件字节相同。审计者只得到该规格快照、干净 Day 1 基线和两份固定 SHA-256 的 design/plan；没有读取参考 Day 2 实现、Day 2 学习笔记、旧阶段报告或当前聊天记录。

初态实证：

- 仓库为干净的 `main@2ad8396def0cbcae838f066eb0aff478a56c1e52`；
- Git 树恰有第 2.2 节列出的 15 个文件；
- plan/design 分别匹配 `ea302b...` 与 `f8f60d...` 固定哈希；
- Day 2 源码与测试不存在；
- 审计者创建 `feat/day-02-safety-boundary`，未读取或复制原实现。

TDD 实证：

- filesystem interface-missing RED：`ModuleNotFoundError: No module named 'ybs_cli.filesystem'`，exit `2`；
- redaction interface-missing RED：`ModuleNotFoundError: No module named 'ybs_cli.redaction'`，exit `2`；
- identity stub 行为 RED：`11 failed, 1 passed`，输出仍含 `abc123` 与 `top-secret`；
- 各组安全回归建立后、对应最终行为实现前，测试均实际运行并保持非绿；
- 独立只读审阅用 `10**100` PID 作为探针；它与 2,000 层 JSON 共同构成一个 Important finding 的两类输入，不是两个 Important；
- 审计仓库的实际 pytest RED/GREEN 使用 `1 << 100` PID 和 2,000 层 JSON：前者真实泄漏 `OverflowError`，后者真实泄漏 `RecursionError`，随后在解析/存活检查边界保守归一化；
- `a5b4732` 中不可用记录回归测试为一个函数内三轮：普通坏 JSON、`1 << 100` PID、2,000 层 JSON；5,000 位整数和四轮固定合同尚不属于该审计提交；
- 并发测试预建可复用 recovery guard，真实到达 `fcntl.flock`，一个竞争者进入、另一个 code `5`，没有临界区重叠。

最终功能和提交实证：

- Day 2 专项 `40 passed in 0.06s`；
- 累计 `42 passed in 0.19s`；
- Ruff 静态检查、`10 files already formatted`、diff、锁文件不变和依赖边界全部通过；
- 审计提交为 `a5b47321ec6b16d3f0fadcb6e46a9125b2fb8739`，父严格为 `2ad8396`；
- 基线后恰有一个提交，只包含五个规定文件，模式全部 `100644`，subject 与 Confidence high / Scope-risk narrow trailers 符合第 11.2 节；
- 最终工作树干净，没有 Day 3、远端变化或外部源仓修改；
- 没有阻止安全复建的规格歧义；私有帮助函数和代码结构按功能等价规则允许不同；
- 审计实现修复后独立复审为 Approved，Critical、Important、Minor 均为 0。

必须保留执行偏差：前几轮 pytest 的 `tmp_path` 使用了系统默认 `/private/var/.../T/pytest-of-jichengye`。产品文件、Git 操作和 uv 持久化状态仍在隔离复建仓库内，最终复跑已经把 `TMPDIR`、`TMP`、`TEMP` 固定到仓库的 `.demo/tmp`。因此本轮可以判定**功能、提交边界和源仓隔离复建通过**，但不能声称全过程的每一个 pytest 临时文件都位于仓库内。

### 16.3 审计发现回灌与当前文档状态

首轮审计主动发现的深层 JSON 和超大 PID 风险，连同后续原工作树独立复审继续发现的“5,000 位正整数在 `json.loads` 处先触发 `ValueError`”问题，已经回灌到：

- 第 4.2 节的项目内 pytest 临时目录要求；
- 第 6.10、6.14 节的 `ValueError`、`RecursionError`、`OverflowError` 归一化合同；
- 第 8 节步骤 3 的测试先行顺序；
- 第 9.1 节一个测试函数内四轮不可用记录；
- 第 10、12、13、14 节的验收、恢复和等价判定。

审计提交 `a5b4732` 保留三轮回归；后续原工作树 `9f2ea4c` 将同一测试固化为四轮，加入 5,000 位整数，并保留普通坏 JSON、2,000 层 JSON 和超大 PID。原工作树返修提交完整 SHA 为 `9f2ea4c4d483f8b7b181fcd572150f6a2d5cb0fa`，父为 `9422739e2c323789eab2968b4954540717f71d6c`；只修改 filesystem 源码与测试。

控制端随后完成了修订规格的定向只读一致性复审。送审版本 SHA-256 为：

```text
4a424053629109bfaf7b4512baaf1fe64e1e36aed138b9cb25e7b0d0c97fca58
```

该值专指复审时读取的**送审版本**；本段审计结论写回后文件 bytes 已变化，因此不能把该值称为当前文件或最终文件 SHA-256。

定向复审确认：

- 普通坏 JSON、2,000 层 JSON、5,000 位正整数 PID JSON、`10**100` PID JSON 四类真实探针均得到 `YbsError(code=5)`，`with` body 未进入，锁原始 bytes 保留；
- 聚焦不可用记录测试为 `1 passed in 0.01s`；
- Day 2 专项为 `40 passed in 0.04s`；
- 累计测试为 `42 passed in 0.21s`；
- Ruff 静态检查、`10 files already formatted` 和 diff check 均通过；
- 临时复建仓库仍停留在 `a5b47321ec6b16d3f0fadcb6e46a9125b2fb8739`，工作树干净；
- 当前规格对四类固定合同、24/16/40/42 计数、四提交参考史、隔离偏差和异常归一化的描述与实际证据一致。

本次审计结论回写没有再次修改代码，也没有重复执行代码门禁；`1 passed`、`40 passed`、`42 passed`、Ruff、格式和 diff 数字来自结论回写前一轮已经实际完成的一致性复验，不能表述为本次文字编辑后重新运行所得。

定向规格复审结论为 `Approved`，Critical、Important、Minor 均为 0。第 8 节步骤 7 中“还必须完成一致性复审”记录的是送审前状态；本节记录复审完成后的最终状态，并取代该时间点状态描述。

当前结论：

```text
首轮无上下文功能复建通过；审计发现已显式固化；
当前修订规格一致性复审已完成，Day 2 资产规格状态闭合。
```
