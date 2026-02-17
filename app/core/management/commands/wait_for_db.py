"""Django command to wait for the database to be available."""
import time
from psycopg2 import OperationalError as Psycopg2Error
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django comando para a espera d base de dados esteje desponivel."""

    def handle(self, *args, **options):
        """Entrypoint for the command."""
        self.stdout.write("Aguardadno pela base de dados...")
        db_up = False
        while not db_up:
            try:
                self.check(databases=["default"])
                db_up = True
            except (Psycopg2Error, OperationalError):
                self.stdout.write(f"Base de dados nao disponvel, aguarde 1 second...")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS("Base de dados disponivel!"))