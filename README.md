# ChocoGest

Sistema Django para gestionar las operaciones de una chocolatería: compras, lotes, inventario, ventas, devoluciones, caja, gastos y reportes.

## Requisitos

- Python 3.10 o superior.
- MySQL 8.x y permisos para crear la base de pruebas.
- Los paquetes indicados en `requirements.txt` (incluye `mysqlclient`, Pillow y openpyxl).

## Instalación local en Windows

Desde PowerShell:

```powershell
cd C:\xampp\htdocs\ChocoGest
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` con la configuración local de MySQL. Crea la base principal:

```sql
CREATE DATABASE chocogest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Aplica las migraciones, crea los roles y datos de ejemplo, y crea el usuario administrador:

```powershell
python manage.py check
python manage.py migrate
python manage.py cargar_datos_iniciales
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. El usuario creado con `createsuperuser` tiene acceso de administrador aunque no tenga un rol asignado. Desde la interfaz de Usuarios se pueden crear usuarios comerciales y asignarles roles.

Las migraciones necesarias ya están versionadas. Ejecuta `makemigrations` solo cuando cambies modelos; revisa y conserva la nueva migración antes de desplegar.

## Configuración de entorno

`.env.example` documenta estas variables:

- `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` de Django.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` para MySQL.
- `DB_TEST_NAME` para la base aislada que Django crea y destruye al correr las pruebas.
- `TIME_ZONE`, por defecto `America/Lima`.

El usuario MySQL de desarrollo debe poder leer y escribir la base principal. Para `manage.py test`, también necesita permisos para crear y borrar `DB_TEST_NAME`. No apuntes `DB_TEST_NAME` a una base con datos que quieras conservar.

## Roles

| Rol | Acceso principal |
| --- | --- |
| Administrador | Todos los módulos, configuración, usuarios, aprobación de devoluciones y reportes. |
| Vendedor | POS y ventas, clientes, consulta de productos e inventario, solicitudes de devolución. |
| Cajero | Caja, movimientos de efectivo, ventas y cobros. |
| Almacenero | Compras y recepción, proveedores, productos, inventario, lotes y ajustes. |

El superusuario de Django también tiene acceso administrativo completo. Las operaciones comerciales se realizan desde las pantallas de la aplicación. Django Admin permite consultar las transacciones, pero no editar ventas, compras, lotes, movimientos de inventario, caja o pagos.

## Flujo de trabajo

1. El administrador configura el negocio, IGV, métodos de pago, almacenes, categorías, marcas, productos y usuarios.
2. El almacenero registra una compra, asigna proveedor y productos, y luego recibe cada línea creando lotes con almacén y vencimiento. La recepción actualiza el inventario y el kardex.
3. El vendedor consulta stock y registra ventas en POS. El servicio consume lotes vigentes por FEFO. Los pagos en efectivo requieren una caja abierta.
4. El cajero abre caja con el fondo inicial, registra ingresos o egresos, y la cierra ingresando el efectivo contado. El sistema calcula el esperado y la diferencia; el resumen se puede imprimir.
5. El vendedor puede solicitar una devolución. Un administrador la aprueba o rechaza. Los reingresos y cuarentenas dejan registro de inventario.
6. El administrador consulta gastos, saldos financieros y reportes de ventas, compras, inventario, lotes y caja. Los reportes se muestran en HTML y se exportan a CSV o Excel.

## Pruebas y comandos

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py cargar_datos_iniciales
python manage.py marcar_lotes_vencidos
```

La prueba de concurrencia usa transacciones y `select_for_update()` de MySQL. Se omite en motores que no implementan bloqueos de fila equivalentes. Las pruebas crean y eliminan la base configurada en `DB_TEST_NAME`.

Programa `marcar_lotes_vencidos` una vez al día con el Programador de tareas de Windows o cron. El comando es idempotente y deja los movimientos de retiro correspondientes.

## Pendiente antes de producción

- Usar `DEBUG=False`, una `SECRET_KEY` aleatoria y privada, y `ALLOWED_HOSTS` con los dominios reales.
- Publicar detrás de HTTPS, activar cookies seguras, configurar el proxy y revisar cabeceras de seguridad.
- Programar backups cifrados de MySQL y archivos subidos; probar periódicamente la restauración.
- Configurar almacenamiento y permisos de los comprobantes y logos, y monitorear errores y disponibilidad.
- La facturación electrónica e integración con SUNAT quedan fuera del alcance de esta versión.
