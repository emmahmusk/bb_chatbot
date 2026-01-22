from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Drops all tables in the current database"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    -- disable referential integrity temporarily
                    EXECUTE 'DROP SCHEMA public CASCADE';
                    EXECUTE 'CREATE SCHEMA public';
                END $$;
            """)
        self.stdout.write(self.style.SUCCESS("All tables dropped and schema recreated."))
