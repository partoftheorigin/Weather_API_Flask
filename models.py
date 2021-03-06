import dateutil.parser
from getweather import get_weather
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.blocking import BlockingScheduler

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'

db = SQLAlchemy(app)


class City(db.Model):
    __tablename__ = 'city'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    country = db.Column(db.String(50), nullable=False)


class Weather(db.Model):
    __tablename__ = 'weather'
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Integer)
    loc_id = db.Column(db.Integer, db.ForeignKey("city.id"))
    date = db.Column(db.String(20))
    description = db.Column(db.String(50))


# All cities in the system
@app.route("/city", methods=["GET"])
def get_all_cities():
    cities = City.query.all()
    output = []
    for city in cities:
        city_data = {}
        city_data['id'] = city.id
        city_data['name'] = city.name
        city_data['country'] = city.country
        output.append(city_data)
    return jsonify({'cities': output})


# Add a new city to the system
@app.route('/city', methods=['POST'])
def add_city():
    city = request.args.get('city', '').lower()
    country = request.args.get('country', '').lower()
    print(City.query.filter_by(name = city, country = country).first())
    if City.query.filter_by(name = city, country = country).first() == None:
        new_city = City(name=city, country=country)
        db.session.add(new_city)
        db.session.commit()
        return jsonify({'message': 'new city added'})
    else:
        return jsonify({'message': 'city already in database'})


# Get a city details by id
@app.route("/city/<int:id>", methods=["GET"])
def get_one_city(id):
    city = City.query.filter_by(id=id).first()
    if not city:
        return jsonify({"messsage": "No City Found"})
    city_data = {}
    city_data['name'] = city.name
    city_data['country'] = city.country
    return jsonify({"city": city_data})


# Delete a city by id
@app.route("/city/<int:id>", methods=["DELETE"])
def delete_city(id):
    city = City.query.filter_by(id=id).first()
    if not city:
        return jsonify({"messsage": "No City Found"})
    db.session.delete(city)
    db.session.commit()
    return jsonify({'message': 'City Deleted'})


# Get weather of all cities for last 5 days
@app.route('/weather/allcities', methods=['GET'])
def get_weather_all():
    reports = Weather.query.all()
    output = list()
    for report in reports:
        report_date = dateutil.parser.parse(report.date)
        if (datetime.now() - report_date).days < 6:
            weather_data = dict()
            weather_data['id'] = report.id
            weather_data['name'] = ''.join([city.name for city in City.query.all() if city.id == report.loc_id])
            weather_data['country'] = ''.join([city.country for city in City.query.all() if city.id == report.loc_id])
            weather_data['temperature'] = report.temperature
            weather_data['date'] = report.date
            weather_data['description'] = report.description
            output.append(weather_data)
    return jsonify({'weather': output})


# Get weather report by city and date filter
@app.route('/weather/filter', methods=['GET'])
def get_weather_filter():
    city = request.args.get('city', '').lower()
    date = request.args.get('date', '').lower()
    reports = Weather.query.all()
    # print(City.query.all())
    output = list()
    for report in reports:
        if city == ''.join([city.name for city in City.query.all() if city.id == report.loc_id]) and date in report.date:
            # print(City.query.filter_by(id = report.loc_id).get('name'))
            weather_data = dict()
            weather_data['id'] = report.id
            weather_data['name'] = ''.join([city.name for city in City.query.all() if city.id == report.loc_id])
            weather_data['country'] = ''.join([city.country for city in City.query.all() if city.id == report.loc_id])
            weather_data['temperature'] = report.temperature
            weather_data['date'] = report.date
            weather_data['description'] = report.description
            output.append(weather_data)
    return jsonify({'weather': output})

# Get weather report for a given city and store data in database
@app.route('/weather', methods=['POST'])
def get_report():
    city = request.args.get('city', '').lower()
    country = request.args.get('country', '').lower()
    report = get_weather(city, country)

    if City.query.filter_by(name = city, country = country).first() == None:
        new_city = City(name=city, country=country)
        db.session.add(new_city)
        db.session.commit()
        # return jsonify({'message': 'new city added'})
    new_report = Weather(loc_id=int(str(City.query.filter_by(name = city, country = country).first()).strip('<City >')), temperature=report['temperature'], date=report['date'], description=report['description'])
    db.session.add(new_report)
    db.session.commit()
    return jsonify({'message': 'new report added'})


# Update a particular weather report by id
@app.route('/weather/<int:id>', methods=['PUT'])
def update_report(id):
    report = Weather.query.filter_by(id=id).first()

    data = request.get_json()
    report.temperature = data['temperature']
    report.date = data['date']
    db.session.commit()
    return jsonify({'message': 'Report Updated'})


# Delete a particular weather report by id
@app.route('/weather/<int:id>', methods=['DELETE'])
def delete_report(id):
    report = Weather.query.filter_by(id=id).first()
    if not report:
        return jsonify({"messsage": "No Report Found"})
    db.session.delete(report)
    db.session.commit()
    return jsonify({'message': 'Report Deleted'})


def job_function():
    city = 'bangalore'
    country = 'in'
    report = get_weather(city, country)
    
    new_report = Weather(loc_id=int(str(City.query.filter_by(name = city, country = country).first()).strip('<City >')), temperature=report['temperature'],
                         date=report['date'], description=report['description'])
    db.session.add(new_report)
    db.session.commit()
    return jsonify({'message': 'new report added'})


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
    sched = BlockingScheduler()
    # Schedule job_function to be called every twenty four hours
    sched.add_job(job_function, 'interval', hours=24, start_date='2017-12-13 17:00:00')
    sched.start()
