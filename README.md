# Gavmild

Et personlig prosjekt for ønskelister, enkel admin-flyt og Telegram-integrasjon.

## Hva prosjektet er

Gavmild er en Flask-app med:
- Ønskelister
- WebAuthn-støtte
- Telegram-bot for varsler og kommandoer

## Teknologi (kortversjon)

- Python + Flask
- SQLAlchemy + MariaDB
- Flask-Login / Flask-WTF
- Docker Compose

## Kom i gang lokalt

Forutsetninger:
- Docker
- Tilgang til `secrets/`-filene lokalt

Start utviklingsmiljoet:

```bash
docker compose up -d
```

Applikasjonen kjører pa:
- http://localhost:5005

Nyttige kommandoer i hverdagen:

```bash
docker compose logs -f
docker compose logs -f webapp
docker compose restart
docker compose down
```

## Hvordan appen starter

- Flask app-factory er `app:create_app`
- Databasetabeller opprettes ved oppstart (`db.create_all()`)
- Første bruker (id=1) får admin-rettigheter automatisk
- Telegram-boten startes fra appen ved oppstart

## Konfigurasjon du bør vite om

- Miljø velges med `FLASK_ENV` (`development`, `production`, `testing`)
- DB-tilkobling bygges fra miljø + secrets
- Flere nøkler/tokens leses fra `secrets/` (Telegram, OpenAI, Flask secret, osv.)