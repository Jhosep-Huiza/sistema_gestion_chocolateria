# ChocoGest — Sistema de gestión para chocolatería

Proyecto Django + MySQL con interfaz administrativa propia y módulos comerciales.

## Requisitos
- Python 3.10 o superior (recomendado 3.11/3.12)
- MySQL 8.x o MariaDB compatible
- Cliente de compilación de `mysqlclient` si tu entorno lo requiere

## Instalación en Windows (PowerShell)

```powershell
cd ChocoGest
py -m venv venv
.env\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y configura DB_NAME, DB_USER, DB_PASSWORD, DB_HOST y DB_PORT.

Crea la base de datos en MySQL:

```sql
CREATE DATABASE chocogest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Genera y aplica migraciones:

```powershell
python manage.py makemigrations usuarios clientes productos proveedores compras inventario ventas devoluciones caja finanzas configuracion
python manage.py migrate
python manage.py cargar_datos_iniciales
python manage.py createsuperuser
python manage.py runserver
```

Abre http://127.0.0.1:8000/

## Acceso
- `http://127.0.0.1:8000/` — Dashboard (requiere autenticación)
- `http://127.0.0.1:8000/login/` — Inicio de sesión
- `http://127.0.0.1:8000/admin/` — Administración Django

## Aplicaciones
- `usuarios`: usuario personalizado, roles y auditoría
- `clientes`: clientes y CRUD inicial
- `productos`: categorías, marcas, productos y CRUD inicial
- `proveedores`: proveedores y CRUD inicial
- `compras`: compras, detalles y pagos
- `inventario`: almacenes, inventario, lotes y movimientos
- `ventas`: ventas, detalles y pagos
- `devoluciones`: devoluciones y detalles
- `caja`: cajas y movimientos
- `finanzas`: gastos
- `reportes`: dashboard inicial
- `configuracion`: métodos de pago y datos del negocio

## Consideraciones importantes
1. El modelo `Usuario` personalizado está configurado desde el inicio. No cambies `AUTH_USER_MODEL` después de migrar.
2. Las tablas se generan mediante las migraciones de Django. El ZIP incluye los paquetes `migrations`, y debes generar las migraciones en tu entorno con los comandos anteriores.
3. Los módulos de clientes, productos y proveedores incluyen CRUD web inicial. Compras, ventas e inventario usan servicios transaccionales para recepción, salidas, ajustes, transferencias y anulaciones.
4. No se debe actualizar el stock editando directamente `Inventario`. Todo cambio de stock debe pasar por servicios con `transaction.atomic()`, `select_for_update()` y movimientos de inventario.
5. Configura `DEBUG=False`, `SECRET_KEY` segura, `ALLOWED_HOSTS`, HTTPS y copias de seguridad antes de publicar.
6. Los importes se guardan como `DecimalField`; no uses `float` para cálculos monetarios.
7. Las referencias comerciales se protegen con `PROTECT` para preservar el historial.


## Servicios transaccionales disponibles
- `apps.compras.services.recibir_compra(...)`: recibe una compra pendiente, valida los lotes y actualiza inventario y movimientos dentro de una transacción.
- `apps.ventas.services.registrar_venta(...)`: registra una venta, valida existencias y distribuye la salida por lotes FEFO dentro de una transacción. Los pagos se registran con `PagoVenta`.
- `apps.inventario.services.ajustar_inventario(...)`, `transferir_stock(...)` y `cambiar_estado_lote(...)`: registran ajustes, transferencias entre almacenes y cambios de cuarentena.
- `python manage.py marcar_lotes_vencidos`: retira del stock y registra movimientos de los lotes cuya fecha ya pasó. Programa este comando una vez al día con el Programador de tareas de Windows o el cron del servidor.

Estos servicios son una base de dominio y deben invocarse desde vistas/formularios validados. Prueba los casos de concurrencia y reglas tributarias antes de producción.
