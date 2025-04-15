# Deploymentgids voor Autoverhuur Beheer

Dit document bevat stapsgewijze instructies om het Autoverhuur Beheersysteem te exporteren uit Replit en te deployen op uw eigen server.

## Stap 1: Bestanden exporteren uit Replit

1. Klik rechtsboven op het "three dots" menu (⋮)
2. Selecteer "Download as zip"
3. Unzip het bestand op uw lokale machine

## Stap 2: Server voorbereiden

Zorg ervoor dat uw server het volgende heeft:

1. Python 3.10 of nieuwer geïnstalleerd
2. pip (Python package manager)
3. PostgreSQL database (aanbevolen, hoewel SQLite wordt ondersteund voor testing)
4. Webserver zoals Nginx (voor productiegebruik)

## Stap 3: Benodigde packages installeren

```bash
# Maak een virtuele omgeving aan (aanbevolen)
python -m venv venv
source venv/bin/activate  # Op Windows: venv\Scripts\activate

# Installeer alle benodigde packages
pip install flask==2.3.3 flask-login==0.6.2 flask-sqlalchemy==3.1.1 flask-wtf==1.2.1 \
    gunicorn==23.0.0 psycopg2-binary==2.9.9 requests==2.31.0 routes==2.5.1 \
    sendgrid==6.10.0 sqlalchemy==2.0.27 trafilatura==1.6.3 Werkzeug==2.3.7 \
    email-validator==2.1.0.post1
```

## Stap 4: Database configureren

1. Maak een nieuwe PostgreSQL database aan
2. Stel de database URL in als omgevingsvariabele:

```bash
# Voor PostgreSQL (aanbevolen voor productie)
export DATABASE_URL="postgresql://gebruiker:wachtwoord@localhost:5432/autoverhuur"

# OF voor SQLite (niet aanbevolen voor productie)
export DATABASE_URL="sqlite:///autoverhuur.db"
```

## Stap 5: Omgevingsvariabelen instellen

```bash
# Sessie-geheim instellen (vervang door een echte lange, willekeurige string)
export SESSION_SECRET="veilige-geheime-sleutel-hier"

# Optioneel voor e-mailfunctionaliteit
export SENDGRID_API_KEY="uw_sendgrid_api_key_hier"
export DEFAULT_MAIL_SENDER="noreply@uwbedrijf.nl"

# Omgeving instellen (development, testing of production)
export FLASK_ENV="production"
```

Voor permanente configuratie kunt u deze variabelen toevoegen aan `/etc/environment` of gebruiken in een .env bestand samen met python-dotenv.

## Stap 6: Mappen en permissies instellen

```bash
# Zorg ervoor dat de uploads map bestaat en schrijfbaar is
mkdir -p uploads/documents
chmod 755 uploads
chmod 755 uploads/documents
```

## Stap 7: Applicatie starten

### Voor ontwikkeling of testen:

```bash
python main.py
```

### Voor productie met Gunicorn:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

## Stap 8: Webserver configureren (voor productie)

Configureer Nginx als reverse proxy voor Gunicorn:

```nginx
server {
    listen 80;
    server_name autoverhuur.uwdomein.nl;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /pad/naar/uw/applicatie/static;
        expires 30d;
    }

    location /uploads {
        alias /pad/naar/uw/applicatie/uploads;
        internal;  # Voorkomt directe toegang, alles gaat via de applicatie
    }
}
```

Vergeet niet HTTPS in te stellen met bijvoorbeeld Let's Encrypt!

## Stap 9: Procesmanager configureren (aanbevolen)

Voor betrouwbare langdurige uitvoering, gebruik Supervisor:

```ini
[program:autoverhuur]
command=/pad/naar/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 main:app
directory=/pad/naar/applicatie
user=www-data
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
```

## Stap 10: Inloggen en systeem testen

1. Ga naar uw domein in de browser
2. Log in met standaard inloggegevens:
   - Gebruikersnaam: admin
   - Wachtwoord: admin123
3. **BELANGRIJK:** Wijzig onmiddellijk het admin-wachtwoord via het gebruikersbeheer

## Stap 11: Backups instellen

Configureer regelmatige database backups:

```bash
# Voorbeeld PostgreSQL backup script
pg_dump -U gebruiker autoverhuur > /backups/autoverhuur_$(date +%Y%m%d).sql
```

## Veiligheidsoverwegingen

1. Wijzig het standaard admin-wachtwoord direct
2. Gebruik altijd HTTPS in productie
3. Houd alle packages up-to-date
4. Maak regelmatig backups
5. Beperk toegang tot uw server met firewall-regels

## Onderhoud

1. Log regelmatig in en controleer op onregelmatigheden
2. Houd de server en alle software up-to-date
3. Monitor de server op CPU, geheugen en schijfgebruik

## Problemen oplossen

Als u problemen ondervindt, controleer:
1. De logbestanden van de applicatie (als u Gunicorn gebruikt, check de Gunicorn logs)
2. De Nginx foutlog (meestal in /var/log/nginx/error.log)
3. Controleer of alle vereiste omgevingsvariabelen zijn ingesteld
4. Controleer database-connectiviteit

Voor meer hulp, raadpleeg de Flask- en SQLAlchemy-documentatie of neem contact op met de ontwikkelaar.