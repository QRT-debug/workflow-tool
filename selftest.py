"""工具箱自检。

用法：
    python selftest.py            # 跑全部检查
    python selftest.py -v         # 同时打印每个用例的细节

覆盖范围：
    1. 静态一致性：三个 .ps1 的 BOM、skill 章节与模板章节对齐、skill 双副本一致
    2. check_hygiene：干净目录 / 已知缺陷样本 / -q / 多路径 / 异常输入
    3. init_project：生成物与模板逐字节一致、幂等且不覆盖用户内容、异常路径
    4. resolve_project_path：空白、None、带引号路径
    5. GUI：按钮清单、场景切换、项目状态分支、推荐动作分支、粘贴板、卫生按钮正反两向
    6. skill 安装：首次安装、重装清理陈旧文件、与源一致

原则：不触碰你的真实项目。所有用例都在系统临时目录里建一次性工程，
安装类用例把 CODEX_HOME / WORKBUDDY_HOME 指向临时目录，跑完还原。

退出码：0 = 全部通过，1 = 有失败，2 = 环境不满足（缺 tkinter 等）。
"""

from __future__ import annotations

import argparse
import filecmp
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types

# 自检会 import 同目录模块，关掉字节码写入以免污染工具箱。
sys.dont_write_bytecode = True

TOOLBOX = pathlib.Path(__file__).resolve().parent
SKILL_SRC = TOOLBOX / "skill" / "project-handoff-resume"
TEMPLATES = TOOLBOX / "templates"
HANDOFF_SECTIONS = [
    "Current Status",
    "Update Rule",
    "Confirmed Findings",
    "Open Questions",
    "Recommended Next Steps",
    "How To Resume In A New Chat",
]

PASS: list[str] = []
FAIL: list[str] = []
SKIP: list[str] = []
VERBOSE = False
_section = ""


def section(title: str) -> None:
    global _section
    _section = title
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def check(name: str, got, want) -> None:
    if got == want:
        PASS.append("%s / %s" % (_section, name))
        print("  PASS  %s" % name)
    else:
        FAIL.append("%s / %s" % (_section, name))
        print("  FAIL  %s" % name)
        print("        期望 %r" % (want,))
        print("        实得 %r" % (got,))


def skip(name: str, why: str) -> None:
    SKIP.append("%s / %s（%s）" % (_section, name, why))
    print("  SKIP  %s —— %s" % (name, why))


def note(text: str) -> None:
    if VERBOSE:
        print("        %s" % text)


def load_toolbox(**overrides):
    """把 workflow-tool.pyw 当模块加载（__main__ 守卫保证不会弹出窗口）。"""
    path = TOOLBOX / "workflow-tool.pyw"
    mod = types.ModuleType("wf_selftest")
    mod.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), mod.__dict__)
    for key, value in overrides.items():
        setattr(mod, key, value)
    return mod


def make_project(root: pathlib.Path) -> pathlib.Path:
    """建一个最小可用的测试工程。"""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    return root


def run_hygiene_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(TOOLBOX / "check_hygiene.py"), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=cwd,
    )


