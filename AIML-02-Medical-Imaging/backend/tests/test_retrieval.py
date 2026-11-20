from app.services import retrieval_service


class _Response:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size: int):
        return self.content[:size]


def test_pubmed_search_returns_live_source_metadata(monkeypatch):
    responses = iter([
        b'{"esearchresult":{"count":"1","idlist":["12345"]}}',
        b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345</PMID><Article>
        <ArticleTitle>Medical imaging research</ArticleTitle>
        <Journal><Title>Journal of Imaging</Title><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>
        </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>''',
    ])
    monkeypatch.setattr(retrieval_service, 'urlopen', lambda request, timeout: _Response(next(responses)))

    result = retrieval_service.search_pubmed('medical imaging', limit=5)

    assert result['count'] == 1
    assert result['articles'] == [{
        'pmid': '12345',
        'title': 'Medical imaging research',
        'journal': 'Journal of Imaging',
        'year': '2025',
        'url': 'https://pubmed.ncbi.nlm.nih.gov/12345/',
    }]
