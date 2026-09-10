import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


TEMPLATE_ROOT = Path(__file__).resolve().parent
SKILL_SOURCE_DIR = TEMPLATE_ROOT / "skill" / "project-handoff-resume"
TEMPLATES_DIR = TEMPLATE_ROOT / "templates"
PROMPTS_FILE = TEMPLATE_ROOT / "PROMPTS.md"

HANDOFF_FILES = [
    Path("CODEX_PROJECT_PROMPT.md"),
    Path("docs/PROJECT_MAP.md"),
    Path("docs/HANDOFF.md"),
]

# 这套工作流同时适配两个智能体，skill 需要分别装到它们各自的技能目录。
AGENT_NAMES = ["Codex", "WorkBuddy"]

RESUME_PROMPT = "使用 project-handoff-resume，然后继续这个工程。"
INIT_PROMPT = (
    "先帮助我填写 CODEX_PROJECT_PROMPT.md、docs/PROJECT_MAP.md、docs/HANDOFF.md。\n"
    "请先阅读这个工程的入口文件、主流程和关键模块，然后把这三个文件初始化成可续聊状态。"
)
WRAPUP_PROMPT = (
    "在结束这轮之前，请刷新 docs/HANDOFF.md。\n"
    "如果架构理解有变化，也同步更新 docs/PROJECT_MAP.md。\n"
    "最后告诉我这次更新了哪些交接信息。"
)

COLORS = {
    "bg": "#f4f7fb",
    "card": "#ffffff",
    "line": "#d7e0ea",
    "text": "#1e293b",
    "muted": "#5b6b7f",
    "blue": "#2563eb",
    "blue_soft": "#dbeafe",
    "green": "#15803d",
    "green_soft": "#dcfce7",
    "amber": "#b45309",
    "amber_soft": "#fef3c7",
    "red": "#b91c1c",
    "red_soft": "#fee2e2",
}

SCENARIOS = {
    "same-project": {
        "title": "同一台电脑 + 同一个工程",
        "color": COLORS["blue"],
        "soft": COLORS["blue_soft"],
        "steps": [
            "如果这台电脑没有装过 workflow skill，先安装一次（Codex 和 WorkBuddy 会一起装好）。",
            "确认下面的项目目录就是你当前这个工程。",
            "如果项目已经有交接文件，一般不用再初始化。",
            "最后复制推荐提示词，去 Codex 或 WorkBuddy 里直接发。"
        ],
    },
    "different-project": {
        "title": "同一台电脑 + 不同工程",
        "color": COLORS["green"],
        "soft": COLORS["green_soft"],
        "steps": [
            "这台电脑通常已经装过 skill，不确定就重装一次。",
            "先选择新的项目目录。",
            "如果新项目没有交接文件，就初始化项目交接文件。",
            "再根据推荐提示词去 Codex 或 WorkBuddy 开新对话。"
        ],
    },
    "new-computer": {
        "title": "换了一台电脑",
        "color": COLORS["amber"],
        "soft": COLORS["amber_soft"],
        "steps": [
            "第一步必须先安装 / 重装 Skill。",
            "然后选择你的项目目录。",
            "如果项目没有交接文件，初始化项目交接文件。",
            "最后复制推荐提示词，去 Codex 或 WorkBuddy 开新对话。"
        ],
    },
}


def agent_home(agent: str) -> Path:
    # 返回指定智能体的配置根目录。
    # CODEX_HOME 是 Codex 官方支持的环境变量。
    # WORKBUDDY_HOME 不是 WorkBuddy 的官方变量，WorkBuddy 始终只读 ~/.workbuddy，
    # 这里仅为自测留口子，正常使用不要设置它，否则安装位置会与实际读取位置脱节。
    if agent == "Codex":
        env_key, default_dir = "CODEX_HOME", Path.home() / ".codex"
    else:
        env_key, default_dir = "WORKBUDDY_HOME", Path.home() / ".workbuddy"
    return Path(os.environ[env_key]) if env_key in os.environ else default_dir


