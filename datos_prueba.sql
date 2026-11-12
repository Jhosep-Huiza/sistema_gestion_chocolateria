-- Datos de demostración para ChocoGest.
-- Ejecutar DESPUÉS de `python manage.py migrate` en una base de desarrollo vacía.
-- Está pensado para una base de desarrollo vacía; usa identificadores fijos.
-- Acceso de demostración: usuario `demo.admin`, contraseña `demo12345`.
-- Cambia esa contraseña o elimina estas cuentas antes de cualquier uso real.

SET NAMES utf8mb4;
START TRANSACTION;

INSERT INTO roles (id, nombre, descripcion, estado) VALUES
(1,'Administrador','Acceso completo al sistema',1),(2,'Vendedor','Ventas y clientes',1),
(3,'Cajero','Caja y cobros',1),(4,'Almacenero','Compras e inventario',1);

-- Hash PBKDF2 de Django para demo12345.
INSERT INTO usuarios (id,password,last_login,is_superuser,username,first_name,last_name,email,is_staff,is_active,date_joined,nombres,apellidos,telefono,rol_id) VALUES
(1,'pbkdf2_sha256$1000000$Mgscejjhv7XBELPGJNdRWD$A9tyvfxJ2CnpUjekeZVQcCWYUL3uMwB7VZAxAnhosBo=',NULL,1,'demo.admin','Ana','Demo','admin.demo@chocogest.local',1,1,'2026-11-11 09:00:00','Ana','Demo','999111111',1),
(2,'!',NULL,0,'demo.vendedor','Luis','Prueba','vendedor.demo@chocogest.local',0,1,'2026-11-11 09:00:00','Luis','Prueba','999222222',2),
(3,'!',NULL,0,'demo.cajero','Rosa','Muestra','cajero.demo@chocogest.local',0,1,'2026-11-11 09:00:00','Rosa','Muestra','999333333',3),
(4,'!',NULL,0,'demo.almacen','Marco','Ejemplo','almacen.demo@chocogest.local',0,1,'2026-11-11 09:00:00','Marco','Ejemplo','999444444',4);

INSERT INTO clientes (id,tipo_documento,numero_documento,nombres,telefono,email,direccion,fecha_registro,estado) VALUES
(1,'DNI','70000001','Cliente General','','','',NOW(),1),
(2,'DNI','70000002','María Chocolate','987111222','maria@example.local','Miraflores, Lima',NOW(),1),
(3,'RUC','20600000001','Cafetería Cacao SAC','014441122','compras@cacao.example.local','Surco, Lima',NOW(),1);

INSERT INTO categorias (id,nombre,descripcion,imagen,estado) VALUES
(1,'Tabletas','Barras y tabletas artesanales','',1),(2,'Bombones','Bombones rellenos','',1),(3,'Trufas','Trufas de cacao','',1),(4,'Regalos','Cajas para regalo','',1);
INSERT INTO marcas (id,nombre,descripcion,estado) VALUES
(1,'ChocoGest Artesanal','Producción propia',1),(2,'Cacao del Valle','Cacao peruano',1);
INSERT INTO productos (id,categoria_id,marca_id,codigo,codigo_barras,nombre,descripcion,peso_gramos,precio_compra_referencial,precio_venta,stock_minimo,imagen,estado,created_at,updated_at) VALUES
(1,1,1,'CHOCO-70','7750000000011','Tableta 70% cacao','Chocolate bitter de origen peruano',100.000,4.50,12.00,5.000,'',1,NOW(),NOW()),
(2,2,1,'BOMB-CLAS','7750000000028','Bombones surtidos','Caja de bombones surtidos',250.000,9.00,24.00,3.000,'',1,NOW(),NOW()),
(3,3,2,'TRUF-CAC','7750000000035','Trufas de cacao','Trufas espolvoreadas con cacao',180.000,6.50,18.00,4.000,'',1,NOW(),NOW()),
(4,4,2,'REG-BOX','7750000000042','Caja regalo cacao','Selección de chocolates para regalo',400.000,18.00,45.00,2.000,'',1,NOW(),NOW());