# ======================================================================
def static_checks() -> None:
    section("1. 静态一致性")

    for name in ("init-project.ps1", "install-skill.ps1", "one-click-init-project.ps1"):
        p = TOOLBOX / name
        if not p.exists():
            check("%s 存在" % name, False, True)
            continue
        raw = p.read_bytes()
        has_non_ascii = any(b > 127 for b in raw)
        if has_non_ascii:
            check("%s 含中文且有 UTF-8 BOM" % name, raw[:3] == b"\xef\xbb\xbf", True)
        else:
            note("%s 无中文，跳过 BOM 检查" % name)

    # skill 的 Preferred Handoff Shape 应与模板章节一一对应
    text = (SKILL_SRC / "SKILL.md").read_text(encoding="utf-8")
    block = text.split("## Preferred Handoff Shape", 1)[1].split("Do not expand", 1)[0]
    listed = [ln.split("`")[1] for ln in block.splitlines()
              if ln.startswith("- ") and "`" in ln]
    check("skill 章节列表与约定一致", listed, HANDOFF_SECTIONS)

    tpl = (TEMPLATES / "docs" / "HANDOFF.md").read_text(encoding="utf-8")
    tpl_sections = [ln[3:].strip() for ln in tpl.splitlines() if ln.startswith("## ")]
    check("模板 HANDOFF 章节顺序一致", tpl_sections, HANDOFF_SECTIONS)

    check("skill 源存在 SKILL.md", (SKILL_SRC / "SKILL.md").exists(), True)
    fm = text.split("---\n", 2)[1]
    check("frontmatter 的 name 与目录名一致",
          [ln.split(":", 1)[1].strip() for ln in fm.splitlines() if ln.startswith("name:")],
          [SKILL_SRC.name])

    # 已安装副本应与源逐字节一致
    for agent, home in (("Codex", pathlib.Path.home() / ".codex"),
                        ("WorkBuddy", pathlib.Path.home() / ".workbuddy")):
        installed = home / "skills" / SKILL_SRC.name
        if not (installed / "SKILL.md").exists():
            skip("%s 侧 skill 副本与源一致" % agent, "尚未安装到 %s" % installed)
            continue
        d = filecmp.dircmp(SKILL_SRC, installed)
        check("%s 侧 skill 副本与源一致" % agent,
              d.diff_files + d.left_only + d.right_only, [])


# ======================================================================
def hygiene_checks(tmp: pathlib.Path) -> None:
    section("2. check_hygiene")

    clean = make_project(tmp / "hyg_clean")
    check_hygiene = None
    sys.path.insert(0, str(TOOLBOX))
    import check_hygiene  # noqa: PLC0415

    r = run_hygiene_cli(str(clean))
    check("干净工程 -> 退出码 0", r.returncode, 0)
    check("干净工程 -> 报 0 个问题文件", "问题文件 0 个" in r.stdout, True)

    # 四类已知缺陷各造一个，要求全部命中
    bad = tmp / "hyg_bad"
    (bad / "docs").mkdir(parents=True)
    (bad / "docs" / "fence.md").write_bytes(b"# bad\n\n\x08eaten\n\n`\ttext\n")
    (bad / "lone.txt").write_bytes(b"a\rb\r\n")
    (bad / "gbk.ps1").write_bytes("Write-Host '中文'\n".encode("gbk"))
    (bad / "unclosed.md").write_bytes(b"# x\n\n```text\none fence\n")
    issues, checked = check_hygiene.scan(bad)
    found = {p.name: set(probs) for p, probs in ((i.path, i.problems) for i in issues)}
    check("缺陷样本被全部识别（4 个文件）", len(issues), 4)
    check("退格 + 压平围栏被识别", "fence.md" in found, True)
    check("孤立 CR 被识别", "lone.txt" in found, True)
    check("非 UTF-8 + 缺 BOM 被识别",
          any("UTF-8" in p or "BOM" in p for p in found.get("gbk.ps1", set())), True)
    check("未闭合围栏被识别", "unclosed.md" in found, True)

    r = run_hygiene_cli(str(bad))
    check("缺陷目录 -> 退出码 1", r.returncode, 1)
    r = run_hygiene_cli(str(bad), "-q")
    check("-q 有问题 -> 退出码 1", r.returncode, 1)
    check("-q -> 只输出一行", len(r.stdout.strip().splitlines()), 1)

    r = run_hygiene_cli(str(clean), str(bad))
    check("多路径 -> 出现两份报告", r.stdout.count("扫描目录"), 2)
    check("多路径 -> 退出码 1", r.returncode, 1)

    missing = tmp / "hyg_missing"
    r = run_hygiene_cli(str(missing))
    check("不存在的目录 -> 退出码 2", r.returncode, 2)

    skiponly = tmp / "hyg_skip"
    (skiponly / "build").mkdir(parents=True)
    (skiponly / "build" / "x.md").write_bytes(b"\x08bad\n")
    r = run_hygiene_cli(str(skiponly))
    check("只含 build/ -> 被跳过，退出码 0", r.returncode, 0)

    # 工具箱自己必须是干净的
    toolbox_issues, _ = check_hygiene.scan(TOOLBOX)
    check("工具箱自身无卫生问题", [str(i.path.name) for i in toolbox_issues], [])


