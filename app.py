import os
from flask import Flask, request, render_template_string, session
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = "supersecretkey"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Autino Conversatie</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <style>
        body { font-family: Arial; max-width: 600px; margin: auto; padding: 20px; background:#f4f4f4; }
        .chat { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .user { font-weight: bold; margin-top: 10px; }
        .ai { margin-bottom: 15px; }
        input[type=text] { width: 100%; padding: 10px; margin-top: 10px; }
        button { margin-top: 10px; padding: 10px 20px; background: #1e3a8a; color: white; border: none; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Autino – AI Auto Advies</h1>
    <div class="chat">
        {% for m in messages %}
            <div class="{{ m.role }}">{{ m.role.capitalize() }}: {{ m.content }}</div>
        {% endfor %}
        
{% if results %}
    <h2>Suggesties op basis van jouw antwoorden</h2>
    {% for r in results %}
        <div style="margin:10px 0;padding:10px;border:1px solid #ccc;border-radius:6px;">
            <a href="{{ r.url }}" target="_blank"><strong>{{ r.title }}</strong></a><br>
            {{ r.price }} – {{ r.km }}
        </div>
    {% endfor %}
{% endif %}

<form method="post">
            <input type="text" name="message" placeholder="Typ hier je antwoord..." autofocus required />
            <button type="submit">Verstuur</button>
        </form>
    </div>
</body>
</html>
"""

START_PROMPT = [
    {"role": "system", "content": "Je bent een behulpzame Nederlandse AI die mensen helpt bij het vinden van een geschikte auto op basis van hun situatie. Stel stapsgewijs maximaal 3 vragen en geef daarna een suggestie voor zoekfilters in JSON-formaat."},
    {"role": "assistant", "content": "Welkom bij Autino! Ik help je de juiste auto te vinden. Waarvoor wil je de auto voornamelijk gebruiken? Voor in de stad, lange ritten, of iets anders?"}
]

@app.route("/", methods=["GET", "POST"])
def index():
    if "messages" not in session:
        session["messages"] = START_PROMPT.copy()

    messages = session["messages"]

    if request.method == "POST":
        user_input = request.form.get("message", "")
        messages.append({"role": "user", "content": user_input})

        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
            )
            reply = response["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            try:
                if "{" in reply:
                    filters = eval(reply.strip().split('\n')[-1])
                    results = real_scraper(filters)
                else:
                    results = []
            except Exception as e:
                results = []
        except Exception as e:
            messages.append({"role": "assistant", "content": f"Er ging iets mis met de AI: {e}"})
            results = []


return render_template_string(HTML_TEMPLATE, messages=messages, results=results if "results" in locals() else [])

if __name__ == "__main__":
    app.run(debug=True)



def mock_scraper(filters):
    # Simuleer dat we op basis van filters auto's tonen
    voorbeeld_auto = {
        "title": "Volvo XC40 Recharge",
        "price": "€47.950",
        "km": "35.000 km",
        "url": "https://voorbeeld.autino.nl/volvo-xc40",
    }
    return [voorbeeld_auto] if filters else []



import requests
from bs4 import BeautifulSoup
import re

def parse_km(km_str):
    km_str = km_str.replace('.', '').replace(',', '').replace('km', '').strip()
    match = re.search(r"(\d+)", km_str)
    return int(match.group(1)) if match else 0

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
                "title": title.text.strip(),
                "price": price.text.strip(),
                "km": km.text.strip(),
                "url": "https://www.vaartland.nl" + link["href"],
                "img": img["src"] if img and img.has_attr("src") else ""
            })
    return results

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
                'img': img['src'] if img else ''
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
                'img': img['src'] if img else ''
            })
    return results

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

def real_scraper(filters):
    all_cars = search_vaartland() + search_broekhuis() + search_volvo()
    return apply_filters(all_cars, filters)