INSERT INTO proveedores (id,ruc,razon_social,contacto,telefono,email,direccion,estado) VALUES
(1,'20600000011','Cacao Andino SAC','Elena Rojas','014441100','ventas@cacaoandino.example.local','Lima',1),
(2,'20600000022','Empaques Dulces EIRL','Pedro León','014442200','pedidos@empaques.example.local','Callao',1);
INSERT INTO metodos_pago (id,nombre,descripcion,estado) VALUES
(1,'Efectivo','Pago en efectivo',1),(2,'Yape','Billetera digital Yape',1),(3,'Plin','Billetera digital Plin',1),
(4,'Tarjeta','Tarjeta de crédito o débito',1),(5,'Transferencia bancaria','Transferencia bancaria',1);
INSERT INTO configuracion (id,nombre_negocio,ruc,direccion,telefono,email,logo,porcentaje_igv,moneda,updated_at) VALUES
(1,'ChocoGest Demo','20612345678','Av. del Cacao 123, Lima','014440000','hola@chocogest.local','',18.00,'PEN',NOW());
INSERT INTO almacenes (id,nombre,ubicacion,descripcion,estado) VALUES
(1,'Almacén principal','Lima','Almacén de demostración',1),(2,'Vitrina de tienda','Tienda','Punto de venta',1);

INSERT INTO compras (id,proveedor_id,usuario_id,numero_compra,tipo_documento,numero_documento,fecha_compra,subtotal,descuento,igv,total,estado,observaciones) VALUES
(1,1,4,'COMP-DEMO-0001','FACTURA','F001-0000123','2026-11-01 10:00:00',200.00,0.00,36.00,236.00,'RECIBIDA','Compra inicial para pruebas');
INSERT INTO detalle_compras (id,compra_id,producto_id,cantidad,precio_unitario,descuento,subtotal) VALUES
(1,1,1,20.000,4.50,0.00,90.00),(2,1,2,10.000,9.00,0.00,90.00),(3,1,3,2.000,10.00,0.00,20.00);
INSERT INTO lotes (id,detalle_compra_id,producto_id,almacen_id,codigo_lote,fecha_fabricacion,fecha_vencimiento,cantidad_recibida,cantidad_disponible,estado) VALUES
(1,1,1,1,'LOT-CHOCO-001','2026-10-01','2027-10-01',20.000,18.000,'DISPONIBLE'),
(2,2,2,1,'LOT-BOMB-001','2026-10-15','2027-04-15',10.000,9.000,'DISPONIBLE'),
(3,3,3,1,'LOT-TRUF-001','2026-10-20','2027-02-20',2.000,1.000,'DISPONIBLE');
INSERT INTO inventario (id,producto_id,almacen_id,stock_actual,stock_reservado,updated_at) VALUES
(1,1,1,18.000,0.000,NOW()),(2,2,1,9.000,0.000,NOW()),(3,3,1,1.000,0.000,NOW());
INSERT INTO pagos_compras (id,compra_id,metodo_pago_id,usuario_id,monto,fecha_pago,referencia,estado) VALUES
(1,1,5,4,236.00,'2026-11-01 10:30:00','TRF-DEMO-001','CONFIRMADO');
INSERT INTO movimientos_inventario (id,producto_id,almacen_id,lote_id,usuario_id,tipo_movimiento,cantidad,motivo,referencia_tipo,referencia_id,fecha) VALUES
(1,1,1,1,4,'ENTRADA',20.000,'Recepción de compra','COMPRA',1,'2026-11-01 10:15:00'),
(2,2,1,2,4,'ENTRADA',10.000,'Recepción de compra','COMPRA',1,'2026-11-01 10:15:00'),
(3,3,1,3,4,'ENTRADA',2.000,'Recepción de compra','COMPRA',1,'2026-11-01 10:15:00');