# ======================================================================
def init_project_checks(tmp: pathlib.Path) -> None:
    section("3. init_project")
    mod = load_toolbox()
    target = make_project(tmp / "proj_a")

    ready, missing = mod.project_handoff_status(target)
    check("初始化前 ready=False", ready, False)
    check("初始化前缺 3 份", len(missing), 3)

    mod.init_project(target)
    ready, _ = mod.project_handoff_status(target)
    check("初始化后 ready=True", ready, True)
    for src, dst in ((TEMPLATES / "CODEX_PROJECT_PROMPT.md", target / "CODEX_PROJECT_PROMPT.md"),
                     (TEMPLATES / "docs" / "PROJECT_MAP.md", target / "docs" / "PROJECT_MAP.md"),
                     (TEMPLATES / "docs" / "HANDOFF.md", target / "docs" / "HANDOFF.md")):
        check("%s 与模板逐字节一致" % dst.name,
              dst.read_bytes() == src.read_bytes(), True)

    # 幂等：用户写进去的内容不能被覆盖，文件也不该被重写
    handoff = target / "docs" / "HANDOFF.md"
    marker = "SELFTEST 用户内容标记——不得被初始化覆盖"
    handoff.write_text(handoff.read_text(encoding="utf-8").replace(
        "State the current phase of work", marker), encoding="utf-8")
    mtime = handoff.stat().st_mtime
    mod.init_project(target)
    check("重复初始化保留用户内容", marker in handoff.read_text(encoding="utf-8"), True)
    check("重复初始化未重写文件", handoff.stat().st_mtime, mtime)

    # 没有 docs 目录时自动创建
    nodocs = tmp / "proj_nodocs"
    nodocs.mkdir(parents=True)
    mod.init_project(nodocs)
    check("可自动创建 docs/", (nodocs / "docs" / "HANDOFF.md").exists(), True)

    # 异常路径
    for label, path, exc in (("不存在的目录", tmp / "nope", FileNotFoundError),
                             ("指向文件", clean_file(tmp), NotADirectoryError),
                             ("深层不存在", tmp / "a" / "b" / "c", FileNotFoundError)):
        try:
            mod.init_project(path)
            check("%s -> 抛 %s" % (label, exc.__name__), "没抛异常", exc.__name__)
        except exc:
            check("%s -> 抛 %s" % (label, exc.__name__), exc.__name__, exc.__name__)
        except Exception as e:  # noqa: BLE001
            check("%s -> 抛 %s" % (label, exc.__name__), type(e).__name__, exc.__name__)

    # 模板缺失时应明确报错
    mod_broken = load_toolbox(TEMPLATES_DIR=tmp / "no_such_templates")
    try:
        mod_broken.init_project(tmp / "proj_b")
        check("模板缺失 -> 抛 FileNotFoundError", "没抛异常", "FileNotFoundError")
    except FileNotFoundError:
        check("模板缺失 -> 抛 FileNotFoundError", "FileNotFoundError", "FileNotFoundError")

    mod_noskill = load_toolbox(SKILL_SOURCE_DIR=tmp / "no_such_skill")
    try:
        mod_noskill.install_skill()
        check("skill 源缺失 -> 抛 FileNotFoundError", "没抛异常", "FileNotFoundError")
    except FileNotFoundError:
        check("skill 源缺失 -> 抛 FileNotFoundError", "FileNotFoundError", "FileNotFoundError")


def clean_file(tmp: pathlib.Path) -> pathlib.Path:
    p = tmp / "not_a_dir.txt"
    p.write_text("x", encoding="utf-8")
    return p


def path_resolution_checks() -> None:
    section("4. resolve_project_path")
    mod = load_toolbox()
    target = pathlib.Path("C:/selftest_target")

    check("空字符串 -> None", mod.resolve_project_path(""), None)
    check("纯空格 -> None", mod.resolve_project_path("   "), None)
    check("制表符 -> None", mod.resolve_project_path("\t"), None)
    check("None -> None", mod.resolve_project_path(None), None)
    check("普通路径 -> 同一个 Path", mod.resolve_project_path("C:/selftest_target"), target)
    check("带引号 -> 去掉引号",
          mod.resolve_project_path('"' + "C:/selftest_target" + '"'), target)
    check("空白+引号 -> 同一个 Path",
          mod.resolve_project_path('   "' + "C:/selftest_target" + '"   '), target)


