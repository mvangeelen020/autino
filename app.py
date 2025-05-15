import os
from flask import Flask, render_template_string, request
import openai
import requests
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
    <title>Autino – AutoZoeker AI</title>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <style>
        body { font-family: Arial; padding: 20px; background: #f4f4f4; }
        h1 { color: #1e3a8a; }
        form, .result { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        img.logo { width: 150px; }
    </style>
</head>
<body>
    <img src="/static/autino_logo.png" class="logo" />
    <h1>Zoek een auto met AI</h1>
    <form method="post">
        <input name="query" style="width:100%; max-width:400px;" placeholder="Bijv: Ik zoek een elektrische Kia met automaat" />
        <button type="submit">Zoeken</button>
    </form>

    {% if results %}
    <div>
        <h2>Resultaten</h2>
        {% for r in results %}
        <div class="result">
            <img src="{{ r.img }}" alt="auto" width="200"/><br>
            <a href="{{ r.url }}" target="_blank">{{ r.title }}</a><br>
            {{ r.price }} – {{ r.km }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>"""

def extract_filters(query):
    prompt = f'''
Je bent een AI die filters uit een autospeficatie haalt in natuurlijke taal.
Haal merk, brandstof, transmissie en max kilometerstand uit deze tekst.
Antwoord als JSON met keys: merk, brandstof, transmissie, kilometerstand.

Input: "{query}"
Output:
'''
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        filters = eval(response['choices'][0]['message']['content'])
        return filters
    except:
        return {}

def parse_km(km_str):
    km_str = km_str.replace('.', '').replace('km', '').strip()
    match = re.search(r"(\d+)", km_str)
    return int(match.group(1)) if match else 0

def apply_filters(cars, filters):
    result = []
    for car in cars:
        title = car['title'].lower()
        km = parse_km(car['km'])
        if filters.get('merk') and filters['merk'].lower() not in title:
            continue
        if filters.get('brandstof') and filters['brandstof'].lower() not in title:
            continue
        if filters.get('transmissie') and filters['transmissie'].lower() not in title:
            continue
        if filters.get('kilometerstand') and km > int(filters['kilometerstand']):
            continue
        result.append(car)
    return result

def search_broekhuis():
    url = 'https://www.broekhuis.nl/volvo/occasions/volvo-selekt'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    results = []
    for card in soup.select('div.vehicle')[:10]:
        title = card.select_one('.vehicle__title')
        price = card.select_one('.vehicle__price')
        km = card.select_one('.vehicle__meta-item--mileage')
        link = card.select_one('a')
        img = card.select_one('img')
        if title and price and km and link:
            results.append({
                'title': title.text.strip(),
                'price': price.text.strip(),
                'km': km.text.strip(),
                'url': 'https://www.broekhuis.nl' + link['href'],
                'img': img['src'] if img else '/static/autino_logo.png'
            })
    return results


def search_vaartland():
    url = "https://www.vaartland.nl/voorraad"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for card in soup.select("div.vehicle-card")[:10]:
        title = card.select_one(".vehicle-card__title")
        price = card.select_one(".vehicle-card__price")
        km = card.select_one(".vehicle-card__mileage")
        link = card.select_one("a")
        img = card.select_one("img")
        if title and price and km and link:
            results.append({
                'title': title.text.strip(),
                'price': price.text.strip(),
                'km': km.text.strip(),
                'url': "https://www.vaartland.nl" + link['href'],
                'img': img['src'] if img and 'src' in img.attrs else '/static/autino_logo.png'
            })
    return results

def search_volvo():
    url = 'https://selekt.volvocars.nl/nl-nl/store/'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    results = []
    for card in soup.select('div.result')[:10]:
        title = card.select_one('.title')
        price = card.select_one('.price')
        km = card.select_one('.mileage')
        link = card.select_one('a')
        img = card.select_one('img')
        if title and price and km and link:
            results.append({
                'title': title.text.strip(),
                'price': price.text.strip(),
                'km': km.text.strip(),
                'url': 'https://selekt.volvocars.nl' + link['href'],
                'img': img['src'] if img else '/static/autino_logo.png'
            })
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        query = request.form['query']
        filters = extract_filters(query)
        all_cars = search_broekhuis() + search_volvo() + search_vaartland()
        results = apply_filters(all_cars, filters)
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == '__main__':
    app.run(debug=True)
