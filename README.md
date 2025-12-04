# Radici Rotariane Server

Backend Django per il progetto Radici Rotariane.

## Traduzione messaggi chat

La traduzione dei messaggi sfrutta provider esterni (DeepL, Google Cloud Translation) con caching locale.
Configura le seguenti variabili nel tuo `.env` per abilitarla:

```env
DEEPL_API_KEY=your-deepl-key
GOOGLE_TRANSLATE_API_KEY=your-google-key
TRANSLATION_SUPPORTED_LANGUAGES=it,en,es,fr,de
TRANSLATION_PROVIDER_PRIORITY=deepl,google
TRANSLATION_HTTP_TIMEOUT=10
```

- Imposta almeno una delle chiavi `DEEPL_API_KEY` o `GOOGLE_TRANSLATE_API_KEY`.
- `TRANSLATION_SUPPORTED_LANGUAGES` accetta una lista di codici ISO2 separati da virgole.
- L'ordine in `TRANSLATION_PROVIDER_PRIORITY` decide il fallback tra i provider configurati.
