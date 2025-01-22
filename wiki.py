import html
import json
import requests
from enum import Enum
from urllib.parse import unquote

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gamemanager import Player

class Endpoint(Enum):
    SEARCH = "/search/page"
    GET_HTML = "/page/_title_/html"
    GET_PAGE_OBJECT = "/page/_title_/bare"

class PageMeta:
    def __init__(self, title, page_id):
        self.title = title
        self.page_id = page_id

    def serialize(self):
        return {
            "title": self.title,
            "page_id": self.page_id
        }
    
class NoPage(PageMeta):
    def __init__(self):
        self.title = ""
        self.page_id = ""
        self.thumb = ""

class WikipediaAPI:
    LANG_CODE = "en"
    USER_AGENT = "Wikipedia Speedrun Game/0.0 (boynegregg312@gmail.com) Requests/2.32.3"
    BASE_URL = "https://api.wikimedia.org/core/v1/wikipedia/"

    def __init__(self):
        pass

    def construct_url(self, endpoint: Endpoint) -> str:
        return self.BASE_URL + self.LANG_CODE + endpoint.value
    
    def construct_request(self, endpoint: Endpoint, replacements: dict, **args):

        url = self.construct_url(endpoint)

        for replacement in replacements.keys():
            url = url.replace(f"_{replacement}_", replacements[replacement])

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept-Encoding": "gzip"

        }
        return {
            "url": url,
            "headers": headers,
            "params": args
        }
    
    def search_pages(self, query: str, limit: int = 1) -> list:
        response = requests.get(**self.construct_request(Endpoint.SEARCH, {}, q=query, limit=limit)).json()
        try: return response["pages"]
        except KeyError: return []
    
    def process_page_request(self, key: str, player: 'Player', add_to_path: bool) -> bool:
        response = requests.get(**self.construct_request(Endpoint.GET_PAGE_OBJECT, {"title": key}))
        page_data = response.json()

        if "httpCode" in page_data.keys() and page_data["httpCode"] == 404:
            return False# Invalid request

        print(page_data)
        if add_to_path: player.page_path.append({"title": page_data["title"], "page_id": key})
        return True

    def get_page_content(self, key: str, player: 'Player' = None) -> str:
        print("Download page:", key)

        response = requests.get(**self.construct_request(Endpoint.GET_PAGE_OBJECT, {"title": key}))
        page_data = response.json()

        if "httpCode" in page_data.keys() and page_data["httpCode"] == 404:
            return "INVALID"

        if player is not None:
            print(page_data)
            player.page_path.append({"title": page_data["title"], "page_id": key})
        
        if "redirect_target" in page_data.keys():
            key = unquote(page_data["redirect_target"].split("/")[-2])

        response = requests.get(**self.construct_request(Endpoint.GET_HTML, {"title": key}))

        text = response.text.encode("ascii", "xmlcharrefreplace").decode("ascii")
        text = (text
                .replace('<base href="//en.wikipedia.org/wiki/"/>', "")
                .replace("./", "https://en.wikipedia.org/wiki/")
                .replace("/w/load.php", "https://en.wikipedia.org/w/load.php"))


        return text

    def search_user_page_or_none(self, query: str) -> PageMeta|None:
        response = self.first_result_or_none(self.search_pages(query))
        if response is not None:
            return PageMeta(response["title"], response["key"])
        return None
    
    def first_result_or_none(self, search: list):
        if len(search) > 0:
            return search[0]
        return None

if __name__ == "__main__":
    print(WikipediaAPI().get_page_content("Joe_Biden"))