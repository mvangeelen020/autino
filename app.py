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
                    results = mock_scraper(filters)
                else:
                    results = []
            except:
                results = []

        except Exception as e:
            messages.append({"role": "assistant", "content": f"Er ging iets mis met de AI: {e}"})

        session["messages"] = messages

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
