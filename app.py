import openai
from flask import Flask, render_template_string, request, session
import requests
from bs4 import BeautifulSoup
import re

openai.api_key = "YOUR_OPENAI_API_KEY"

app = Flask(__name__)
app.secret_key = "supersecretkey"

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
    <title>Autino – AutoZoeker AI</title>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link rel='icon' href='/static/autino_logo.png' type='image/png'>
    <style>
        body { font-family: Arial; background:#f4f4f4; padding:20px; }
        h1 { color:#1e3a8a; }
        form { background:#fff; padding:20px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1); }
        input, select, button { margin-top:5px; padding:8px; width:100%; max-width:400px; box-sizing:border-box; }
        button { background:#1e3a8a; color:#fff; border:none; border-radius:4px; }
        ul { list-style:none; padding:0; }
        li { background:#fff; padding:15px; margin-bottom:10px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }
        img.logo { width:150px; }
        @media (max-width:600px) {
            body { padding:10px; }
            img.logo { width:120px; }
        }
    </style>
</head>
<body>
    <img src="/static/autino_logo.png" alt="Autino logo" class="logo" />
    <p style="margin-top:0; color:#1e3a8a; font-weight:bold;">Wij helpen je</p>
    <p style="margin-top:4px; color:#555; font-size:0.9em;">Met AI naar jouw perfecte auto</p>
    <h1>Zoek een auto met AI + filters</h1>

    <form method="post">
        <input name="query" placeholder="Bijv: Ik zoek een elektrische Kia met automaat" /><br><br>
        <label>Merk:</label>
        <select name="merk"><option value="">--</option><option value="Kia">Kia</option><option value="Volvo">Volvo</option></select>
        <label>Brandstof:</label>
        <select name="brandstof"><option value="">--</option><option value="elektrisch">Elektrisch</option><option value="benzine">Benzine</option></select>
        <label>Transmissie:</label>
        <select name="transmissie"><option value="">--</option><option value="automaat">Automaat</option><option value="handgeschakeld">Handgeschakeld</option></select>
        <label>Max kilometerstand:</label>
        <input type="number" name="kilometerstand" />
        <label>Minimaal aantal zitplaatsen:</label>
        <input type="number" name="zitplaatsen" />
        <button type="submit">Zoeken</button>
    </form>

    {% if results %}
        <h2>Resultaten</h2>
        <ul>
        {% for r in results %}
            <li><img src="{{ r.img }}" alt="auto" width="200"><br>
                <a href="{{ r.url }}" target="_blank">{{ r.title }}</a> - {{ r.price }} - {{ r.km }}
            </li>
        {% endfor %}
        </ul>
    {% endif %}

    <hr style="margin-top:40px;">
    <h3>Hoe werkt het?</h3>
    <p>Vertel ons wat voor auto je zoekt in gewone taal. Beantwoord drie korte vragen zodat we je beter begrijpen. Daarna laten we je direct auto's zien die bij je passen, uit betrouwbare Nederlandse voorraad.</p>
    <p style="text-align:center; font-size:0.8em; color:#888; margin-top:60px;">Made in Amsterdam XXX</p>
</body>
</html>"""

def extract_filters(query):
    return {"merk": "Kia", "brandstof": "elektrisch", "transmissie": "automaat", "kilometerstand": "80000", "zitplaatsen": "5"}

def parse_km(km_str):
    match = re.search(r"(\d[\d.]*)", km_str.replace('.', '').replace(',', ''))
    return int(match.group(1)) if match else None

def apply_filters(cars, filters):
    filtered = []
    for car in cars:
        title = car['title'].lower()
        km = parse_km(car['km'])
        if filters.get("merk") and filters["merk"].lower() not in title:
            continue
        filtered.append(car)
    return filtered

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    if request.method == "POST":
        query = request.form.get("query", "")
        filters = extract_filters(query)
        results = apply_filters([
            {"title": "Kia e-Niro", "price": "€25.000", "km": "60.000", "url": "#", "img": "/static/autino_logo.png"}
        ], filters)
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == "__main__":
    app.run(debug=True)
