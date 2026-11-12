# Generada para asociar a cada detalle las unidades provenientes de stock reservado.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0002_pagoventa_chk_pago_venta_monto_gte_0'),
    ]

    operations = [
        migrations.AddField(
            model_name='detalleventa',
            name='cantidad_reservada',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
    ]