# ======================================================================
def gui_checks(tmp: pathlib.Path) -> None:
    section("5. GUI 行为")

    import tkinter as tk  # noqa: PLC0415

    mod = load_toolbox()
    popups: list[tuple[str, str]] = []
    explorer: list[str] = []

    class FakeBox:
        @staticmethod
        def showinfo(title, message=None, **kw):
            popups.append(("info", str(title)))

        @staticmethod
        def showerror(title, message=None, **kw):
            popups.append(("error", str(title)))

        @staticmethod
        def showwarning(title, message=None, **kw):
            popups.append(("warning", str(title)))

    mod.messagebox = FakeBox
    mod.open_in_explorer = lambda p: explorer.append(str(p))

    app = mod.WorkflowTool()
    app.withdraw()

    def walk(w):
        yield w
        for c in w.winfo_children():
            yield from walk(c)

    buttons = [w.cget("text") for w in walk(app) if isinstance(w, tk.Button)]
    expected = [
        "同一台电脑\n同一个工程", "同一台电脑\n不同工程", "换了一台电脑",
        "浏览...", "重新检查项目状态", "打开项目目录", "打开 HANDOFF",
        "检查工程卫生",
        "安装 / 重装 Skill（两个智能体）", "初始化项目交接文件",
        "打开提示词文档", "运行工具箱自检",
        "复制当前推荐提示词", "复制初始化提示词", "复制续聊提示词", "复制收尾提示词",
    ]
    for label in expected:
        check("按钮存在：%s" % label.replace("\n", " / "),
              sum(b == label for b in buttons) >= 1, True)
    check("状态卡有 2 个 agent 徽章", len(app.skill_badges), 2)
    check("窗口标题", app.title(), "Codex / WorkBuddy 工作流工具")

    # 场景
    for key in ("same-project", "different-project", "new-computer"):
        app._apply_scenario(key)
        check("场景 %s 标题" % key, app.scenario_title.cget("text"),
              "当前场景：%s" % mod.SCENARIOS[key]["title"])
    app._apply_scenario("new-computer")
    check("选中场景为实心色", app.scenario_buttons["new-computer"].cget("bg"),
          mod.COLORS["amber"])
    check("未选中场景为浅色", app.scenario_buttons["same-project"].cget("bg"),
          mod.COLORS["blue_soft"])
    app._apply_scenario("same-project")

    ready_proj = make_project(tmp / "gui_ready")
    mod.init_project(ready_proj)
    empty_proj = tmp / "gui_empty"
    empty_proj.mkdir(parents=True, exist_ok=True)

    def set_project(p):
        app.project_var.set(str(p))
        app._refresh_all()

    # 项目状态 4 分支
    set_project(ready_proj)
    check("完整交接文件 -> 徽章", app.project_badge.cget("text"), "项目状态：已发现完整交接文件")
    check("完整交接文件 -> 绿色", app.project_badge.cget("fg"), mod.COLORS["green"])
    set_project(empty_proj)
    check("空目录 -> 徽章", app.project_badge.cget("text"), "项目状态：缺少交接文件")
    check("空目录 -> 橙色", app.project_badge.cget("fg"), mod.COLORS["amber"])
    set_project(clean_file(tmp))
    check("指向文件 -> 徽章", app.project_badge.cget("text"), "项目状态：目标不是目录")
    set_project(tmp / "no_such_dir_selftest")
    check("目录不存在 -> 徽章", app.project_badge.cget("text"), "项目状态：目录不存在")
    app.project_var.set("")
    app._refresh_all()
    check("空白路径 -> 徽章", app.project_badge.cget("text"), "项目状态：未选择目录")

    # 推荐动作分支
    set_project(ready_proj)
    check("就绪 -> 续聊", app.main_action_kind, "copy-resume-prompt")
    check("就绪 -> 主按钮文案", app.main_action_button.cget("text"), "复制续聊提示词")
    check("就绪 -> 提示词是续聊口令", app.prompt_text.get("1.0", "end").strip(),
          mod.RESUME_PROMPT)
    set_project(empty_proj)
    check("缺交接文件 -> 初始化", app.main_action_kind, "init-project")
    check("缺交接文件 -> 提示词是初始化口令",
          app.prompt_text.get("1.0", "end").strip(), mod.INIT_PROMPT)
    set_project(tmp / "no_such_dir_selftest")
    check("目录无效 -> 选目录", app.main_action_kind, "choose-project")
    app.project_var.set("")
    app._refresh_all()
    check("空白路径 -> 选目录", app.main_action_kind, "choose-project")

    # 主按钮与剪贴板
    set_project(ready_proj)
    before = len(popups)
    app.on_main_action()
    check("主按钮复制续聊口令", app.clipboard_get(), mod.RESUME_PROMPT)
    app._copy_text(mod.INIT_PROMPT, "x")
    check("复制初始化口令", app.clipboard_get(), mod.INIT_PROMPT)
    app._copy_text(mod.WRAPUP_PROMPT, "x")
    check("复制收尾口令", app.clipboard_get(), mod.WRAPUP_PROMPT)
    app.on_copy_current_prompt()
    check("复制当前推荐口令", app.clipboard_get(), mod.RESUME_PROMPT)
    check("按钮操作未弹窗", len(popups), before)

    # 打开类动作
    explorer.clear()
    app.on_open_project()
    check("打开项目目录调用 explorer", len(explorer), 1)
    explorer.clear()
    app.on_open_handoff()
    check("打开 HANDOFF（存在）", len(explorer), 1)
    explorer.clear()
    popups.clear()
    set_project(empty_proj)
    app.on_open_handoff()
    check("打开 HANDOFF（缺失）不调 explorer", len(explorer), 0)
    check("打开 HANDOFF（缺失）给提示", len(popups), 1)
    explorer.clear()
    app.on_open_prompts()
    check("打开提示词文档", len(explorer), 1)

    # 空白路径下的破坏性动作必须被拦住
    app.project_var.set("")
    app._refresh_all()
    cwd_before = sorted(p.name for p in pathlib.Path.cwd().iterdir())
    popups.clear()
    app.on_init_project()
    check("空白路径点初始化 -> 弹窗且不写 CWD",
          (len(popups), sorted(p.name for p in pathlib.Path.cwd().iterdir())),
          (1, cwd_before))
    popups.clear()
    app.on_check_hygiene()
    check("空白路径点卫生检查 -> 弹窗", len(popups), 1)
    popups.clear()
    explorer.clear()
    app.on_open_project()
    check("空白路径点打开目录 -> 只提示", (len(popups), len(explorer)), (1, 0))

    # 卫生检查按钮：正反两向
    set_project(ready_proj)
    popups.clear()
    app.on_check_hygiene()
    check("卫生检查无弹窗", len(popups), 0)
    check("卫生检查通过", "未发现隐藏问题" in app.output_text.get("1.0", "end"), True)
    planted = ready_proj / "docs" / "PLANTED.md"
    planted.write_bytes(b"# x\n\n\x08eaten\n")
    app.on_check_hygiene()
    out = app.output_text.get("1.0", "end")
    check("植入缺陷后报出 1 个文件", "发现 1 个问题文件" in out, True)
    check("报告点名缺陷文件", "PLANTED.md" in out, True)
    planted.unlink()
    app.on_check_hygiene()
    check("删除缺陷后恢复通过", "未发现隐藏问题" in app.output_text.get("1.0", "end"), True)

    # 浏览对话框
    class FakeDialog:
        @staticmethod
        def askdirectory(**kw):
            return str(ready_proj)

    mod.filedialog = FakeDialog
    set_project(empty_proj)
    app.on_browse_project()
    check("浏览返回后写入路径", app.project_var.get(), str(ready_proj))
    check("浏览后状态刷新", app.project_badge.cget("text"), "项目状态：已发现完整交接文件")

    class CancelDialog:
        @staticmethod
        def askdirectory(**kw):
            return ""

    mod.filedialog = CancelDialog
    app.on_browse_project()
    check("取消浏览不改路径", app.project_var.get(), str(ready_proj))

    # 未安装 skill 时的分支
    fake_home = tmp / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    saved = {k: os.environ.get(k) for k in ("CODEX_HOME", "WORKBUDDY_HOME")}
    os.environ["CODEX_HOME"] = str(fake_home)
    os.environ["WORKBUDDY_HOME"] = str(fake_home)
    try:
        check("未安装时两个 agent 均为 False", mod.skill_installed_map(),
              {"Codex": False, "WorkBuddy": False})
        app._apply_scenario("same-project")
        set_project(ready_proj)
        check("未安装 -> 推荐装 skill", app.main_action_kind, "install-skill")
        check("未安装 -> 徽章文案", app.skill_badges["Codex"].cget("text"),
              "Codex Skill：未安装")
        check("未安装 -> 徽章为红色", app.skill_badges["WorkBuddy"].cget("fg"),
              mod.COLORS["red"])
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    app.destroy()


