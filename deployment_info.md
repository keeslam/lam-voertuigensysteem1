# Deployment Handleiding - Autoverhuur Beheer Systeem

## Benodigde Dependencies
Installeer de volgende Python packages via pip:

```
flask==2.3.3
flask-login==0.6.2
flask-sqlalchemy==3.1.1
flask-wtf==1.2.1
gunicorn==23.0.0
psycopg2-binary==2.9.9
requests==2.31.0
routes==2.5.1
sendgrid==6.10.0
sqlalchemy==2.0.27
trafilatura==1.6.3
Werkzeug==2.3.7
email-validator==2.1.0.post1
```

## Omgevingsvariabelen
Stel de volgende omgevingsvariabelen in op uw server:

- `DATABASE_URL`: URL voor uw database-verbinding (PostgreSQL aanbevolen)
- `SESSION_SECRET`: Een lange, willekeurige string voor de sessiesleutel
- `SENDGRID_API_KEY`: (Optioneel) Voor het versturen van e-mails via SendGrid

## Bestandsstructuur
Alle bestanden uit deze Replit-repository moeten worden gekopieerd naar uw server.

## Database Setup
1. Maak een nieuwe database aan op uw PostgreSQL server
2. Stel de `DATABASE_URL` omgevingsvariabele in
3. Start de applicatie - de tabellen worden automatisch aangemaakt
4. De standaard inloggegevens zijn:
   - Gebruikersnaam: admin
   - Wachtwoord: admin123

## Server Starten
Gebruik Gunicorn om de applicatie te starten:

```
gunicorn --bind 0.0.0.0:5000 main:app
```

Of gebruik een WSGI-server zoals uWSGI, samen met een webserver zoals Nginx voor productiegebruik.

## Belangrijk voor Productie
1. Wijzig het standaard admin-wachtwoord direct na de eerste login
2. Stel HTTPS in via Nginx of een andere webserver
3. Overweeg het gebruik van een proces-manager zoals Supervisor voor het beheren van de applicatie
4. Maak regelmatig back-ups van uw database