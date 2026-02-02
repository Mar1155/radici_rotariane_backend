from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import storages
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Verify S3 Static Files Configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- S3 DIAGNOSTICS ---'))
        
        # 1. Check Settings
        use_s3 = getattr(settings, 'USE_S3', False)
        self.stdout.write(f"USE_S3: {use_s3}")
        
        if not use_s3:
            self.stdout.write(self.style.ERROR("USE_S3 is False. Using local/whitenoise storage."))
            return

        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'NOT SET')
        region = getattr(settings, 'AWS_S3_REGION_NAME', 'NOT SET')
        static_url = settings.STATIC_URL
        
        self.stdout.write(f"Bucket: {bucket_name}")
        self.stdout.write(f"Region: {region}")
        self.stdout.write(f"STATIC_URL: {static_url}")
        
        # 2. Check Storage Backend
        try:
            storage = storages['staticfiles']
            self.stdout.write(f"Storage Backend: {storage.__class__.__name__}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not load staticfiles storage: {e}"))
            return

        # 3. Test Write/Read
        test_filename = 's3_test_file.txt'
        test_content = b'Hello S3 from Django!'
        
        self.stdout.write("Attempting to save test file...")
        try:
            saved_name = storage.save(test_filename, ContentFile(test_content))
            self.stdout.write(self.style.SUCCESS(f"Successfully saved file: {saved_name}"))
            
            file_url = storage.url(saved_name)
            self.stdout.write(f"File URL: {file_url}")
            
            self.stdout.write("\nPlease check if this URL is accessible in your browser.")
            if '?' in file_url:
                 self.stdout.write(self.style.WARNING("URL contains query parameters. Check AWS_QUERYSTRING_AUTH setting if this is unintended."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error communicating with S3: {e}"))
