import os
import json
import subprocess
import requests
from datetime import datetime

MEMES_DIR = 'memes'
OUTPUT_FILE = '_data/memes.json'
EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_OWNER = "simonleclere"
REPO_NAME = "aslmemes"
CATEGORY_ID = "DIC_kwDORD658c4C1ljw"

user_cache = {}

def get_github_reactions():
    if not GH_TOKEN:
        print("GH_TOKEN non trouvé, skip fetching reactions.")
        return {}

    query = """
    query($owner: String!, $name: String!, $categoryId: ID!) {
      repository(owner: $owner, name: $name) {
        discussions(first: 100, categoryId: $categoryId) {
          nodes {
            title
            createdAt
            reactionGroups {
              content
              reactors {
                totalCount
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "owner": REPO_OWNER,
        "name": REPO_NAME,
        "categoryId": CATEGORY_ID
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {GH_TOKEN}"},
            json={"query": query, "variables": variables},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        reactions_map = {}
        
        for disc in discussions:
            filename = disc["title"]
            total_votes = sum(group["reactors"]["totalCount"] for group in disc["reactionGroups"])
            reactions_map[filename] = {
                "votes": total_votes,
                "github_createdAt": disc["createdAt"]
            }
        return reactions_map
    except Exception as e:
        print(f"Erreur lors de la récupération des réactions GitHub: {e}")
        return {}

def get_author_info(filepath):
    try:
        sha = subprocess.check_output(
            ['git', 'log', '-1', '--format=%H', '--', filepath]
        ).decode('utf-8').strip()
        
        if not sha:
            return "Inconnu", datetime.now().isoformat(), None, None

        if GH_TOKEN and sha:
            if sha in user_cache:
                return user_cache[sha]
            
            api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{sha}"
            res = requests.get(api_url, headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=5)
            if res.status_code == 200:
                commit_data = res.json()
                author_data = commit_data.get("author")
                if author_data:
                    login = author_data.get("login")
                    avatar = author_data.get("avatar_url")
                    profile = author_data.get("html_url")
                    date = commit_data["commit"]["author"]["date"]
                    user_cache[sha] = (login, date, avatar, profile)
                    return login, date, avatar, profile

        author = subprocess.check_output(
            ['git', 'log', '-1', '--format=%an', '--', filepath]
        ).decode('utf-8').strip()
        date_str = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ai', '--', filepath]
        ).decode('utf-8').strip()
        
        return author, date_str, f"https://github.com/{author}.png", f"https://github.com/{author}"
        
    except Exception as e:
        print(f"Erreur lors de la récupération des infos d'auteur pour {filepath}: {e}")
        return "Inconnu", datetime.now().isoformat(), None, None

def main():
    os.makedirs('_data', exist_ok=True)
    
    github_stats = get_github_reactions()
    memes_data = []

    for filename in os.listdir(MEMES_DIR):
        if filename.lower().endswith(EXTENSIONS):
            filepath = os.path.join(MEMES_DIR, filename)
            
            author, date_str, avatar, profile = get_author_info(filepath)
            stats = github_stats.get(filename, {"votes": 0, "github_createdAt": date_str})
            
            memes_data.append({
                'filename': filename,
                'author': author,
                'author_avatar': avatar,
                'author_url': profile,
                'date': date_str,
                'votes': stats["votes"],
                'github_date': stats["github_createdAt"]
            })

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(memes_data, f, indent=4, ensure_ascii=False)

    print(f"Index généré avec {len(memes_data)} memes.")

if __name__ == "__main__":
    main()
