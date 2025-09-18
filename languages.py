import os
import requests
import subprocess
import shutil
from collections import defaultdict

USERNAME = "16-by-9"
TOKEN = os.getenv("GITHUB_TOKEN")  # must be set in GitHub Actions secrets

LANGUAGES_EXT = {
    "Python": [".py", ".pyi", ".pyl"],
    "C++": [".cpp", ".cxx", ".cc", ".hpp", ".ino"],
    "C": [".c", ".h"],
    "C#": [".cs"],
    "Java": [".java", ".jar"],
    "JavaScript": [".js"],
    "TypeScript": [".ts"],
    "Go": [".go"],
    "Rust": [".rs"],
    "CMake": [".cmake", ".make"],
    "Shell": [".sh"],
    "HTML": [".html", ".htm"],
    "CSS": [".css"],
    "Assembly": [".s", ".asm"],
    "PHP": [".php"],
    "Kotlin": [".kt", ".kts"],
    "SolidWorks": [".3MF"],
    "Swift": [".swift"],
    "Ruby": [".rb"],
    "R": [".r"],
    "Dart": [".dart"],
}

def get_user_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}"
        headers = {"Authorization": f"token {TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            raise Exception(f"GitHub API error: {r.status_code} - {r.text}")
        data = r.json()
        if not data:
            break
        repos += data
        page += 1
    return [repo["clone_url"] for repo in repos]

def get_language_counts(repo_urls):
    counts = defaultdict(int)

    for url in repo_urls:
        name = url.split("/")[-1].replace(".git", "")
        if os.path.exists(name):
            shutil.rmtree(name)
        subprocess.run(["git", "clone", "--depth", "1", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(name):
            continue

        used_langs = set()
        for root, _, files in os.walk(name):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                for lang, exts in LANGUAGES_EXT.items():
                    if ext in exts:
                        used_langs.add(lang)
                        break
        for lang in used_langs:
            counts[lang] += 1
        shutil.rmtree(name)
    return counts

def update_readme(counts):
    start_tag = "<!--LANGUAGE_STATS_START-->"
    end_tag = "<!--LANGUAGE_STATS_END-->"
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    before = content.split(start_tag)[0]
    after = content.split(end_tag)[1]
    stats = "\n".join(
    [f"- {count} {lang} project{'s' if count > 1 else ''}" for lang, count in sorted(counts.items(), key=lambda x: -x[1])]
)
    new_block = f"{start_tag}\n{stats}\n{end_tag}"
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(before + new_block + after)

if __name__ == "__main__":
    repos = get_user_repos()
    counts = get_language_counts(repos)
    update_readme(counts)


