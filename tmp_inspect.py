import pathlib
from app.crawler.cli import extract_next_data

html = pathlib.Path('fifa_matches_page.html').read_text(encoding='utf-8', errors='ignore')
next_data = extract_next_data(html)

def walk(obj, path='root'):
    if isinstance(obj, dict):
        if 'matches' in obj and isinstance(obj['matches'], list):
            print('found matches at', path, 'len', len(obj['matches']))
            if obj['matches']:
                print('sample keys', list(obj['matches'][0].keys())[:20])
                print('sample', {k: obj['matches'][0][k] for k in list(obj['matches'][0].keys())[:8]})
        for k,v in obj.items():
            walk(v, f'{path}.{k}')
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            walk(item, f'{path}[{idx}]')

walk(next_data)
