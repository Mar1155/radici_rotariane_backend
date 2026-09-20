"""Tetti di frequenza per le operazioni che costano.

Non sono una misura di sicurezza — per quella ci sono i permessi — ma di
spesa. Ogni articolo, post, commento e messaggio fa partire una traduzione a
pagamento; ogni immagine caricata occupa spazio. Senza un tetto, un ciclo
lasciato acceso per sbaglio diventa una bolletta.

Le soglie stanno in `DEFAULT_THROTTLE_RATES` e si cambiano da variabile
d'ambiente senza toccare il codice, perche' il numero giusto lo si scopre
guardando l'uso vero.
"""

from rest_framework.throttling import UserRateThrottle


class Scrittura(UserRateThrottle):
    """Tutto cio' che crea contenuto da tradurre."""

    scope = 'scrittura'


class Caricamento(UserRateThrottle):
    """Tutto cio' che finisce nel bucket."""

    scope = 'caricamento'


class SoloInScrittura:
    """Mixin per i ViewSet: il tetto vale solo su POST.

    Un ViewSet mescola letture e scritture sotto lo stesso indirizzo, e
    mettere `throttle_classes` sulla classe limiterebbe anche chi sta solo
    leggendo — che non costa niente. Qui il tetto si applica dove nasce la
    spesa, cioe' dove nasce il contenuto.
    """

    def get_throttles(self):
        if self.request.method == 'POST':
            return [Scrittura()]
        return super().get_throttles()
