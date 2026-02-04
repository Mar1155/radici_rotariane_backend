#!/usr/bin/env python
"""
Script per configurare il bucket S3 per permettere l'accesso pubblico ai file statici.

ATTENZIONE: Questo script richiede di:
1. Disabilitare "Block all public access" nelle impostazioni del bucket su AWS Console
2. Eseguire questo script per applicare la bucket policy

Uso:
    python scripts/configure_s3_bucket.py
"""

import json
import sys
import os

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.conf import settings

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERRORE: boto3 non è installato. Installalo con: pip install boto3")
    sys.exit(1)


def get_bucket_policy():
    """Genera la bucket policy per permettere l'accesso pubblico ai file statici."""
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/static/*"
            },
            {
                "Sid": "PublicReadGetMedia",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/media/*"
            }
        ]
    }
    return policy


def apply_bucket_policy():
    """Applica la bucket policy al bucket S3."""
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    region = settings.AWS_S3_REGION_NAME
    
    print(f"\n=== Configurazione Bucket S3: {bucket_name} ===\n")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=region
    )
    
    policy = get_bucket_policy()
    policy_json = json.dumps(policy, indent=2)
    
    print("Bucket Policy da applicare:")
    print(policy_json)
    print()
    
    try:
        # Verifica se il bucket esiste
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ Bucket '{bucket_name}' trovato")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"✗ ERRORE: Bucket '{bucket_name}' non trovato")
        else:
            print(f"✗ ERRORE: {e}")
        return False
    
    try:
        # Applica la bucket policy
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=policy_json
        )
        print(f"✓ Bucket policy applicata con successo!")
        print(f"\nI file statici sono ora accessibili pubblicamente:")
        print(f"  - https://{bucket_name}.s3.{region}.amazonaws.com/static/...")
        print(f"  - https://{bucket_name}.s3.{region}.amazonaws.com/media/...")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            print("\n✗ ERRORE: Accesso negato. Devi prima:")
            print("  1. Andare su AWS Console > S3 > rotarywebappdjango > Permissions")
            print("  2. Cliccare su 'Block public access (bucket settings)' > Edit")
            print("  3. DESELEZIONARE 'Block all public access'")
            print("  4. Salvare le modifiche")
            print("  5. Rieseguire questo script")
            print("\n  Oppure applica manualmente la seguente policy:")
            print("  AWS Console > S3 > rotarywebappdjango > Permissions > Bucket Policy > Edit")
            print()
            print(policy_json)
        else:
            print(f"✗ ERRORE: {e}")
        return False


def main():
    if not settings.USE_S3:
        print("ERRORE: USE_S3 non è abilitato nelle impostazioni Django.")
        sys.exit(1)
    
    print("=" * 60)
    print("CONFIGURAZIONE S3 PER ACCESSO PUBBLICO AI FILE STATICI")
    print("=" * 60)
    
    success = apply_bucket_policy()
    
    if not success:
        print("\n" + "=" * 60)
        print("ISTRUZIONI MANUALI:")
        print("=" * 60)
        print("""
Se lo script non riesce ad applicare la policy, segui questi passi:

1. Vai su AWS Console: https://console.aws.amazon.com/s3/

2. Seleziona il bucket: rotarywebappdjango

3. Vai su "Permissions" tab

4. In "Block public access (bucket settings)":
   - Clicca "Edit"
   - Deseleziona "Block all public access"
   - Salva

5. In "Bucket policy":
   - Clicca "Edit"
   - Incolla la policy mostrata sopra
   - Salva

6. Ri-esegui collectstatic:
   python manage.py collectstatic --noinput

L'admin Jazzmin dovrebbe ora caricare correttamente i CSS.
""")
        sys.exit(1)
    
    print("\n✓ Configurazione completata con successo!")
    sys.exit(0)


if __name__ == '__main__':
    main()
