import math
import os
import requests
import shutil
import subprocess
from collections import defaultdict

USERNAME = "16-by-9"

EXCLUDED_REPOS = {
    "16-by-9",
}

LANGUAGES_EXT = {
    "Python": [".py", ".pyi", ".pyl"],
    "C++": [".cpp", ".cxx", ".cc", ".h", ".hpp", ".ino"],
    "C": [".c"],
    "C#": [".cs"],
    "Java": [".java", ".jar"],
    "JavaScript": [".js"],
    "TypeScript": [".ts"],
    "Go": [".go"],
    "Rust": [".rs"],
    "Shell": [".sh"],
    "HTML": [".html", ".htm"],
    "CSS": [".css"],
    "Assembly": [".s", ".asm"],
    "PHP": [".php"],
    "Kotlin": [".kt", ".kts"],
    "SolidWorks": [".sldprt"],
    "Swift": [".swift"],
    "Ruby": [".rb"],
    "R": [".r"],
    "Dart": [".dart"],
}

DOMINATES = {
    "C++": ["C"],
    "TypeScript": ["JavaScript"],
}


SECONDARY_THRESHOLD = 0.40

# Hybrid weighting
SIZE_WEIGHT = 0.70
FILE_WEIGHT = 0.30

# Prevents giant files from overpowering everything
USE_LOG_SIZE = True

# Ignore directories that would distort actual language
SKIP_DIRS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    ".dart_tool",
    "__pycache__",
    ".idea",
    ".vscode",
    ".vs",
    "target",
    "out",
    "bin",
    "obj",
}


def get_user_repos():
    repos = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/"
            f"{USERNAME}/repos?per_page=100&page={page}"
        )

        r = requests.get(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

        if r.status_code != 200:
            raise Exception(
                f"GitHub API error: "
                f"{r.status_code} - {r.text}"
            )

        data = r.json()

        if not data:
            break

        repos.extend(data)
        page += 1

    # Public repos only.
    # Ignore forks.
    # Ignore excluded repos.
    return [
        repo["clone_url"]
        for repo in repos
        if not repo["fork"]
        and repo["name"] not in EXCLUDED_REPOS
    ]


def scan_repo_language_scores(repo_path):
    file_counts = defaultdict(int)
    size_scores = defaultdict(float)

    for root, dirs, files in os.walk(repo_path):
        # Skip junk/generated dirs.
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        for file in files:
            ext = os.path.splitext(file)[1].lower()

            matched_lang = None

            for lang, exts in LANGUAGES_EXT.items():
                if ext in exts:
                    matched_lang = lang
                    break

            if not matched_lang:
                continue

            path = os.path.join(root, file)

            try:
                raw_size = os.path.getsize(path)
            except OSError:
                raw_size = 0

            if USE_LOG_SIZE:
                weighted_size = math.log2(raw_size + 1)
            else:
                weighted_size = raw_size

            file_counts[matched_lang] += 1
            size_scores[matched_lang] += weighted_size

    total_files = sum(file_counts.values())
    total_size = sum(size_scores.values())

    if total_files == 0 or total_size == 0:
        return {}

    lang_scores = {}

    for lang in set(file_counts) | set(size_scores):
        file_ratio = file_counts[lang] / total_files
        size_ratio = size_scores[lang] / total_size

        score = (
            FILE_WEIGHT * file_ratio
            + SIZE_WEIGHT * size_ratio
        )

        lang_scores[lang] = score

    return lang_scores


def apply_dominance(lang_scores):
    used_langs = set(lang_scores.keys())

    for dominant, dominated_langs in DOMINATES.items():
        if dominant not in lang_scores:
            continue

        for weak in dominated_langs:
            if weak not in lang_scores:
                continue

            dominant_score = lang_scores[dominant]
            weak_score = lang_scores[weak]

            pair_total = dominant_score + weak_score

            if pair_total <= 0:
                continue

            weak_ratio = weak_score / pair_total

            # Weak language is only helper noise.
            if weak_ratio < SECONDARY_THRESHOLD:
                used_langs.discard(weak)

            # If both are substantial,
            # keep whichever is more dominant.
            elif dominant_score >= weak_score:
                used_langs.discard(weak)

            else:
                used_langs.discard(dominant)

    return used_langs


def get_language_counts(repo_urls):
    counts = defaultdict(int)

    for url in repo_urls:
        repo_name = (
            url.split("/")[-1]
            .replace(".git", "")
        )

        if os.path.exists(repo_name):
            shutil.rmtree(repo_name)

        subprocess.run(
            ["git", "clone", "--depth", "1", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not os.path.exists(repo_name):
            continue

        try:
            lang_scores = scan_repo_language_scores(repo_name)

            if not lang_scores:
                continue

            used_langs = apply_dominance(lang_scores)

            for lang in used_langs:
                counts[lang] += 1

        finally:
            shutil.rmtree(repo_name)

    return counts


def update_readme(counts):
    start_tag = "<!--LANGUAGE_STATS_START-->"
    end_tag = "<!--LANGUAGE_STATS_END-->"

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    if start_tag not in content or end_tag not in content:
        raise Exception(
            "README.md is missing language stats tags."
        )

    before = content.split(start_tag)[0]
    after = content.split(end_tag)[1]

    stats = "\n".join(
        [
            f"- {count} {lang} project"
            f"{'s' if count != 1 else ''}"
            for lang, count in sorted(
                counts.items(),
                key=lambda x: (-x[1], x[0])
            )
        ]
    )

    new_block = (
        f"{start_tag}\n"
        f"{stats}\n"
        f"{end_tag}"
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(before + new_block + after)


if __name__ == "__main__":
    repos = get_user_repos()
    counts = get_language_counts(repos)
    update_readme(counts)
