"""Verifica che i media su S3 funzionino davvero.

Non basta che il caricamento riesca: il bucket deve anche lasciar leggere i
file a chi non ha credenziali, perche' e' il browser del visitatore a
scaricarli. Una scrittura che riesce con una policy che blocca la lettura e'
il guasto che si scopre solo in produzione, e questo comando lo anticipa.
"""

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

NOME = 'verifica-s3.txt'
CONTENUTO = b'Radici Rotariane: prova di scrittura e lettura.'


class Command(BaseCommand):
    help = 'Controlla la configurazione S3 dei media: scrive, rilegge, scarica, pulisce.'

    def handle(self, *args, **options):
        if not getattr(settings, 'USE_S3', False):
            self.stdout.write(self.style.WARNING(
                'USE_S3 non e\' attivo: i media restano sul disco del container.\n'
                'In produzione spariscono al primo riavvio.'))
            return

        firmati = getattr(settings, 'AWS_QUERYSTRING_AUTH', False)
        self.stdout.write(f'bucket   {settings.AWS_STORAGE_BUCKET_NAME}')
        self.stdout.write(f'dove     {getattr(settings, "AWS_S3_ENDPOINT_URL", None) or f"AWS {settings.AWS_S3_REGION_NAME}"}')
        self.stdout.write(f'storage  {type(default_storage).__name__}')
        self.stdout.write('accesso  ' + (
            f'URL firmati, validi {settings.AWS_QUERYSTRING_EXPIRE // 3600} ore'
            if firmati else 'URL pubblici'))

        salvato = None
        try:
            salvato = default_storage.save(NOME, ContentFile(CONTENUTO))
            self.stdout.write(self.style.SUCCESS(f'scrittura  {salvato}'))

            with default_storage.open(salvato) as f:
                if f.read() != CONTENUTO:
                    raise ValueError('il file riletto non corrisponde a quello scritto')
            self.stdout.write(self.style.SUCCESS('rilettura  contenuto identico'))

            url = default_storage.url(salvato)
            if firmati and '?' not in url:
                self.stdout.write(self.style.WARNING(
                    'lettura    ci si aspettava un URL firmato e non lo e\'.'))
            risposta = requests.get(url, timeout=10)
            if risposta.status_code == 200 and risposta.content == CONTENUTO:
                self.stdout.write(self.style.SUCCESS(f'lettura    200 da {url}'))
            else:
                spiegazione = (
                    '           la firma non viene accettata: controlla che\n'
                    '           AWS_S3_ENDPOINT_URL e la regione siano quelli del bucket.'
                    if firmati else
                    '           il bucket non e\' leggibile pubblicamente: nessuna\n'
                    '           immagine si vedra\' sul sito. Controlla la bucket policy,\n'
                    '           oppure attiva AWS_QUERYSTRING_AUTH=True.')
                self.stdout.write(self.style.ERROR(
                    f'lettura    {risposta.status_code} da {url.split("?")[0]}\n' + spiegazione))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'errore     {exc}'))
        finally:
            if salvato and default_storage.exists(salvato):
                default_storage.delete(salvato)
                self.stdout.write('pulizia    file di prova rimosso')
