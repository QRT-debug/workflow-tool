"""工程卫生检查工具。

扫描文本文件中的隐藏问题：
  1. 控制字符污染（退格 0x08、孤立 CR、被吞掉的反引号+TAB 代码围栏）
  2. 非 UTF-8 编码字节
  3. Markdown 代码围栏未闭合
  4. 含中文的 PowerShell 脚本缺少 UTF-8 BOM

既可以作为命令行工具直接运行，也可以被 workflow-tool.pyw 导入复用。
命令行运行有问题的文件时返回退出码 1，便于接入钩子或 CI。
"""

from __future__ import annotations

import argparse
import pathlib
import sys

# 扫描时跳过的目录，避免把生成物当成源码检查。
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "build",
    "release",
    "node_modules",
    "managed_components",
    ".espressif",
    ".workbuddy",
    ".venv",
    "dist",
}

# 需要检查的文本扩展名；空字符串代表无扩展名的文件（例如 .gitattributes）。
TEXT_SUFFIXES = {
    "",
    ".md",
    ".txt",
    ".ps1",
    ".bat",
    ".cmd",
    ".py",
    ".pyw",
    ".vbs",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".csv",
    ".cmake",
    ".kconfig",
}

UTF8_BOM = b"\xef\xbb\xbf"


class FileIssue:
    """单个文件的问题集合。"""

    def __init__(self, path: pathlib.Path, problems: list[str]) -> None:
        self.path = path
        self.problems = problems


def check_bytes(raw: bytes, suffix: str) -> list[str]:
    """对单个文件的原始字节做全部检查，返回问题描述列表。"""
    problems: list[str] = []

    if b"\x08" in raw:
        problems.append("退格字符 0x08 x%d" % raw.count(b"\x08"))

    lone_cr = raw.count(b"\r") - raw.count(b"\r\n")
    if lone_cr:
        problems.append("孤立 CR x%d" % lone_cr)

    if b"`\t" in raw:
        problems.append("反引号+TAB（代码围栏被压平）x%d" % raw.count(b"`\t"))

    text = None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        problems.append("含非 UTF-8 字节")

    if suffix == ".md" and text is not None:
        fences = sum(1 for line in text.split("\n") if line.strip().startswith("`" * 3))
        if fences % 2:
            problems.append("Markdown 代码围栏未闭合（共 %d 个）" % fences)

    if suffix == ".ps1":
        has_non_ascii = any(byte > 127 for byte in raw)
        if has_non_ascii and not raw.startswith(UTF8_BOM):
            problems.append("含非 ASCII 字符但缺少 UTF-8 BOM（PS 5.1 下会乱码或语法报错）")

    return problems


def iter_text_files(root: pathlib.Path):
    """遍历目录下需要检查的文本文件。"""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def scan(root: pathlib.Path) -> tuple[list[FileIssue], int]:
    """扫描一个目录，返回（问题列表，已检查文件数）。"""
    issues: list[FileIssue] = []
    checked = 0
    for path in iter_text_files(root):
        checked += 1
        try:
            raw = path.read_bytes()
        except OSError as exc:
            issues.append(FileIssue(path, ["读取失败：%s" % exc]))
            continue
        problems = check_bytes(raw, path.suffix.lower())
        if problems:
            issues.append(FileIssue(path, problems))
    return issues, checked


def format_report(roots: list[pathlib.Path], per_root: list[tuple[list[FileIssue], int]]) -> tuple[str, int]:
    """把扫描结果格式化成可读文本，返回（文本，问题文件总数）。"""
    lines: list[str] = []
    total_files = 0
    total_problems = 0

    for root, (issues, checked) in zip(roots, per_root):
        total_files += checked
        total_problems += len(issues)
        lines.append("扫描目录：%s" % root)
        if not issues:
            lines.append("  未发现问题")
        else:
            for issue in issues:
                try:
                    shown = issue.path.relative_to(root)
                except ValueError:
                    shown = issue.path
                lines.append("  [!] %s" % shown)
                for problem in issue.problems:
                    lines.append("        - %s" % problem)
        lines.append("  已检查 %d 个文本文件，问题文件 %d 个" % (checked, len(issues)))
        lines.append("")

    lines.append("合计：检查 %d 个文件，问题文件 %d 个" % (total_files, total_problems))
    return "\n".join(lines), total_problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查工程文本文件的隐藏问题。")
    parser.add_argument("paths", nargs="*", help="要检查的目录，默认当前目录")
    parser.add_argument("-q", "--quiet", action="store_true", help="只输出结论，不列出细节")
    args = parser.parse_args(argv)

    roots = [pathlib.Path(p) for p in (args.paths or ["."])]
    missing = [r for r in roots if not r.is_dir()]
    if missing:
        for root in missing:
            print("目录不存在或不是目录：%s" % root, file=sys.stderr)
        return 2

    per_root = [scan(root) for root in roots]
    report, problems = format_report(roots, per_root)

    if args.quiet:
        total_files = sum(checked for _, checked in per_root)
        print("检查 %d 个文件，问题文件 %d 个" % (total_files, problems))
    else:
        print(report)

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
