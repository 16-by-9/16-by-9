import requests
from collections import defaultdict
import os

GITHUB_USER = "16-by-9"
TOKEN = os.getenv("GITHUB_TOKEN")
LANGUAGES_EXT = {
    "Python": [".py", ".pyi", ".pyl"],
    "C++": [".cpp", ".hpp", ".h", ".cc", ".cxx"],
    "C": [".c"],
    "C#": [".cs"],
    "JavaScript": [".js"],
    "Java": [".jar", ".java"],
    "CMake": [".cmake", ".make"],
}

def get_user_repos():
    headers = {"Authorization": f"token {TOKEN}"}
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}"
        r = requests.get(url, headers=headers)
        if not r.ok or not r.json():
            break
        repos.extend(r.json())
        page += 1
    return repos

def fetch_language_stats():
    counts = defaultdict(int)
    headers = {"Authorization": f"token {TOKEN}"}
    repos = get_user_repos()

    for repo in repos:
        repo_name = repo["full_name"]
        url = f"https://api.github.com/repos/{repo_name}/contents"
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            continue
        exts_found = set()
        for file in r.json():
            name = file.get("name", "")
            for lang, exts in LANGUAGES_EXT.items():
                if any(name.endswith(ext) for ext in exts):
                    exts_found.add(lang)
        for lang in exts_found:
            counts[lang] += 1

    return counts

def update_readme(language_counts):
    with open("README.md", "r", encoding="utf-8") as f:
        lines = f.readlines()

    start = lines.index("<!--LANGUAGE_STATS_START-->\n")
    end = lines.index("<!--LANGUAGE_STATS_END-->\n")
    new_block = "\n".join([f"{count} {lang} project{'s' if count != 1 else ''}" for lang, count in sorted(language_counts.items(), key=lambda x: -x[1])])
    lines[start + 1:end] = [new_block + "\n"]

    with open("README.md", "w", encoding="utf-8") as f:
        f.writelines(lines)

if __name__ == "__main__":
    counts = fetch_language_stats()
    update_readme(counts)