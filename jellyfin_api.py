import os
import requests

class JellyfinAPI:
    def __init__(self):
        self.url = os.getenv('JELLYFIN_URL')
        self.api_key = os.getenv('JELLYFIN_API_KEY')
        self.library_id = os.getenv('JELLYFIN_LIBRARY_ID', None)
        self.session = requests.Session()
        self.session.headers.update({
            'X-Emby-Token': self.api_key
        })
        self.session.trust_env = False  # <--- ВАЖНО!

    def movie_exists(self, title):
        params = {
            'IncludeItemTypes': 'Movie',
            'SearchTerm': title,
            'Recursive': 'true'
        }
        if self.library_id:
            params['ParentId'] = self.library_id
        resp = self.session.get(f"{self.url}/emby/Items", params=params, proxies={}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('Items', []):
                if item.get('Name', '').strip().lower() == title.strip().lower():
                    return True
        return False