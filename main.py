import re
import logging
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction

class GithubQuery():

  def __init__(self, url, token):
    headers = {'Authorization': 'bearer %s' % token}
    transport = RequestsHTTPTransport(url, headers=headers, use_json=True)
    self.client = Client(transport=transport)

  def repos(self, query, count=8):
    query = gql('''
query {
  search(query: "%s", type: REPOSITORY, first: 10) {
    nodes {
      ... on Repository {
        nameWithOwner
        description
      }
    }
  }
}
''' % query)
    result = self.client.execute(query)
    return result["search"]["nodes"]

  def myname(self):
    query = gql('''
query {
  viewer {
    login
  }
}
''' % query)
    result = self.client.execute(query)
    return result["viewer"]["login"]


class GithubExtension(Extension):

    def __init__(self):
        super(GithubExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        keyword = event.get_keyword()

        if keyword == extension.preferences["github"]:
          hostname = "github.com"
          gh = GithubQuery("https://api.github.com/graphql", extension.preferences["github_token"])
        else:
          hostname = extension.preferences["ghe_hostname"]
          url = "https://%s/api/graphql" % hostname
          gh = GithubQuery(url, extension.preferences["ghe_token"])

        items = []
        argument = event.get_argument() or ""
        arguments = argument.split(" ", 1)
        command = arguments[0]
        query = arguments[1] if len(arguments) > 1 else ''

        if command == "my":
          my_pages = ["dashboard", "notifications", "issues", "pulls", "settings", "stars", "gist"]
          for page in my_pages:
            if query != '' and re.search("^%s" % query, page) is None:
              continue
            url  = "https://%s/%s" % (hostname, page)
            items.append(ExtensionResultItem(icon='images/repo.png',
                                              name=page,
                                              description="Open %s page" % page,
                                              on_enter=OpenUrlAction(url)))
        else:
          argument += " in:name,org"

          repos = gh.repos(argument)
          for r in sorted(repos, key=lambda r:r["nameWithOwner"]):
            name = r["nameWithOwner"]
            desc = r["description"]

            url  = "https://%s/%s" % (hostname, name)
            items.append(ExtensionResultItem(icon='images/repo.png',
                                              name=name,
                                              description=desc,
                                              on_enter=OpenUrlAction(url)))

        return RenderResultListAction(items)

if __name__ == '__main__':
    GithubExtension().run()
