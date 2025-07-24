from flask import Flask, render_template
from flights import get_nearby_flights

app = Flask(__name__)

@app.route("/")
def home():
    flights, timestamp, using_adsb = get_nearby_flights()
    return render_template("dashboard.html", flights=flights, timestamp=timestamp, using_adsb=using_adsb)

if __name__ == "__main__":
    app.run(debug=True)
