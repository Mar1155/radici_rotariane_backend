import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from users.models import User

# List of international clubs to remove
clubs_to_remove = [
    "rc_newyork", "rc_london", "rc_paris", "rc_tokyo", 
    "rc_sydney", "rc_berlin", "rc_madrid", "rc_saopaulo"
]

print("Removing international clubs...")
for username in clubs_to_remove:
    try:
        user = User.objects.get(username=username)
        user.delete()
        print(f"Deleted {username}")
    except User.DoesNotExist:
        pass

clubs_data = [
    {
        "username": "rc_milano",
        "email": "info@rcmilano.it",
        "password": "password123",
        "club_name": "Rotary Club Milano",
        "club_city": "Milano",
        "club_country": "Italy",
        "club_district": "2041",
        "club_latitude": 45.4642,
        "club_longitude": 9.1900,
        "club_members_count": 120,
        "club_sister_clubs_count": 5,
        "bio": "<p>Il Rotary Club Milano, fondato nel 1923, è il primo club in Italia. Impegnato in progetti di servizio locali e internazionali.</p>"
    },
    {
        "username": "rc_roma",
        "email": "info@rcroma.it",
        "password": "password123",
        "club_name": "Rotary Club Roma",
        "club_city": "Roma",
        "club_country": "Italy",
        "club_district": "2080",
        "club_latitude": 41.9028,
        "club_longitude": 12.4964,
        "club_members_count": 150,
        "club_sister_clubs_count": 8,
        "bio": "<p>Il Rotary Club Roma è uno dei più antichi e prestigiosi d'Italia, attivo nella promozione della cultura e del servizio umanitario.</p>"
    },
    {
        "username": "rc_torino",
        "email": "info@rctorino.it",
        "password": "password123",
        "club_name": "Rotary Club Torino",
        "club_city": "Torino",
        "club_country": "Italy",
        "club_district": "2031",
        "club_latitude": 45.0703,
        "club_longitude": 7.6869,
        "club_members_count": 110,
        "club_sister_clubs_count": 4,
        "bio": "<p>Il Rotary Club Torino promuove l'etica professionale e la solidarietà sociale nel capoluogo piemontese.</p>"
    },
    {
        "username": "rc_napoli",
        "email": "info@rcnapoli.it",
        "password": "password123",
        "club_name": "Rotary Club Napoli",
        "club_city": "Napoli",
        "club_country": "Italy",
        "club_district": "2101",
        "club_latitude": 40.8518,
        "club_longitude": 14.2681,
        "club_members_count": 130,
        "club_sister_clubs_count": 6,
        "bio": "<p>Il Rotary Club Napoli è impegnato in numerose iniziative per la valorizzazione del territorio e il supporto alle fasce deboli.</p>"
    },
    {
        "username": "rc_firenze",
        "email": "info@rcfirenze.it",
        "password": "password123",
        "club_name": "Rotary Club Firenze",
        "club_city": "Firenze",
        "club_country": "Italy",
        "club_district": "2071",
        "club_latitude": 43.7696,
        "club_longitude": 11.2558,
        "club_members_count": 105,
        "club_sister_clubs_count": 7,
        "bio": "<p>Il Rotary Club Firenze unisce professionisti e leader per servire la comunità nella culla del Rinascimento.</p>"
    },
    {
        "username": "rc_bologna",
        "email": "info@rcbologna.it",
        "password": "password123",
        "club_name": "Rotary Club Bologna",
        "club_city": "Bologna",
        "club_country": "Italy",
        "club_district": "2072",
        "club_latitude": 44.4949,
        "club_longitude": 11.3426,
        "club_members_count": 115,
        "club_sister_clubs_count": 3,
        "bio": "<p>Il Rotary Club Bologna sostiene progetti educativi e culturali nella storica città universitaria.</p>"
    },
    {
        "username": "rc_venezia",
        "email": "info@rcvenezia.it",
        "password": "password123",
        "club_name": "Rotary Club Venezia",
        "club_city": "Venezia",
        "club_country": "Italy",
        "club_district": "2060",
        "club_latitude": 45.4408,
        "club_longitude": 12.3155,
        "club_members_count": 95,
        "club_sister_clubs_count": 9,
        "bio": "<p>Il Rotary Club Venezia si dedica alla salvaguardia del patrimonio artistico e ambientale della laguna.</p>"
    },
    {
        "username": "rc_genova",
        "email": "info@rcgenova.it",
        "password": "password123",
        "club_name": "Rotary Club Genova",
        "club_city": "Genova",
        "club_country": "Italy",
        "club_district": "2032",
        "club_latitude": 44.4056,
        "club_longitude": 8.9463,
        "club_members_count": 125,
        "club_sister_clubs_count": 5,
        "bio": "<p>Il Rotary Club Genova opera attivamente per il benessere della comunità ligure e internazionale.</p>"
    },
    {
        "username": "rc_palermo",
        "email": "info@rcpalermo.it",
        "password": "password123",
        "club_name": "Rotary Club Palermo",
        "club_city": "Palermo",
        "club_country": "Italy",
        "club_district": "2110",
        "club_latitude": 38.1157,
        "club_longitude": 13.3615,
        "club_members_count": 140,
        "club_sister_clubs_count": 4,
        "bio": "<p>Il Rotary Club Palermo promuove lo sviluppo sociale ed economico nel cuore del Mediterraneo.</p>"
    },
    {
        "username": "rc_bari",
        "email": "info@rcbari.it",
        "password": "password123",
        "club_name": "Rotary Club Bari",
        "club_city": "Bari",
        "club_country": "Italy",
        "club_district": "2120",
        "club_latitude": 41.1171,
        "club_longitude": 16.8719,
        "club_members_count": 100,
        "club_sister_clubs_count": 2,
        "bio": "<p>Il Rotary Club Bari è un punto di riferimento per il servizio e l'amicizia nel capoluogo pugliese.</p>"
    }
]

print("Populating Italian clubs...")
for data in clubs_data:
    if not User.objects.filter(username=data['username']).exists():
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            user_type='CLUB',
            club_name=data['club_name'],
            club_city=data['club_city'],
            club_country=data['club_country'],
            club_district=data['club_district'],
            club_latitude=data['club_latitude'],
            club_longitude=data['club_longitude'],
            club_members_count=data['club_members_count'],
            club_sister_clubs_count=data['club_sister_clubs_count'],
            bio=data['bio']
        )
        print(f"Created club: {user.club_name}")
    else:
        print(f"Club already exists: {data['club_name']}")

print("Done populating clubs.")
