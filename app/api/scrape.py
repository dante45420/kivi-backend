from flask import Blueprint, jsonify, request
import requests
from bs4 import BeautifulSoup

scrape_bp = Blueprint('scrape', __name__)


def scrape_jumbo(query: str):
    # Nota: sitio puede cambiar; este es un placeholder minimalista
    url = f"https://www.jumbo.cl/busca?q={requests.utils.quote(query)}"
    html = requests.get(url, timeout=10).text
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for card in soup.select('[data-cy="product-card"]')[:10]:
        name = (card.select_one('[data-cy="product-card-name"]') or {}).get_text(strip=True)
        price_el = card.select_one('[data-cy="price-current"]') or card.select_one('.product-card__price')
        if not name or not price_el:
            continue
        price_txt = price_el.get_text(strip=True).replace('.', '').replace('$', '').replace('CLP','')
        try:
            price = float(''.join(ch for ch in price_txt if ch.isdigit()))
        except Exception:
            continue
        items.append({ 'competitor': 'Jumbo', 'name': name, 'price': price })
    return items


def scrape_lider(query: str):
    url = f"https://www.lider.cl/supermercado/search?Ntt={requests.utils.quote(query)}"
    html = requests.get(url, timeout=10).text
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for card in soup.select('[data-qa="product-card"]')[:10]:
        name = card.get_text(strip=True)
        price_el = card.select_one('[data-qa="product-price"]')
        if not name or not price_el:
            continue
        price_txt = price_el.get_text(strip=True).replace('.', '').replace('$', '')
        try:
            price = float(''.join(ch for ch in price_txt if ch.isdigit()))
        except Exception:
            continue
        items.append({ 'competitor': 'Lider', 'name': name, 'price': price })
    return items


@scrape_bp.get('/scrape')
def do_scrape():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    jumbo = scrape_jumbo(q)
    lider = scrape_lider(q)
    return jsonify(jumbo + lider)




