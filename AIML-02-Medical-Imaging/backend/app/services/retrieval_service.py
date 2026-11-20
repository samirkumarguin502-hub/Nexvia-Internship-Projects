import json
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.core.config import settings

_EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'


def _request(url: str) -> bytes:
    request = Request(url, headers={'User-Agent': 'AIML-02-Medical-Imaging/1.0'})
    try:
        with urlopen(request, timeout=8) as response:
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise HTTPException(status_code=502, detail='PubMed response exceeded the size limit')
            return data
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail='PubMed is currently unavailable') from exc


def search_pubmed(query: str, limit: int = 10) -> dict:
    term = query.strip()
    if not 3 <= len(term) <= 200:
        raise HTTPException(status_code=422, detail='Search query must contain 3 to 200 characters')

    params = {'db': 'pubmed', 'term': term, 'retmode': 'json', 'retmax': str(limit), 'sort': 'relevance'}
    if settings.PUBMED_API_KEY:
        params['api_key'] = settings.PUBMED_API_KEY
    try:
        result = json.loads(_request(f'{_EUTILS}esearch.fcgi?{urlencode(params)}'))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail='PubMed returned an invalid search response') from exc
    search = result.get('esearchresult', {})
    ids = search.get('idlist', [])
    if not ids:
        return {'query': term, 'count': int(search.get('count', 0)), 'articles': []}

    fetch_params = {'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'xml'}
    if settings.PUBMED_API_KEY:
        fetch_params['api_key'] = settings.PUBMED_API_KEY
    try:
        root = ET.fromstring(_request(f'{_EUTILS}efetch.fcgi?{urlencode(fetch_params)}'))
    except ET.ParseError as exc:
        raise HTTPException(status_code=502, detail='PubMed returned invalid article metadata') from exc
    articles = []
    for record in root.findall('.//PubmedArticle'):
        medline = record.find('./MedlineCitation')
        article = medline.find('./Article') if medline is not None else None
        if article is None:
            continue
        pmid = medline.findtext('./PMID') if medline is not None else None
        title = ' '.join(''.join(article.find('./ArticleTitle').itertext()).split()) if article.find('./ArticleTitle') is not None else ''
        journal = article.findtext('./Journal/Title') or ''
        year = article.findtext('./Journal/JournalIssue/PubDate/Year') or article.findtext('./Journal/JournalIssue/PubDate/MedlineDate') or ''
        articles.append({
            'pmid': pmid,
            'title': title,
            'journal': journal,
            'year': year,
            'url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/' if pmid else None,
        })
    return {'query': term, 'count': int(search.get('count', 0)), 'articles': articles}