INSERT INTO cajas (id,usuario_id,fecha_apertura,fecha_cierre,monto_inicial,monto_final,monto_esperado,diferencia,estado) VALUES
(1,3,'2026-11-11 08:00:00',NULL,100.00,NULL,NULL,NULL,'ABIERTA');
INSERT INTO ventas (id,cliente_id,usuario_id,caja_id,numero_venta,tipo_comprobante,numero_comprobante,fecha_venta,subtotal,descuento,igv,total,estado,observaciones) VALUES
(1,2,2,1,'VTA-DEMO-0001','BOLETA','B001-000001','2026-11-11 09:15:00',36.00,0.00,6.48,42.48,'PAGADA','Venta de prueba'),
(2,3,2,1,'VTA-DEMO-0002','TICKET','T001-000002','2026-11-11 10:00:00',24.00,0.00,4.32,28.32,'PARCIAL','Venta con saldo pendiente');
INSERT INTO detalle_ventas (id,venta_id,producto_id,lote_id,cantidad,precio_unitario,descuento,subtotal,cantidad_reservada) VALUES
(1,1,1,1,1.000,12.00,0.00,12.00,0.000),(2,1,2,2,1.000,24.00,0.00,24.00,0.000),
(3,2,2,2,1.000,24.00,0.00,24.00,0.000);
INSERT INTO pagos_ventas (id,venta_id,metodo_pago_id,usuario_id,monto,fecha_pago,referencia,estado) VALUES
(1,1,1,3,42.48,'2026-11-11 09:16:00','','CONFIRMADO'),(2,2,2,3,10.00,'2026-11-11 10:01:00','YAPE-DEMO-002','CONFIRMADO');
INSERT INTO movimientos_caja (id,caja_id,usuario_id,tipo,concepto,monto,fecha,referencia_tipo,referencia_id) VALUES
(1,1,3,'INGRESO','Cobro venta VTA-DEMO-0001',42.48,'2026-11-11 09:16:00','VENTA',1),
(2,1,3,'INGRESO','Pago parcial venta VTA-DEMO-0002',10.00,'2026-11-11 10:01:00','VENTA',2);
INSERT INTO movimientos_inventario (id,producto_id,almacen_id,lote_id,usuario_id,tipo_movimiento,cantidad,motivo,referencia_tipo,referencia_id,fecha) VALUES
(4,1,1,1,2,'SALIDA',1.000,'Venta','VENTA',1,'2026-11-11 09:15:00'),
(5,2,1,2,2,'SALIDA',2.000,'Ventas','VENTA',1,'2026-11-11 10:00:00');
UPDATE lotes SET cantidad_disponible=17.000 WHERE id=1;
UPDATE lotes SET cantidad_disponible=7.000 WHERE id=2;
UPDATE inventario SET stock_actual=17.000 WHERE id=1;
UPDATE inventario SET stock_actual=7.000 WHERE id=2;

INSERT INTO devoluciones (id,venta_id,usuario_id,fecha_devolucion,motivo,tipo_reembolso,reembolso_efectivo,total_devolucion,estado) VALUES
(1,1,2,'2026-11-11 11:00:00','Empaque dañado durante el traslado','REEMBOLSO',0,12.00,'PENDIENTE');
INSERT INTO detalle_devoluciones (id,devolucion_id,detalle_venta_id,cantidad,motivo,estado_producto) VALUES
(1,1,1,1.000,'Producto cerrado, revisar empaque','CUARENTENA');
INSERT INTO gastos (id,usuario_id,caja_id,categoria,descripcion,monto,es_efectivo,fecha_gasto,comprobante,estado) VALUES
(1,3,1,'Movilidad','Traslado de insumos',8.50,1,'2026-11-11 10:30:00','','REGISTRADO');
INSERT INTO auditoria (id,usuario_id,accion,tabla_afectada,registro_id,descripcion,direccion_ip,fecha) VALUES
(1,1,'INSERT','productos',1,'Carga de datos de demostración','127.0.0.1','2026-11-11 08:00:00');
INSERT INTO secuencia_ventas (id,ultimo_numero) VALUES (1,2);

COMMIT;
