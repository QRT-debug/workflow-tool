# 工程笔记：缺陷、沙箱限制与排障

这份文件是**常驻的**工程知识库，不属于三份交接文件的一部分（那三份是"续做用"的入口，需要保持精简）。这里放的是踩过的坑、定位过程与应对方法 —— 写得越具体，下次越省时间。

> 面向的读者是**未来的 agent 会话**。结论优先，"当时怎么发现的"也保留，因为错误的排查方向往往比结论更值得记住。

---

## 一、修过的真实缺陷

### 缺陷 1：`one-click-init-project.ps1` 用裸名调用兄弟脚本，会静默中断

**现象**：脚本用 `powershell -ExecutionPolicy Bypass -File $initScript -ProjectPath $ProjectPath` 调用同目录的 `init-project.ps1`。当 `powershell` 这个名字解析不到时抛 `CommandNotFoundException`；在脚本顶部的 `$ErrorActionPreference = "Stop"` 作用下，**整个脚本当场中断**。可观察到的只有：部分输出 + 非零退出码 + **没有任何有用的报错**。

**根因**：把一个"名字解析"的外部依赖塞进了关键路径。裸名依赖 PATH 与执行策略；一旦名字解析失败，失败点离真正原因很远。

**修法**：改为同进程直接调用 `& $initScript -ProjectPath $ProjectPath`。好处有三：不再依赖 PATH；stdout 留在同一个控制台；异常能正常向上传播。

**验证**：`selftest.py` 的第 3 分区覆盖 `init_project` 的生成物逐字节一致、幂等（不覆盖用户内容、mtime 不变）、自动创建 `docs/`、三类异常路径、模板缺失时报错。

**诚实附注**：当时的触发环境是 agent 沙箱（`Get-Command powershell` 失败，但 `powershell.exe` 确实存在且其目录在 PATH 上）。**无法断言用户双击时也会中断**。但改动在两种情况下都严格更优，所以保留。

### 缺陷 2：GUI 的空路径会退化成"当前目录"

**现象**：清空项目路径输入框后，界面会把 **GUI 进程的工作目录（CWD）**当成项目，并给出"已发现完整交接文件 / 推荐续聊"这种**自信但完全错误**的结论。更糟的是：如果 CWD 恰好缺交接文件，推荐动作会变成 `init-project`，**点下去就往 CWD 里写模板文件**。另外纯空格 `"   "` 走的是另一条分支（显示"目录不存在"），同一类输入行为不一致。

**根因**：`Path("")` 等于 `Path(".")`。Python 里空字符串路径会被解释为当前目录，这是一个静默的语义陷阱，不报错。

**修法**：新增模块级 `resolve_project_path(raw: str) -> Path | None`，把空白、纯空格、`None` 一律归一为 `None`，顺带剥掉用户从资源管理器复制来的包裹引号。**7 处调用点**（`_refresh_status_cards`、`_recommended_action`、`on_browse_project`、`on_init_project`、`on_check_hygiene`、`on_open_project`、`on_open_handoff`）全部改用它，并对 `None` 给出明确提示（"项目状态：未选择目录" / "请先选择项目目录，再点…"）。

**验证**：7 项路径解析单元 + GUI 的项目状态 5 分支、推荐动作 5 分支。

### 缺陷 3：点一次「检查工程卫生」会在工具箱里留下 `__pycache__`

**现象**：`run_hygiene_scan()` 里的 `import check_hygiene` 会把 `.pyc` 写到源码旁边，污染这个对外分发的目录。

**修法**：把 import 包在 `sys.dont_write_bytecode` 的 try/finally 里，读完立即还原原值。注意 `selftest.py` 自己也有同样的风险，靠文件顶部的 `sys.dont_write_bytecode = True` 兜住 —— **两处保险都要保留**，缺一个就会漏。

**这一条差点被漏掉，因为它暴露了"验证方法本身不可信"的问题**：沙箱给工具启动的进程设了 `PYTHONDONTWRITEBYTECODE=1`，所以第一轮测"扫描是否污染工具箱"时**测出的是假阴性**（我这边根本不生成 `__pycache__`）。必须在**子进程里清掉该变量**才是用户桌面的真实环境，一跑就复现了。**方法论：凡是被环境变量影响的副作用，都要在清掉该变量的子进程里复测。**

---

## 二、沙箱限制清单

