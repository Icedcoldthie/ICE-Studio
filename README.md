# ICE Studio 1.1 – Living Farmer Cohost

ICE = Intelligent Cohost Engine

Versie 1.1 bouwt verder op de werkende 1.0 en voegt de eerste levende OBS-avatar en lokale stem toe.

## Nieuw in 1.1

- Transparante OBS Browser Source via `http://127.0.0.1:8765/avatar`
- Humanoïde ICE-avatar met boerenkleding
- Knipperende ogen en idle-beweging
- Automatische mondanimatie tijdens antwoorden
- Automatische emotieherkenning
- OBS-ondertiteling
- Avatar-testpaneel in het dashboard
- Acht testbare emoties
- Optionele lokale Windows TTS via `System.Speech`
- Instelbare stemnaam, snelheid en volume
- Ieder antwoord uit Twitch of de dashboardtest wordt naar avatar en stem gestuurd
- Alle functies van ICE Studio 1.0 blijven aanwezig

## Starten

1. Zorg dat Ollama draait.
2. Controleer het model met:
   `ollama run qwen3:4b`
3. Dubbelklik op `run.bat`.
4. Open het dashboard:
   `http://127.0.0.1:8765`

## Avatar in OBS zetten

1. Start ICE Studio.
2. Open OBS.
3. Voeg een **Browser Source** toe.
4. Gebruik URL:
   `http://127.0.0.1:8765/avatar`
5. Aanbevolen formaat: 800 × 1000.
6. Plaats en schaal ICE naar wens in je scène.

De avatarpagina heeft standaard een transparante achtergrond.

## Stem

Ga in het dashboard naar **Avatar & stem**.

- Zet **Lokale Windows-stem inschakelen** aan.
- Laat stemnaam leeg om de standaard Windows-stem te gebruiken.
- Pas snelheid en volume aan.
- Gebruik **Test avatar en stem**.

OBS moet het Windows/desktopgeluid vastleggen om ICE hoorbaar te maken op stream.

## Streamer.bot

1. Zet de WebSocket Server aan in Streamer.bot.
2. Standaardadres: `ws://127.0.0.1:8080/`
3. Maak de actie `ICE - Send Chat`.
4. Voeg Twitch > Chat > Send Message toe.
5. Bericht: `%ice_message%`

## Veilig leren

ICE slaat zijn eigen antwoorden niet automatisch als feiten op. Via het Learning Center kun je antwoorden goedkeuren, afkeuren of corrigeren. Correcties worden aan de lokale kennisbank toegevoegd.
