import os
from flask import Flask, request, render_template_string, session
import openai
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import re

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = "supersecretkey"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Autino – AI Auto Assistent</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; padding: 20px; max-width: 800px; margin: auto; background:#f9f9f9; }
        .chat-box { background:#fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .user { color: #1e3a8a; font-weight: bold; }
        .assistant { margin-bottom: 15px; }
        .car { margin:10px 0; padding:10px; border:1px solid #ccc; border-radius:6px; background:white; }
    </style>
</head>
<body>
    <h1>Autino – AI Auto Assistent</h1>
    <div class="chat-box">
        {% for m in messages %}
            <div class="{{ m.role }}"><strong>{{ m.role.capitalize() }}:</strong> {{ m.content }}</div>
        {% endfor %}
        <form method="post">
            <input type="text" name="message" style="width:100%; padding:10px;" placeholder="Typ hier je antwoord..." required>
            <button type="submit" style="margin-top:10px; padding:10px 20px;">Verstuur</button>
        </form>
    </div>

    {% if results %}
    <h2>Voorgestelde auto’s</h2>
    {% for r in results %}
        <div class="car">
            <a href="{{ r.url }}" target="_blank"><strong>{{ r.title }}</strong></a><br>
            {{ r.price }} – {{ r.km }}
        </div>
    {% endfor %}
    {% endif %}
</body>
</html>
"""

START_PROMPT = [
    {"role": "system", "content": "Je bent een Nederlandse AI auto-assistent die mensen helpt bij het kiezen van een auto. Stel maximaal 3 vragen, genereer dan JSON filters (merk, brandstof, transmissie, kilometerstand)."},
    {"role": "assistant", "content": "Welkom bij Autino! Waarvoor wil je de auto vooral gebruiken? Stad, snelweg, of lange ritten?"}
]

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

@app.route("/", methods=["GET", "POST"])
def index():
    if "messages" not in session:
        session["messages"] = START_PROMPT.copy()

    messages = session["messages"]
    results = []

    if request.method == "POST":
        user_input = request.form.get("message", "")
        messages.append({"role": "user", "content": user_input})

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
            )
            reply = response["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            try:
                if "{" in reply:
                    filters = eval(reply.strip().split('\n')[-1])
                    results = real_scraper(filters)
            except:
                pass
        except Exception as e:
            messages.append({"role": "assistant", "content": f"Er ging iets mis met de AI: {e}"})

    session["messages"] = messages
    return render_template_string(HTML_TEMPLATE, messages=messages, results=results)

if __name__ == "__main__":
    app.run(debug=True)