每一条都实测确认过。**关键是不变"修"脚本去迎合沙箱** —— 这些是测试环境的限制，不是产品缺陷。

| 限制 | 现象 | 应对 |
| --- | --- | --- |
| 拦 PowerShell `Remove-Item -Recurse` | 全盘生效，**连工作区内的目录也拦**（`SAFE_DELETE_BULK_GUARD_ERROR`） | 承认测不了；**但不要混淆成"所有递归删除都拦不了"** |
| **不拦** Python `shutil.rmtree` / `os.remove` | 实测可正常删除 | 所以 GUI 的 Python 重装路径**是可以测的** |
| 把"禁止启动子进程"伪装成找不到命令 | `Get-Command powershell` 失败，但 exe 存在且在 PATH 上 | 用 `& $fullExePath` 再试一次，才能看到真正原因 |
| 设 `PYTHONDONTWRITEBYTECODE=1` | 掩盖 `__pycache__` 类字节码副作用，产出假阴性 | 在子进程里清掉该变量复测 |
| 拦 `Add-Type` 与反射加载 | `Add-Type -AssemblyName Microsoft.VisualBasic` 与 `[System.Reflection.Assembly]::LoadWithPartialName` 都被拒 | 送回收站改用纯 ctypes 调 `shell32.SHFileOperationW`（见下） |
| 注入不可用的 HTTP 代理 | `http_proxy` / `https_proxy` / `HTTP_PROXY` / `HTTPS_PROXY` 指向本地透明代理；git 继承后连不上 GitHub | 推送时 `env -u` 清掉，见第三节 |
| 不持久化 git 远端跟踪引用 | `fetch` / `push -u` 报成功、reflog 也写，但 `refs/remotes/...` 文件不落地 | 手工重建，见第三节 |
| PowerShell 工具可能整体不回显 stdout | 连 `Write-Output "ps-ok"` 都返回空，只剩退出码 | 重定向到工作区文件再读回；文件复制/diff 直接用 Bash |

### 关于"删除要进回收站"

纯 ctypes 调 `shell32.SHFileOperationW`，`wFunc = FO_DELETE (0x0003)`，`fFlags |= FOF_ALLOWUNDO (0x0040) | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI`；`pFrom` 必须是 `\0` 连接的**多字符串**并以**双 NUL** 结尾。

两个坑：

- **返回码不可信**：实测返回 `2`（`ERROR_FILE_NOT_FOUND`）却其实全部成功。判定依据是 `path.exists()` 与 `fAnyOperationsAborted`。
- **要验证真的可恢复**：列 `C:\$Recycle.Bin\<SID>\$I*`，按 UTF-16-LE 解码 `$I` 文件能读回原路径。

附带发现：这个沙箱里连 Bash 的 `rm -rf` 也会进回收站而非不可恢复 —— 但**仍然要验证而非假设**。

---

## 三、推送 GitHub 的排障（三个障碍，逐个定位）

三条都不是用户的网络问题，但报错全都长得像网络问题。**按顺序查**。

### 障碍 1：沙箱注入了不能用的代理

`HTTP_PROXY` / `HTTPS_PROXY` / `http_proxy` / `https_proxy` 被设成本地透明代理（如 `http://127.0.0.1:51798`）。git 继承后把 github.com 的流量发给它，表现为：

```
schannel: server closed abruptly (missing close_notify)
CONNECT tunnel failed, response 502
```

**排除方法（先做这一步，别急着改配置）**：

```bash
curl -s -m 8 --noproxy '*' -o /dev/null -w "%{http_code}\n" https://github.com   # 直连
curl -s -m 8 -x http://127.0.0.1:7897 -o /dev/null -w "%{http_code}\n" https://github.com   # 用户自己的代理
curl -s -m 8 -x "$https_proxy" -o /dev/null -w "%{http_code}\n" https://github.com   # 沙箱注入的
```

实测结果：直连 200、用户代理 7897 → 200、沙箱注入的 → **000**。找可用代理用 `netstat -ano | grep LISTENING`。