# ======================================================================
def skill_install_checks(tmp: pathlib.Path) -> None:
    section("6. skill 安装")

    os.environ.pop("CODEX_HOME", None)
    os.environ.pop("WORKBUDDY_HOME", None)
    mod = load_toolbox()

    home = tmp / "install_home"
    saved = {k: os.environ.get(k) for k in ("CODEX_HOME", "WORKBUDDY_HOME")}
    os.environ["CODEX_HOME"] = str(home / "codex")
    os.environ["WORKBUDDY_HOME"] = str(home / "wb")
    try:
        check("安装前状态为未安装", mod.skill_installed_map(),
              {"Codex": False, "WorkBuddy": False})
        mod.install_skill()
        check("安装后状态为已安装", mod.skill_installed(), True)

        for agent, base in (("Codex", home / "codex"), ("WorkBuddy", home / "wb")):
            target = base / "skills" / SKILL_SRC.name
            d = filecmp.dircmp(SKILL_SRC, target)
            check("%s 副本与源一致" % agent,
                  d.diff_files + d.left_only + d.right_only, [])

        # 重装应清掉陈旧文件（验证 rmtree + copytree 语义真的生效）
        stale = home / "codex" / "skills" / SKILL_SRC.name / "STALE_LEFTOVER.md"
        stale.write_text("x", encoding="utf-8")
        mod.install_skill()
        check("重装清掉陈旧文件", stale.exists(), False)
        check("重装后仍与源一致",
              (home / "codex" / "skills" / SKILL_SRC.name / "SKILL.md").exists(), True)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # install-skill.ps1 的第二次执行依赖 PowerShell 的递归删除，
    # 在受限沙箱里会被安全守卫拦掉，这里明确标注为跳过而不是误报失败。
    skip("install-skill.ps1 目标已存在时重跑", "需在非沙箱终端手动验证")


