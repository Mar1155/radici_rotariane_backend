"""Runner dei test.

Esiste per una cosa sola: spegnere la traduzione in sottofondo. Quella apre un
thread con una connessione propria, e un thread ancora vivo quando i test
finiscono impedisce di cancellare il database di prova — la suite passa e il
comando esce lo stesso con errore, che e' il modo peggiore di fallire.

La traduzione ha i suoi test in `traduzione/`, dove viene chiamata
direttamente: spegnerla qui non lascia scoperto niente.
"""

from django.conf import settings
from django.test.runner import DiscoverRunner


class Runner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.TRADUZIONE_IN_SOTTOFONDO = False