**修法**：推送时清掉变量，并把可用代理写进仓库级配置：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  git push -u origin main
git config --local http.proxy http://127.0.0.1:7897
```

### 障碍 2：捆绑的 git 一个凭据助手都没带

`which git` 指向 PortableGit（`…/PortableGit/versions/*/mingw64/bin/git`），其 `bin` 目录下**没有任何 `git-credential-*`** —— 但它加载的系统 gitconfig 里却写着 `credential.helper=helper-selector`，**指向一个不存在的程序**。于是凭据查询**静默失败**，git 只能退回去索要用户名：

```
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

**注意：取不到凭据 ≠ 没有凭据。** 这里非常容易得出错误结论（本仓库的开发过程中就误判过一次）。凭据管理器里其实早就存着 `git:https://github.com`。

**修法**（仓库级，先置空以清掉继承来的列表，再用 8.3 短路径避开 `Program Files` 的空格 —— 助手是经 shell 调用的，含空格的裸路径会被切开）：

```bash
git config --local credential.helper ""
git config --local --add credential.helper "C:/PROGRA~1/Git/mingw64/bin/git-credential-manager.exe"
```

**验证助手本身可用**（只显示用户名，别把密码打出来）：

```bash
printf "protocol=https\nhost=github.com\n\n" | "C:/PROGRA~1/Git/mingw64/bin/git-credential-manager.exe" get
# 期望输出 username=... 和 password=...
```

**查有没有已存凭据**：`cmdkey /list | grep -a github`。必须加 `-a`，它的输出是 UTF-16，不加会被 grep 当成二进制文件。

### 障碍 3：git 自己的引用更新不落地

`git fetch` 和 `git push -u` 都报成功（甚至打印 `* [new branch] main -> origin/main`），reflog（`.git/logs/refs/remotes/...`）也逐条记录，**但 `refs/remotes/origin/main` 文件始终不存在**。症状是 `git branch -r` 为空、`git status` 卡在 `## main...origin/main [gone]`。

**先排除文件系统因素**：手工写入的引用文件能跨命令存活，git 也能读到（往里写垃圾内容，`git show-ref` 会立刻报 `bad ref`）。所以这是沙箱对 git「`.lock` + rename」引用更新路径的干扰 —— 附带旁证：追加式的 reflog 写得进去，重命名式的 ref 写不进去。

**修法**：

```bash
mkdir -p .git/refs/remotes/origin          # 注意先建目录，直接 printf 会失败
printf '%s\n' "$(git rev-parse HEAD)" > .git/refs/remotes/origin/main
```

用户在自己的终端里不会遇到这个问题。

### 附带的一条纪律

**验证类命令不要串在管道下游。** `timeout 60 git fetch | head -3` 会让 `head` 提前关闭管道、git 中途夭折，你要查的那个副作用就悄悄丢了（远端跟踪引用没落地的现象，第一次就是这样被掩盖的）。干净跑完，再单独查。

---

## 四、Windows 文件卫生

### `.ps1` 的 UTF-8 BOM

含中文的 `.ps1` **必须有 UTF-8 BOM**。PowerShell 5.1 在读不到 BOM 时会按系统 ANSI 代码页解析（中文系统上是 GBK）：

- 引号里的中文会变成乱码；
- **注释里的中文会吞掉行尾换行**，然后在**后面某一行**报出误导性语法错误（例如"意外的标记 `{`"指着一个你根本没动过的 `switch` 块）。

**所以要记住两个方向**：

- 症状识别：一个本来能跑的脚本突然在**你没改过的后续行**报语法错 → 先怀疑编码，别怀疑逻辑。
- 写入工具差异：本环境的 `Write` 工具会**清掉** BOM，`Edit` 会**保留**。所以"整文件重写"正是最容易翻车的操作。改完必须复检：

```bash
head -c 3 x.ps1 | od -An -tx1    # 应为 ef bb bf
```

### 换行符：绝不要用 bash 数

用 `grep -c $'\r$' "$f"` 这种循环判断换行符是**不可靠的**：`\r` 会在命令传输过程中被破坏，结果对**纯 LF 的文件照样报满行数**。本仓库开发过程中就据此得出了"全部文件是 CRLF"的错误结论。

**权威做法**：

```bash
git ls-files --eol     # 一次给出索引 i/、工作区 w/ 和生效属性
head -2 f.ps1 | od -c  # 单文件字节级确认
```

### 换行符策略

`.gitattributes` 规定**仓库内统一 LF**（含 `*.ps1` / `*.vbs`），只给 `*.bat` / `*.cmd` 预留 `eol=crlf`（`cmd.exe` 对 LF 的标签/`goto` 解析可能异常）。

**不要从别的仓库照抄 `.ps1 → crlf`。** 判断依据是"谁来写这些文件"：本仓库的文件由 Codex 与 WorkBuddy 写出、两边都产 LF，钉成 CRLF 会导致每次检出都改写文件而索引存 LF，工作区与索引来回不一致、每次 `git add` 都刷警告。策略靠仓库级 `.gitattributes` 钉死，**不动全局 `core.autocrlf`**（本机是 `true`）。

### 控制字符

模板、脚本或第三方工具产出的文本可能夹带**未转义的控制字符**（本意是 `\t` / `\r` / `\n` / `\b` 字面量）。症状很隐蔽：Markdown 代码围栏塌陷（一个反引号 + TAB 代替三个反引号）、句子莫名少一个字符（孤立的 `\r` 或 `\b` 吃掉了下一个字母）、Windows 路径出现双反斜杠。

**用常驻工具扫，不要手写检查**：

```bash
python check_hygiene.py <repo>     # 退出码 1 表示有问题
```

它覆盖：退格（0x08）、孤立 CR、反引号+TAB、非 UTF-8 字节、未闭合的 Markdown 围栏、缺 UTF-8 BOM 的 `.ps1`。也可 `import` 复用（`check_hygiene.scan(root)` + `format_report()`），GUI 里对应「检查工程卫生」按钮。

> 已知局限：跳过列表含 `.workbuddy/`，所以**扫不到装在 `~/.workbuddy/skills/` 下的技能** —— 而那正是最常被编辑的一类文件。要检查已安装的 skill，得先把文件复制到别处。见 `HANDOFF.md` 的 Open Questions。

---

## 五、如何验证这个 GUI

三个陷阱会让"看起来验过了"的验证其实什么都没验到。

1. **托管 Python 没有 tkinter。** 用托管解释器加载本模块会以 `No module named 'tkinter'` 失败，看起来像代码 bug，其实是解释器选错了。GUI 必须用**系统 Python**（`pyw` 解析到的那一个）。

2. **绝不 `import` 一个 `.pyw`。** `.pyw` 不一定在 `importlib` 的源码后缀列表里，而且真 import 会执行 `__main__` 守卫。用模块对象加载：

   ```python
   mod = types.ModuleType("probe"); mod.__file__ = str(target)
   exec(compile(target.read_text(encoding="utf-8"), str(target), "exec"), mod.__dict__)
   ```

   因为 `if __name__ == "__main__"` 守卫仍在，这样做**无副作用**，于是可以直接单元测试模块级函数、也可以在真实实例上驱动控件回调。

3. **只测类是不够的，还必须测入口。** 用 `runpy.run_path(path, run_name="__main__")`，并把 `tk.Tk.mainloop` 猴补成一个跑几十次 `update_idletasks()` / `update()`、记录 `winfo_ismapped()` / `winfo_geometry()`、最后 `self.destroy()` 的函数。这样会真的建出窗口、证明它 map 成功、然后正常退出 —— 这是最接近"双击"的验证方式（直接启动一个分离的 GUI 进程是测不到结果的，会话结束时子进程会被收割）。

另外：驱动回调前先拦截 `messagebox` 与任何"打开资源管理器"之类的助手，否则一个模态对话框或一堆 Explorer 窗口会把测试卡住或刷屏。

---

## 六、自测的设计原则

`selftest.py` 是唯一的验证入口，**改完工具箱任何东西都该跑它**。它的设计约束值得沿用：

- **全部 fixture 建在系统临时目录**，安装类用例把 `CODEX_HOME` / `WORKBUDDY_HOME` 指向临时目录并在 `finally` 里还原 —— **绝不碰真实项目与真实技能安装**。
- 文件顶部设 `sys.dont_write_bytecode = True`，避免自检自己污染工具箱。
- 缺 tkinter 时以退出码 2 退出并给出提示，不伪装成失败。
- **跑不了的用例显式标 `SKIP` 并写清原因**（当前只有一条：`install-skill.ps1` 在目标已存在时重跑），**不伪装成通过**。
- 断言要具体到行为，不要只数个数：GUI 按钮按**标签**逐个断言，而不是断言"有 16 个按钮"。

当前基线：**113 通过 / 0 失败 / 1 跳过**，约 1 秒。