def skill_target_dir(agent: str) -> Path:
    return agent_home(agent) / "skills" / "project-handoff-resume"


def skill_installed_map() -> dict:
    # 分别统计每个智能体是否已经装好这个 skill。
    return {agent: (skill_target_dir(agent) / "SKILL.md").exists() for agent in AGENT_NAMES}


def skill_installed() -> bool:
    # 两个智能体都装好才算就绪，否则主按钮会引导补齐。
    return all(skill_installed_map().values())


def install_skill() -> str:
    if not SKILL_SOURCE_DIR.exists():
        raise FileNotFoundError(f"未找到 skill 源目录：\n{SKILL_SOURCE_DIR}")

    lines = []
    for agent in AGENT_NAMES:
        target_dir = skill_target_dir(agent)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        if target_dir.exists():
            shutil.rmtree(target_dir)

        shutil.copytree(SKILL_SOURCE_DIR, target_dir)
        lines.append(f"已安装到 {agent}：\n{target_dir}")

    lines.append("")
    lines.append("两个智能体共用同一份 skill 源，两份副本内容完全一致。")
    return "\n".join(lines)


def project_handoff_status(project_root: Path) -> tuple[bool, list[Path]]:
    missing = [rel for rel in HANDOFF_FILES if not (project_root / rel).exists()]
    return len(missing) == 0, missing


def resolve_project_path(raw: str) -> Path | None:
    # 注意：Path("") 会变成当前目录（"."），那样就会把 CWD 误当成项目目录，
    # 甚至在点「初始化」时往 CWD 里写交接文件。所以空白输入一律视为「未选择」。
    # 顺带容忍用户从资源管理器复制过来的带引号路径。
    text = (raw or "").strip().strip('"').strip()
    return Path(text) if text else None


def init_project(project_path: Path) -> str:
    if not project_path.exists():
        raise FileNotFoundError(f"项目目录不存在：\n{project_path}")

    if not project_path.is_dir():
        raise NotADirectoryError(f"目标不是目录：\n{project_path}")

    docs_dir = project_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    operations = []
    copies = [
        (TEMPLATES_DIR / "CODEX_PROJECT_PROMPT.md", project_path / "CODEX_PROJECT_PROMPT.md"),
        (TEMPLATES_DIR / "docs" / "PROJECT_MAP.md", docs_dir / "PROJECT_MAP.md"),
        (TEMPLATES_DIR / "docs" / "HANDOFF.md", docs_dir / "HANDOFF.md"),
    ]

    for src, dst in copies:
        if not src.exists():
            raise FileNotFoundError(f"模板文件不存在：\n{src}")
        if dst.exists():
            operations.append(f"跳过已存在：{dst}")
        else:
            shutil.copy2(src, dst)
            operations.append(f"已创建：{dst}")

    operations.extend(
        [
            "",
            "下一步建议：",
            "1. 在 Codex 或 WorkBuddy 中打开这个项目",
            "2. 如果这是刚初始化的新项目，先发送“初始化提示词”",
            "3. 如果项目已经有交接文件，发送“续聊提示词”",
        ]
    )
    return "\n".join(operations)


def open_in_explorer(path: Path) -> None:
    subprocess.run(["explorer", str(path)], check=False)


def run_hygiene_scan(project_root: Path) -> tuple[str, int]:
    # 调用同目录下的 check_hygiene 扫描项目，返回（报告文本，问题文件数）。
    # 延迟导入：检查逻辑改动后不必重启主程序，也不会拖慢界面启动。
    if str(TEMPLATE_ROOT) not in sys.path:
        sys.path.insert(0, str(TEMPLATE_ROOT))

    # 临时关掉字节码写入，否则第一次扫描会在工具箱目录里留下 __pycache__。
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import check_hygiene
    finally:
        sys.dont_write_bytecode = previous

    roots = [project_root]
    per_root = [check_hygiene.scan(project_root)]
    return check_hygiene.format_report(roots, per_root)