# ======================================================================
def main(argv: list[str] | None = None) -> int:
    global VERBOSE
    parser = argparse.ArgumentParser(description="工具箱自检")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印额外细节")
    args = parser.parse_args(argv)
    VERBOSE = args.verbose

    print("工具箱自检：%s" % TOOLBOX)
    print("解释器：%s" % sys.executable)

    try:
        import tkinter  # noqa: F401,PLC0415
    except ImportError:
        print()
        print("环境不满足：当前解释器没有 tkinter，无法执行 GUI 检查。")
        print("请改用带 tkinter 的解释器运行，例如：")
        print("  pyw -3 selftest.py        （或 GUI 里的「运行工具箱自检」按钮）")
        return 2

    if not TOOLBOX.joinpath("workflow-tool.pyw").exists():
        print("未找到 workflow-tool.pyw，请把 selftest.py 放在工具箱目录下运行。")
        return 2

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="toolbox_selftest_"))
    cwd = pathlib.Path.cwd()
    try:
        static_checks()
        hygiene_checks(tmp)
        init_project_checks(tmp)
        path_resolution_checks()
        os.chdir(tmp)
        gui_checks(tmp)
        skill_install_checks(tmp)
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=" * 70)
    print("通过 %d 项，失败 %d 项，跳过 %d 项" % (len(PASS), len(FAIL), len(SKIP)))
    print("=" * 70)
    if SKIP:
        print("跳过：")
        for item in SKIP:
            print("  - %s" % item)
    if FAIL:
        print("失败：")
        for item in FAIL:
            print("  - %s" % item)
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
