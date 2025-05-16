import os
from flask import Flask, request, render_template_string, session
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
    <title>Autino AI Match</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body { font-family: Arial; padding: 20px; max-width: 800px; margin: auto; background: #f5f5f5; }
        .chat-box { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .car { background: #fff; padding: 10px; border: 1px solid #ddd; margin-bottom: 10px; border-radius: 6px; }
    </style>
</head>
<body>
    <h1>Autino – Slimme Autozoeker</h1>
    <div class="chat-box">
        {% for m in messages %}
            <p><strong>{{ m.role.capitalize() }}:</strong> {{ m.content }}</p>
        {% endfor %}
        <form method="post">
            <input type="text" name="message" style="width: 100%; padding: 10px;" placeholder="Waarvoor zoek je een auto?" required />
            <button type="submit" style="margin-top: 10px;">Verstuur</button>
        </form>
    </div>

    {% if results %}
        <h2>Beste matches voor jouw situatie</h2>
        {% for car in results %}
            <div class="car">
                <strong>{{ car.title }}</strong><br>
                {{ car.price }} – {{ car.km }}<br>
                <a href="{{ car.url }}" target="_blank">Bekijk</a>
            </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""


def get_broekhuis():
    url = 'https://www.broekhuis.nl/volvo/occasions/volvo-selekt'
    r = requests.get(url)
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

def get_volvo():
    url = 'https://selekt.volvocars.nl/nl-nl/store/'
    r = requests.get(url)
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

def get_voorraad():
    url = "https://www.vaartland.nl/voorraad"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for card in soup.select("div.vehicle-card")[:20]:
        title = card.select_one(".vehicle-card__title")
        price = card.select_one(".vehicle-card__price")
        km = card.select_one(".vehicle-card__mileage")
        link = card.select_one("a")
        description = title.text if title else ""
        if title and price and km and link:
            results.append({
                "title": title.text.strip(),
                "description": description,
                "price": price.text.strip(),
                "km": km.text.strip(),
                "url": "https://www.vaartland.nl" + link["href"]
            })
    return results

def rank_autos(user_description, cars):
    descriptions = [f"{car['title']}: {car['description']}" for car in cars]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Je bent een AI die de top 10 auto's kiest op basis van relevantie voor de omschrijving van een gebruiker."},
                {"role": "user", "content": f"Gebruiker zoekt: {user_description}

Auto's:
" + "\n".join(descriptions) + "

Geef een lijst van de 5 beste titels."}
            ],
            temperature=0.2
        )
        top_titles = response["choices"][0]["message"]["content"].split("\n")
        return [car for car in cars if any(title.strip().lower() in car['title'].lower() for title in top_titles)]
    except Exception as e:
        print("Ranking error:", e)
        return cars[:5]

@app.route("/", methods=["GET", "POST"])
def index():
    if "messages" not in session:
        session["messages"] = []
    messages = session["messages"]
    results = []

    if request.method == "POST":
        message = request.form.get("message", "")
        messages.append({"role": "user", "content": message})
        voorraad = get_voorraad() + get_broekhuis() + get_volvo()
        results = rank_autos(message, voorraad)
        messages.append({"role": "assistant", "content": "Ik heb auto's geselecteerd die het beste bij je beschrijving passen."})

    session["messages"] = messages
    return render_template_string(HTML_TEMPLATE, messages=messages, results=results)

if __name__ == "__main__":
    app.run(debug=True)
