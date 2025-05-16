import os
from flask import Flask, request, render_template_string, session, redirect, url_for
import openai
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = "supersecretkey"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Autino – AI Auto Assistent</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body { font-family: Arial; padding: 20px; max-width: 800px; margin: auto; background: #f5f5f5; }
        .chat-box { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .car { background: #fff; padding: 10px; border: 1px solid #ddd; margin-bottom: 10px; border-radius: 6px; }
        .reset-link { float: right; margin-top: 10px; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>Autino – Slimme Autozoeker</h1>
    <div class="chat-box">
        <form method="POST" action="/">
            <a href="/reset" class="reset-link">Reset gesprek</a>
            {% for m in messages %}
                <p><strong>{% if m.role == 'assistant' %}Martino{% else %}{{ m.role.capitalize() }}{% endif %}:</strong> {{ m.content }}</p>
            {% endfor %}
            <input type="text" name="message" style="width: 100%; padding: 10px;" placeholder="Typ hier je antwoord..." required />
            <button type="submit" style="margin-top: 10px;">Verstuur</button>
        </form>
    </div>

    {% if results %}
        <h2>Beste matches voor jouw situatie</h2>
        {% for car in results %}
            <div class="car">
                <strong>{{ car.get('title', '') }}</strong><br>
                {{ car.get('price', '') }} – {{ car.get('km', '') }}<br>
                <a href="{{ car.get('url', '#') }}" target="_blank">Bekijk</a>
            </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""

INTRO_PROMPT = [
    {"role": "system", "content": "Je bent Martino, een slimme AI-autoassistent. Stel maximaal 5 vragen om te begrijpen wat voor auto de gebruiker nodig heeft. Zodra je genoeg weet, zeg dan: 'Dank je, ik zoek de best passende auto's voor je op.' en geef geen extra vragen meer."},
    {"role": "assistant", "content": "Welkom bij Autino! Ik ben Martino. Waarvoor zoek je een auto?"}
]

def get_all_autos():
    all_results = []
    for func in [get_vaartland, get_broekhuis, get_volvo]:
        try:
            all_results.extend(func())
        except:
            continue
    return all_results

def get_vaartland():
    try:
        url = "https://www.vaartland.nl/voorraad"
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for card in soup.select("div.vehicle-card")[:10]:
            title = card.select_one(".vehicle-card__title")
            price = card.select_one(".vehicle-card__price")
            km = card.select_one(".vehicle-card__mileage")
            link = card.select_one("a")
            if title and price and km and link:
                results.append({
                    "title": title.text.strip(),
                    "description": title.text.strip(),
                    "price": price.text.strip(),
                    "km": km.text.strip(),
                    "url": "https://www.vaartland.nl" + link["href"]
                })
        return results
    except:
        return []

def get_broekhuis():
    try:
        url = 'https://www.broekhuis.nl/volvo/occasions/volvo-selekt'
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []
        for card in soup.select('div.vehicle')[:10]:
            title = card.select_one('.vehicle__title')
            price = card.select_one('.vehicle__price')
            km = card.select_one('.vehicle__meta-item--mileage')
            link = card.select_one('a')
            if title and price and km and link:
                results.append({
                    'title': title.text.strip(),
                    'description': title.text.strip(),
                    'price': price.text.strip(),
                    'km': km.text.strip(),
                    'url': 'https://www.broekhuis.nl' + link['href']
                })
        return results
    except:
        return []

def get_volvo():
    try:
        url = 'https://selekt.volvocars.nl/nl-nl/store/'
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []
        for card in soup.select('div.result')[:10]:
            title = card.select_one('.title')
            price = card.select_one('.price')
            km = card.select_one('.mileage')
            link = card.select_one('a')
            if title and price and km and link:
                results.append({
                    'title': title.text.strip(),
                    'description': title.text.strip(),
                    'price': price.text.strip(),
                    'km': km.text.strip(),
                    'url': 'https://selekt.volvocars.nl' + link['href']
                })
        return results
    except:
        return []

def rank_autos(user_description, cars):
    descriptions = [f"{car['title']}: {car['description']}" for car in cars]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Je bent een AI die auto's selecteert op basis van een gebruikersbeschrijving. Kies de top 5 auto's uit deze lijst die het beste passen."
                },
                {
                    "role": "user",
                    "content": f"""Gebruiker zoekt: {user_description}

Hier zijn de beschikbare auto's:
{chr(10).join(descriptions)}

Noem de titels van de 5 beste auto's."""
                }
            ],
            temperature=0.3
        )
        top_titles = response["choices"][0]["message"]["content"].split("\n")
        matches = [car for car in cars if any(title.strip().lower() in car['title'].lower() for title in top_titles)]
        return matches if matches else cars[:5]
    except Exception as e:
        print("GPT matching error:", e)
        return cars[:5]

@app.route("/", methods=["GET", "POST"])
def index():
    if "messages" not in session:
        session["messages"] = INTRO_PROMPT.copy()
        session["question_count"] = 0
        session["gathering"] = True
        session["collected_info"] = ""

    messages = session["messages"]
    question_count = session.get("question_count", 0)
    gathering = session.get("gathering", True)
    results = []

    if request.method == "POST":
        user_input = request.form.get("message", "")
        messages.append({"role": "user", "content": user_input})
        session["collected_info"] += " " + user_input

        if gathering and question_count < 5:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.5
            )
            reply = response["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            session["question_count"] += 1

            if "ik zoek de best passende auto's" in reply.lower() or session["question_count"] >= 5:
                session["gathering"] = False
                voorraad = get_all_autos()
                results = rank_autos(session["collected_info"], voorraad)
        else:
            voorraad = get_all_autos()
            results = rank_autos(session["collected_info"], voorraad)

    session["messages"] = messages
    return render_template_string(HTML_TEMPLATE, messages=messages, results=results)

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
