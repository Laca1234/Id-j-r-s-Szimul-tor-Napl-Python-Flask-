# 🌤️ Időjárás Szimulátor & Napló (Python Flask)

Ez egy oktatási célú, rétegzett architektúrájú (MVC jellegű) webalkalmazás Pythonban. A projekt nem használ külső időjárási API-kat, hanem saját, évszak-alapú logikával generál véletlenszerű, de logikus időjárási adatokat, kiszámolja a hőérzetet, és perzisztensen elmenti azokat egy JSON fájlba.

## 🛠️ Architektúra és Fájlstruktúra

A kód szigorúan szét van választva különböző felelősségi körökre:

* **`app.py`** (Controller réteg): A Flask webalkalmazás magja, amely kezeli a HTTP kéréseket és összeköti a nézetet a logikával.
* **`engine.py`** (Engine / Üzleti logika réteg): Felelős az időjárási adatok (hőmérséklet, szél, páratartalom, állapot) generálásáért és a komfortindex számításáért.
* **`service.py`** (Service / Adatkezelési réteg): Kezeli az adatok olvasását és írását a helyi JSON fájlba.
* **`templates/index.html`**: A reszponzív HTML felület.
* **`static/style.css`**: Különálló, modern CSS fájl a vizuális megjelenésért.

---

## 🚀 Telepítés és Futtatás

1. **Klónozd a repót vagy töltsd le a fájlokat:**
   ```bash
   git clone [https://github.com/felhasznaloneved/weather-simulator.git](https://github.com/felhasznaloneved/weather-simulator.git)
   cd weather_project