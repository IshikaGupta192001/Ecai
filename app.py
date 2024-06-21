from flask import Flask, request, jsonify
from models import db, Appointment
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables before the first request using the app context
with app.app_context():
    db.create_all()

def find_nearest_available_slot(date, time):
    while True:
        # Check for conflicting appointments
        conflicting_appointment = Appointment.query.filter_by(date=date, time=time).first()
        if not conflicting_appointment:
            return date, time
        
        # Increment time by 30 minutes
        datetime_combined = datetime.combine(date, time) + timedelta(minutes=30)
        date = datetime_combined.date()
        time = datetime_combined.time()
        
        # If time exceeds 23:30, move to the next day
        if time > datetime.strptime("23:30", "%H:%M").time():
            date = date + timedelta(days=1)
            time = datetime.strptime("00:00", "%H:%M").time()

@app.route('/appointment', methods=['POST'])
def create_appointment():
    data = request.get_json()
    user_id = data.get('user_id')
    date_str = data.get('date')
    time_str = data.get('time')

    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    time = datetime.strptime(time_str, '%H:%M').time()

    # Check for existing appointment with the same user_id
    existing_appointment = Appointment.query.filter_by(user_id=user_id).first()
    if existing_appointment:
        return jsonify({'message': 'User already has an appointment', 'appointment': existing_appointment.to_dict()})

    # Check for conflicting appointment and suggest nearest available slot
    conflicting_appointment = Appointment.query.filter_by(date=date, time=time).first()
    if conflicting_appointment:
        nearest_date, nearest_time = find_nearest_available_slot(date, time)
        return jsonify({
            'message': 'The requested time slot is already taken. Suggested nearest available slot:',
            'suggested_date': nearest_date.isoformat(),
            'suggested_time': nearest_time.isoformat()
        })

    # Create new appointment
    new_appointment = Appointment(user_id=user_id, date=date, time=time)
    db.session.add(new_appointment)
    db.session.commit()

    return jsonify({'message': 'Appointment created', 'appointment': new_appointment.to_dict()})

if __name__ == '__main__':
    app.run(debug=True)
