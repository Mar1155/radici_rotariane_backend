"""Le traduzioni scritte da una persona, che nessuno deve riscrivere.

I seed non portano solo contenuto italiano: portano anche coppie che qualcuno
ha scelto. "Puglia" si dice "Apulia", "Gestione Progetti" si dice "Project
Management", e "Six Sigma" non si dice affatto — resta "Six Sigma". Sono
decisioni, non traduzioni da rifare.

`locked_paths` e' cio' che le protegge: `translate_pending --forza` ritraduce
tutto il resto e salta i percorsi bloccati. Senza, al primo ripasso una
provincia italiana diventerebbe quello che il modello linguistico pensa che
debba diventare.

Stava dentro `seed_geo` come funzione privata. Da quando serve anche ai tre
cataloghi del profilo starebbe in quattro copie, ed e' il genere di funzione
che in quattro copie si aggiorna in tre.
"""

from __future__ import annotations


def fissa(oggetto, lingua: str, testi: dict[str, str], *, da: str = 'it') -> None:
    """Scrive (o aggiorna) la traduzione umana di un oggetto, e la blocca."""
    from django.contrib.contenttypes.models import ContentType

    from traduzione.models import Traduzione, impronta
    from traduzione.percorsi import estrai

    Traduzione.objects.update_or_create(
        content_type=ContentType.objects.get_for_model(oggetto),
        object_id=str(oggetto.pk), target_language=lingua,
        defaults=dict(source_language=da, texts=dict(testi),
                      locked_paths=sorted(testi), provider='umano',
                      needs_review=False,
                      # L'impronta dell'originale, come la scriverebbe il
                      # motore. Senza, il ripasso degli arretrati torna su
                      # questa riga a ogni avvio: non paga niente (i percorsi
                      # sono bloccati, non c'e' niente da chiedere) ma la
                      # riscrive, e `provider` diventa il nome del motore su
                      # un testo che ha scritto una persona.
                      source_digest=impronta(estrai(oggetto))),
    )