class WorkflowTool(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Codex / WorkBuddy 工作流工具")
        self.geometry("1020x760")
        self.minsize(980, 700)
        self.configure(bg=COLORS["bg"])

        self.project_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.status_var = tk.StringVar(value="先选择你的情况，再按照主按钮提示往下点。")
        self.project_state_var = tk.StringVar()
        self.recommendation_var = tk.StringVar()
        self.scenario_key = "same-project"
        self.main_action_kind = "install-skill"

        self._build_ui()
        self._apply_scenario("same-project")
        self._refresh_all()
        self.after(0, self._expand_window_on_start)

    def _card(self, parent: tk.Widget, title: str) -> tk.LabelFrame:
        return tk.LabelFrame(
            parent,
            text=title,
            padx=14,
            pady=12,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 10, "bold"),
            bd=1,
            relief="solid",
        )

    def _build_ui(self) -> None:
        root = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=16)
        root.pack(fill="both", expand=True)

        hero = tk.Frame(root, bg=COLORS["card"], bd=1, relief="solid", highlightthickness=0)
        hero.pack(fill="x")
        tk.Label(hero, text="Codex / WorkBuddy 工作流工具", font=("Microsoft YaHei UI", 20, "bold"), bg=COLORS["card"], fg=COLORS["text"]).pack(
            anchor="w", padx=18, pady=(16, 4)
        )
        tk.Label(
            hero,
            text="目标：你不需要记命令。只要选场景、选项目目录，然后一直点主按钮。Skill 会同时装给 Codex 和 WorkBuddy。",
            font=("Microsoft YaHei UI", 10),
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=18, pady=(0, 16))

        top = tk.Frame(root, bg=COLORS["bg"])
        top.pack(fill="x", pady=(14, 0))

        left = tk.Frame(top, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(top, bg=COLORS["bg"], width=360)
        right.pack(side="left", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        self._build_scenario_card(left)
        self._build_project_card(left)
        self._build_action_card(left)
        self._build_prompt_card(left)

        self._build_status_card(right)
        self._build_output_card(right)

        footer = tk.Label(root, textvariable=self.status_var, anchor="w", bg=COLORS["bg"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        footer.pack(fill="x", pady=(12, 0))

    def _build_scenario_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "第一步：选择你的情况")
        card.pack(fill="x")

        row = tk.Frame(card, bg=COLORS["card"])
        row.pack(fill="x")

        self.scenario_buttons = {}
        configs = [
            ("same-project", "同一台电脑\n同一个工程"),
            ("different-project", "同一台电脑\n不同工程"),
            ("new-computer", "换了一台电脑"),
        ]
        for idx, (key, label) in enumerate(configs):
            btn = tk.Button(
                row,
                text=label,
                width=18,
                height=3,
                font=("Microsoft YaHei UI", 10, "bold"),
                command=lambda k=key: self._apply_scenario(k),
                relief="flat",
                cursor="hand2",
            )
            btn.grid(row=0, column=idx, padx=(0 if idx == 0 else 10, 0), sticky="nsew")
            row.columnconfigure(idx, weight=1)
            self.scenario_buttons[key] = btn

        self.scenario_title = tk.Label(card, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 11, "bold"))
        self.scenario_title.pack(anchor="w", pady=(14, 6))

        self.scenario_text = tk.Text(card, height=6, wrap="word", font=("Microsoft YaHei UI", 10), bd=0, bg=COLORS["card"], fg=COLORS["text"])
        self.scenario_text.pack(fill="x")
        self.scenario_text.configure(state="disabled")

    def _build_project_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "第二步：确认项目目录")
        card.pack(fill="x", pady=(14, 0))

        row = tk.Frame(card, bg=COLORS["card"])
        row.pack(fill="x")
        tk.Label(row, text="项目目录：", bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 10)).pack(side="left")
        tk.Entry(row, textvariable=self.project_var, font=("Consolas", 10), bd=1, relief="solid").pack(side="left", fill="x", expand=True, padx=8)
        tk.Button(row, text="浏览...", width=10, command=self.on_browse_project, relief="flat", bg="#e2e8f0", cursor="hand2").pack(side="left")

        tk.Label(card, textvariable=self.project_state_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 10)).pack(
            anchor="w", pady=(12, 4)
        )

        row2 = tk.Frame(card, bg=COLORS["card"])
        row2.pack(fill="x", pady=(4, 0))
        tk.Button(row2, text="重新检查项目状态", width=16, command=self._refresh_all, relief="flat", bg="#e2e8f0", cursor="hand2").pack(side="left")
        tk.Button(row2, text="打开项目目录", width=14, command=self.on_open_project, relief="flat", bg="#e2e8f0", cursor="hand2").pack(side="left", padx=8)
        tk.Button(row2, text="打开 HANDOFF", width=14, command=self.on_open_handoff, relief="flat", bg="#e2e8f0", cursor="hand2").pack(side="left")

        row3 = tk.Frame(card, bg=COLORS["card"])
        row3.pack(fill="x", pady=(8, 0))
        tk.Button(row3, text="检查工程卫生", width=16, command=self.on_check_hygiene, relief="flat", bg="#e2e8f0", cursor="hand2").pack(side="left")
        tk.Label(
            row3,
            text="扫描控制字符、非 UTF-8 字节、代码围栏未闭合、PS 脚本缺 BOM",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left", padx=8)

    def _build_action_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "第三步：跟着主按钮点")
        card.pack(fill="x", pady=(14, 0))

        self.recommend_label = tk.Label(card, textvariable=self.recommendation_var, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 11, "bold"))
        self.recommend_label.pack(anchor="w", pady=(0, 10))

        self.main_action_button = tk.Button(
            card,
            text="主按钮",
            height=3,
            font=("Microsoft YaHei UI", 12, "bold"),
            relief="flat",
            cursor="hand2",
            command=self.on_main_action,
        )
        self.main_action_button.pack(fill="x")

        aux = tk.Frame(card, bg=COLORS["card"])
        aux.pack(fill="x", pady=(10, 0))
        tk.Button(aux, text="安装 / 重装 Skill（两个智能体）", width=26, command=self.on_install_skill, relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left"
        )
        tk.Button(aux, text="初始化项目交接文件", width=18, command=self.on_init_project, relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left", padx=8
        )

        aux2 = tk.Frame(card, bg=COLORS["card"])
        aux2.pack(fill="x", pady=(8, 0))
        tk.Button(aux2, text="打开提示词文档", width=16, command=self.on_open_prompts, relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left"
        )
        tk.Button(aux2, text="运行工具箱自检", width=16, command=self.on_run_selftest, relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left", padx=8
        )

    def _build_prompt_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "第四步：把这句发给 Codex 或 WorkBuddy")
        card.pack(fill="both", expand=True, pady=(14, 0))

        self.prompt_title = tk.Label(card, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 11, "bold"))
        self.prompt_title.pack(anchor="w")

        self.prompt_text = tk.Text(card, height=5, wrap="word", font=("Microsoft YaHei UI", 10), bd=1, relief="solid")
        self.prompt_text.pack(fill="x", pady=(10, 0))
        self.prompt_text.configure(state="disabled")

        row = tk.Frame(card, bg=COLORS["card"])
        row.pack(fill="x", pady=(10, 0))
        tk.Button(row, text="复制当前推荐提示词", width=18, command=self.on_copy_current_prompt, relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left"
        )
        tk.Button(row, text="复制初始化提示词", width=16, command=lambda: self._copy_text(INIT_PROMPT, "初始化提示词已复制。"), relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left", padx=8
        )
        tk.Button(row, text="复制续聊提示词", width=16, command=lambda: self._copy_text(RESUME_PROMPT, "续聊提示词已复制。"), relief="flat", bg="#e2e8f0", cursor="hand2").pack(
            side="left"
        )
        tk.Button(
            row,
            text="复制收尾提示词",
            width=16,
            command=lambda: self._copy_text(WRAPUP_PROMPT, "收尾提示词已复制。"),
            relief="flat",
            bg="#e2e8f0",
            cursor="hand2",
        ).pack(side="left", padx=8)

    def _build_status_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "当前状态")
        card.pack(fill="x")

        # 每个智能体一行，分别显示 skill 安装状态。
        self.skill_badges = {}
        for index, agent in enumerate(AGENT_NAMES):
            badge = tk.Label(card, anchor="w", font=("Microsoft YaHei UI", 10, "bold"), padx=10, pady=8)
            badge.pack(fill="x", pady=(0 if index == 0 else 8, 0))
            self.skill_badges[agent] = badge

        self.project_badge = tk.Label(card, anchor="w", font=("Microsoft YaHei UI", 10, "bold"), padx=10, pady=8)
        self.project_badge.pack(fill="x", pady=(8, 0))

    def _build_output_card(self, parent: tk.Widget) -> None:
        card = self._card(parent, "操作结果 / 说明")
        card.pack(fill="both", expand=True, pady=(14, 0))

        self.output_text = tk.Text(card, wrap="word", font=("Consolas", 10), bd=1, relief="solid")
        self.output_text.pack(fill="both", expand=True)
        self._write_output(
            "欢迎使用。\n\n"
            "最简单的流程：\n"
            "1. 先选顶部场景\n"
            "2. 确认项目目录\n"
            "3. 直接点蓝色主按钮\n"
            "4. 然后复制推荐提示词去 Codex 或 WorkBuddy 发送"
        )

    def _expand_window_on_start(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            # Keep the larger default geometry as a safe fallback.
            pass

    def _set_text_widget(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _write_output(self, text: str) -> None:
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)

    def _apply_scenario(self, key: str) -> None:
        self.scenario_key = key
        current = SCENARIOS[key]

        for scenario_key, button in self.scenario_buttons.items():
            data = SCENARIOS[scenario_key]
            if scenario_key == key:
                button.configure(bg=data["color"], fg="white", activebackground=data["color"], activeforeground="white")
            else:
                button.configure(bg=data["soft"], fg=data["color"], activebackground=data["soft"], activeforeground=data["color"])

        self.scenario_title.configure(text=f"当前场景：{current['title']}")
        steps = "\n".join(f"{index}. {item}" for index, item in enumerate(current["steps"], start=1))
        self._set_text_widget(self.scenario_text, steps)
        self.status_var.set(f"已切换场景：{current['title']}")
        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_status_cards()
        self._refresh_recommendation()

    def _refresh_status_cards(self) -> None:
        installed = skill_installed_map()
        for agent, badge in self.skill_badges.items():
            if installed[agent]:
                badge.configure(text=f"{agent} Skill：已安装", bg=COLORS["green_soft"], fg=COLORS["green"])
            else:
                badge.configure(text=f"{agent} Skill：未安装", bg=COLORS["red_soft"], fg=COLORS["red"])

        project = resolve_project_path(self.project_var.get())
        if project is None:
            self.project_state_var.set("项目状态：还没有选择项目目录")
            self.project_badge.configure(text="项目状态：未选择目录", bg=COLORS["red_soft"], fg=COLORS["red"])
            return

        if not project.exists():
            self.project_state_var.set("项目状态：目录不存在，请重新选择")
            self.project_badge.configure(text="项目状态：目录不存在", bg=COLORS["red_soft"], fg=COLORS["red"])
            return

        if not project.is_dir():
            self.project_state_var.set("项目状态：目标不是目录，请重新选择")
            self.project_badge.configure(text="项目状态：目标不是目录", bg=COLORS["red_soft"], fg=COLORS["red"])
            return

        ready, missing = project_handoff_status(project)
        if ready:
            self.project_state_var.set("项目状态：已发现完整交接文件，可以直接续聊")
            self.project_badge.configure(text="项目状态：已发现完整交接文件", bg=COLORS["green_soft"], fg=COLORS["green"])
        else:
            missing_text = "、".join(str(item).replace("\\", "/") for item in missing)
            self.project_state_var.set(f"项目状态：缺少交接文件，建议初始化（缺少：{missing_text}）")
            self.project_badge.configure(text="项目状态：缺少交接文件", bg=COLORS["amber_soft"], fg=COLORS["amber"])

    def _refresh_recommendation(self) -> None:
        action = self._recommended_action()
        self.main_action_kind = action["kind"]
        self.recommendation_var.set(f"推荐下一步：{action['summary']}")
        self.main_action_button.configure(text=action["button_text"], bg=COLORS["blue"], fg="white", activebackground="#1d4ed8", activeforeground="white")
        self.prompt_title.configure(text=action["prompt_title"])
        self._set_text_widget(self.prompt_text, action["prompt"])

    def _recommended_action(self) -> dict:
        project = resolve_project_path(self.project_var.get())
        skill_ready = skill_installed()
        project_exists = project is not None and project.is_dir()
        handoff_ready = False
        if project_exists:
            handoff_ready, _ = project_handoff_status(project)

        if self.scenario_key == "new-computer" and not skill_ready:
            return {
                "kind": "install-skill",
                "summary": "这是一台新电脑，先安装 Skill",
                "button_text": "现在先安装 Skill",
                "prompt_title": "安装后再发送这句",
                "prompt": RESUME_PROMPT,
            }

        if not skill_ready:
            return {
                "kind": "install-skill",
                "summary": "本机还没有安装 Skill，先装上最稳",
                "button_text": "现在先安装 Skill",
                "prompt_title": "安装后推荐发送：续聊提示词",
                "prompt": RESUME_PROMPT,
            }

        if not project_exists:
            return {
                "kind": "choose-project",
                "summary": "先选择一个有效的项目目录",
                "button_text": "请先点“浏览...”选择项目目录",
                "prompt_title": "选择好项目后再发送提示词",
                "prompt": RESUME_PROMPT,
            }

        if not handoff_ready:
            return {
                "kind": "init-project",
                "summary": "这个项目还没有完整交接文件，先初始化",
                "button_text": "现在初始化项目交接文件",
                "prompt_title": "初始化完成后建议发送：初始化提示词",
                "prompt": INIT_PROMPT,
            }

        return {
            "kind": "copy-resume-prompt",
            "summary": "项目已准备好，直接续聊",
            "button_text": "复制续聊提示词",
            "prompt_title": "现在建议发送：续聊提示词",
            "prompt": RESUME_PROMPT,
        }

    def _copy_text(self, value: str, status: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self.status_var.set(status)
        self._write_output(f"已复制到剪贴板：\n\n{value}")

    def on_main_action(self) -> None:
        if self.main_action_kind == "install-skill":
            self.on_install_skill()
        elif self.main_action_kind == "init-project":
            self.on_init_project()
        elif self.main_action_kind == "copy-resume-prompt":
            self._copy_text(RESUME_PROMPT, "续聊提示词已复制。")
        elif self.main_action_kind == "choose-project":
            self.on_browse_project()

    def on_install_skill(self) -> None:
        try:
            result = install_skill()
            self._write_output(result)
            self.status_var.set("Skill 安装完成。")
            self._refresh_all()
        except Exception as exc:
            messagebox.showerror("安装失败", str(exc))
            self.status_var.set("Skill 安装失败。")

    def on_browse_project(self) -> None:
        current = resolve_project_path(self.project_var.get())
        initial = str(current) if current is not None and current.is_dir() else str(Path.home())
        selected = filedialog.askdirectory(title="选择项目目录", initialdir=initial)
        if selected:
            self.project_var.set(selected)
            self._refresh_all()
            self.status_var.set("已选择项目目录。")

    def on_init_project(self) -> None:
        project = resolve_project_path(self.project_var.get())
        if project is None:
            messagebox.showerror("无法初始化", "请先选择项目目录，再点初始化。")
            return
        try:
            result = init_project(project)
            self._write_output(result)
            self.status_var.set("项目初始化完成。")
            self._refresh_all()
        except Exception as exc:
            messagebox.showerror("初始化失败", str(exc))
            self.status_var.set("项目初始化失败。")

    def on_check_hygiene(self) -> None:
        project = resolve_project_path(self.project_var.get())
        if project is None:
            messagebox.showerror("无法检查", "请先选择项目目录，再点检查工程卫生。")
            return
        if not project.is_dir():
            messagebox.showerror("无法检查", f"项目目录不存在或不是目录：\n{project}")
            return
        try:
            report, problems = run_hygiene_scan(project)
        except Exception as exc:
            messagebox.showerror("检查失败", str(exc))
            self.status_var.set("工程卫生检查失败。")
            return

        if problems == 0:
            header = "工程卫生检查通过：未发现隐藏问题。"
        else:
            header = f"工程卫生检查完成：发现 {problems} 个问题文件，详见下方。"
        self._write_output(f"{header}\n\n{report}")
        self.status_var.set(header)

    def on_run_selftest(self) -> None:
        # 在独立子进程里跑 selftest.py：它自己要建 Tk 窗口，
        # 在当前进程里再起一个 Tk 根窗口会互相干扰，所以必须分开。
        script = TEMPLATE_ROOT / "selftest.py"
        if not script.exists():
            messagebox.showerror("未找到", f"未找到自检脚本：\n{script}")
            return

        self.status_var.set("正在运行工具箱自检，请稍候…")
        self._write_output("正在运行工具箱自检，请稍候…\n")
        self.update_idletasks()

        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300,
            )
        except Exception as exc:
            messagebox.showerror("自检无法启动", str(exc))
            self.status_var.set("工具箱自检无法启动。")
            return

        output = (proc.stdout or "").strip()
        if proc.stderr and proc.stderr.strip():
            output += "\n\n--- stderr ---\n" + proc.stderr.strip()
        self._write_output(output or "(自检没有产生输出)")

        if proc.returncode == 0:
            summary = "工具箱自检全部通过。"
        elif proc.returncode == 2:
            summary = "工具箱自检无法运行（环境不满足），详见右侧。"
        else:
            summary = f"工具箱自检发现失败项（退出码 {proc.returncode}），详见右侧。"
        self.status_var.set(summary)

    def on_open_project(self) -> None:
        project = resolve_project_path(self.project_var.get())
        if project is None:
            messagebox.showinfo("未选择", "请先选择项目目录。")
            return
        try:
            open_in_explorer(project)
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def on_open_handoff(self) -> None:
        project = resolve_project_path(self.project_var.get())
        if project is None:
            messagebox.showinfo("未选择", "请先选择项目目录。")
            return
        handoff = project / "docs" / "HANDOFF.md"
        if handoff.exists():
            open_in_explorer(handoff.parent)
            self._write_output(f"请在这个目录打开 HANDOFF 文件：\n{handoff}")
        else:
            messagebox.showinfo("未找到", "当前项目里还没有 docs/HANDOFF.md，请先初始化项目交接文件。")

    def on_open_prompts(self) -> None:
        if PROMPTS_FILE.exists():
            open_in_explorer(PROMPTS_FILE.parent)
            self._write_output(f"请在这个目录打开提示词文档：\n{PROMPTS_FILE}")
        else:
            messagebox.showerror("未找到", f"未找到提示词文档：\n{PROMPTS_FILE}")

    def on_copy_current_prompt(self) -> None:
        prompt = self._recommended_action()["prompt"]
        prompt_name = "当前推荐提示词已复制。"
        self._copy_text(prompt, prompt_name)


if __name__ == "__main__":
    app = WorkflowTool()
    app.mainloop()
