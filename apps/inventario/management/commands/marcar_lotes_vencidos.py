from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from apps.inventario.services import marcar_lotes_vencidos


class Command(BaseCommand):
    help = "Retira del stock los lotes vencidos; puede programarse para ejecutarse a diario."

    def handle(self, *args, **options):
        try:
            resultado = marcar_lotes_vencidos()
        except ValidationError as error:
            raise CommandError("No se pudo completar la actualización de vencimientos: " + " ".join(error.messages)) from error
        self.stdout.write(self.style.SUCCESS(
            f"Lotes marcados vencidos: {resultado['marcados']}. "
            f"Movimientos de retiro creados: {resultado['movimientos']}."
        ))
