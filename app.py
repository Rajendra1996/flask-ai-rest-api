from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    temperatures = db.relationship('Temperature', backref='room', lazy=True, cascade="all, delete")

class Temperature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    temperature = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))

# Ensure that db.create_all() is called within an application context
with app.app_context():
    db.create_all()

# Create a Room
@app.post("/api/room")
def create_room():
    data = request.get_json()
    new_room = Room(name=data["name"])
    db.session.add(new_room)
    db.session.commit()
    return {"id": new_room.id, "message": f"Room {new_room.name} created."}, 201

# Add a temperature
@app.post("/api/temperature")
def add_temp():
    data = request.get_json()
    room_id = data["room"]
    temperature = data["temperature"]
    date = datetime.strptime(data.get("date", datetime.now(timezone.utc).strftime("%m-%d-%Y %H:%M:%S")), "%m-%d-%Y %H:%M:%S")
    new_temp = Temperature(room_id=room_id, temperature=temperature, date=date)
    db.session.add(new_temp)
    db.session.commit()
    return {"message": "Temperature added."}, 201

@app.get("/api/average")
def get_global_avg():
    avg_temp = db.session.query(db.func.avg(Temperature.temperature)).scalar()
    distinct_days = db.session.query(db.func.count(db.distinct(db.func.date(Temperature.date)))).scalar()
    return {"average": round(avg_temp if avg_temp else 0, 2), "days": distinct_days}

@app.get("/api/room/<int:room_id>")
def get_room_all(room_id):
    room = Room.query.get_or_404(room_id)
    term = request.args.get("term")
    if term:
        return get_room_term(room_id, term)
    else:
        temperatures = room.temperatures
        if temperatures:
            avg_temp = sum(temp.temperature for temp in temperatures) / len(temperatures)
            distinct_days = len({temp.date.date() for temp in temperatures})
        else:
            avg_temp = 0
            distinct_days = 0
        return {"name": room.name, "average": round(avg_temp, 2), "days": distinct_days}


def get_room_term(room_id, term):
    terms = {"week": 7, "month": 30}
    room = Room.query.get_or_404(room_id)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=terms[term])

    temperatures = Temperature.query.filter(
        Temperature.room_id == room_id,
        Temperature.date >= start_date
    ).all()

    if temperatures:
        avg_temp = sum(temp.temperature for temp in temperatures) / len(temperatures)
        temperatures_formatted = [(temp.date.strftime("%Y-%m-%d"), temp.temperature) for temp in temperatures]
    else:
        avg_temp = 0
        temperatures_formatted = []

    return {
        "name": room.name,
        "temperatures": temperatures_formatted,
        "average": round(avg_temp, 2)
    }



if __name__ == '__main__':
    app.run(debug=True)
