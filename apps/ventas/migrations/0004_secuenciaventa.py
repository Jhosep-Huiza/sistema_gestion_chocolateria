# Generada para agregar un contador correlativo bloqueable de ventas.

from django.db import migrations, models


def inicializar_secuencia(apps, schema_editor):
    Venta = apps.get_model("ventas", "Venta")
    SecuenciaVenta = apps.get_model("ventas", "SecuenciaVenta")
    ultimo_numero = 0
    for numero in Venta.objects.filter(numero_venta__startswith="VTA-").values_list("numero_venta", flat=True):
        try:
            ultimo_numero = max(ultimo_numero, int(numero.removeprefix("VTA-")))
        except ValueError:
            continue
    SecuenciaVenta.objects.get_or_create(pk=1, defaults={"ultimo_numero": ultimo_numero})


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0003_detalleventa_cantidad_reservada'),
    ]

    operations = [
        migrations.CreateModel(
            name='SecuenciaVenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ultimo_numero', models.PositiveBigIntegerField(default=0)),
            ],
            options={
                'db_table': 'secuencia_ventas',
            },
        ),
        migrations.RunPython(inicializar_secuencia, migrations.RunPython.noop),
    ]
