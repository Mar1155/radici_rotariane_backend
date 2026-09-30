"""Una risposta che dipende dalla lingua del lettore lo deve dichiarare.

`Accept-Language` decide il contenuto di quasi ogni risposta dell'API, e tre
endpoint del CMS dicono `Cache-Control: public`. Senza `Vary`, una cache
condivisa — il browser, un proxy, la CDN di Vercel — servirebbe all'inglese la
copia italiana che ha appena dato a qualcun altro: un guasto che non si
riproduce quando lo si cerca, perche' dipende da chi e' passato prima.

Un middleware e non una riga su ogni vista: le viste che servono contenuto sono
decine e crescono, e quella dimenticata non darebbe errore.
"""

from django.utils.cache import patch_vary_headers


class VariaConLaLingua:
    """Aggiunge `Vary: Accept-Language` alle risposte dell'API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        risposta = self.get_response(request)
        if request.path.startswith('/api/'):
            patch_vary_headers(risposta, ['Accept-Language'])
        return risposta
