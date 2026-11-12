(() => {
  const root = document.querySelector(".pos-layout");
  const form = document.getElementById("saleForm");
  if (!root || !form) return;

  const productos = new Map();
  document.querySelectorAll(".add-product").forEach((boton) => {
    productos.set(boton.dataset.id, {
      id: boton.dataset.id,
      nombre: boton.dataset.name,
      codigo: boton.dataset.code,
      precio: escala(boton.dataset.price, 2),
      stock: escala(boton.dataset.stock, 3),
      fefo: boton.dataset.fefo,
    });
  });

  const carrito = new Map();
  const lineas = document.getElementById("cartItems");
  const pagos = document.getElementById("paymentRows");
  const igv = escala(root.dataset.igv || "18", 2);
  const formatoDinero = (centimos) => `S/ ${(centimos / 100).toFixed(2)}`;

  function escala(valor, decimales) {
    const texto = String(valor ?? "0").trim();
    const negativo = texto.startsWith("-");
    const limpio = negativo ? texto.slice(1) : texto;
    const [entero = "0", fraccion = ""] = limpio.split(".");
    const base = 10 ** decimales;
    const fraccionEscalada = (fraccion + "0".repeat(decimales)).slice(0, decimales);
    const resultado = Number(entero || "0") * base + Number(fraccionEscalada || "0");
    return negativo ? -resultado : resultado;
  }

  function decimal(valor, decimales) {
    const base = 10 ** decimales;
    const signo = valor < 0 ? "-" : "";
    const absoluto = Math.abs(valor);
    return `${signo}${Math.floor(absoluto / base)}.${String(absoluto % base).padStart(decimales, "0")}`;
  }

  function redondearMitadArriba(numerador, denominador) {
    return Math.floor((numerador + Math.floor(denominador / 2)) / denominador);
  }

  function agregarProducto(id, cantidad = 1000, descuento = 0) {
    const producto = productos.get(String(id));
    if (!producto || producto.stock <= 0) return;
    const existente = carrito.get(producto.id);
    const siguiente = (existente?.cantidad || 0) + cantidad;
    if (siguiente > producto.stock) return;
    carrito.set(producto.id, {
      ...producto,
      cantidad: siguiente,
      descuento: existente ? existente.descuento : descuento,
    });
    dibujarCarrito();
  }

  function dibujarCarrito() {
    lineas.replaceChildren();
    if (!carrito.size) {
      const vacio = document.createElement("div");
      vacio.className = "cart-empty";
      vacio.innerHTML = "<span>🛍</span><b>Tu carrito está vacío</b><small>Agrega productos del catálogo para comenzar.</small>";
      lineas.append(vacio);
    }

    let subtotal = 0;
    let descuentoLineas = 0;
    carrito.forEach((producto) => {
      const bruto = redondearMitadArriba(producto.precio * producto.cantidad, 1000);
      producto.descuento = Math.max(0, Math.min(producto.descuento, bruto));
      subtotal += bruto;
      descuentoLineas += producto.descuento;

      const fila = document.createElement("article");
      fila.className = "cart-line";
      const arte = document.createElement("span");
      arte.className = "cart-line-art";
      arte.textContent = "🍫";
      const info = document.createElement("div");
      info.className = "cart-line-info";
      const nombre = document.createElement("b");
      nombre.textContent = producto.nombre;
      const codigo = document.createElement("small");
      codigo.textContent = producto.codigo;
      const cantidad = document.createElement("input");
      cantidad.className = "cart-quantity";
      cantidad.type = "number";
      cantidad.min = "0.001";
      cantidad.step = "0.001";
      cantidad.max = decimal(producto.stock, 3);
      cantidad.value = decimal(producto.cantidad, 3);
      cantidad.setAttribute("aria-label", `Cantidad de ${producto.nombre}`);
      cantidad.addEventListener("change", () => {
        const valor = escala(cantidad.value, 3);
        if (valor > 0 && valor <= producto.stock) producto.cantidad = valor;
        dibujarCarrito();
      });
      const descuento = document.createElement("input");
      descuento.className = "cart-line-discount";
      descuento.type = "number";
      descuento.min = "0";
      descuento.step = "0.01";
      descuento.value = decimal(producto.descuento, 2);
      descuento.setAttribute("aria-label", `Descuento de ${producto.nombre}`);
      descuento.addEventListener("change", () => {
        producto.descuento = Math.max(0, escala(descuento.value, 2));
        dibujarCarrito();
      });
      const quitar = document.createElement("button");
      quitar.type = "button";
      quitar.className = "remove-line";
      quitar.textContent = "Quitar";
      quitar.addEventListener("click", () => { carrito.delete(producto.id); dibujarCarrito(); });
      info.append(nombre, codigo, cantidad, descuento, quitar);
      const importe = document.createElement("b");
      importe.className = "cart-line-amount";
      importe.textContent = formatoDinero(bruto - producto.descuento);
      fila.append(arte, info, importe);
      lineas.append(fila);
    });

    const descuentoGlobal = Math.max(0, escala(document.getElementById("discountGlobal").value, 2));
    const descuentoTotal = descuentoLineas + descuentoGlobal;
    const base = Math.max(0, subtotal - descuentoTotal);
    const impuesto = redondearMitadArriba(base * igv, 10000);
    const total = base + impuesto;
    document.getElementById("cartSubtotal").textContent = formatoDinero(subtotal);
    document.getElementById("cartDiscount").textContent = formatoDinero(descuentoTotal);
    document.getElementById("cartTax").textContent = formatoDinero(impuesto);
    document.getElementById("cartTotal").textContent = formatoDinero(total);
    document.getElementById("checkoutButton").disabled = !carrito.size;
    document.getElementById("pendingButton").disabled = !carrito.size;
    form.dataset.totalCentimos = String(total);
  }

  function pagosDesdeFormulario() {
    const items = [];
    let suma = 0;
    for (const fila of pagos.querySelectorAll(".payment-entry")) {
      const metodo = fila.querySelector(".payment-method").value;
      const montoTexto = fila.querySelector(".payment-amount").value.trim();
      const referencia = fila.querySelector(".payment-reference").value.trim();
      if (!metodo && !montoTexto && !referencia) continue;
      if (!metodo || !montoTexto) throw new Error("Completa el método y el monto de cada pago.");
      const monto = escala(montoTexto, 2);
      if (monto <= 0) throw new Error("Cada pago debe ser mayor a cero.");
      items.push({ metodo_pago_id: metodo, monto: decimal(monto, 2), referencia });
      suma += monto;
      const textoMetodo = fila.querySelector(".payment-method option:checked").dataset.nombre || "";
      if (textoMetodo === "efectivo" && form.dataset.cajaAbierta !== "1") {
        throw new Error("Para cobrar en efectivo primero debe abrirse una caja.");
      }
    }
    if (suma > Number(form.dataset.totalCentimos || 0)) {
      throw new Error("La suma de pagos supera el total de la venta.");
    }
    return items;
  }

  document.getElementById("productSearch").addEventListener("input", (evento) => {
    const busqueda = evento.target.value.trim().toLocaleLowerCase("es");
    document.querySelectorAll(".product-card").forEach((tarjeta) => {
      const coincide = `${tarjeta.dataset.name} ${tarjeta.dataset.code} ${tarjeta.dataset.barcode}`.includes(busqueda);
      tarjeta.hidden = !coincide || (document.getElementById("categoryFilter").value && tarjeta.dataset.category !== document.getElementById("categoryFilter").value);
    });
  });
  document.getElementById("productSearch").addEventListener("keydown", (evento) => {
    if (evento.key !== "Enter") return;
    evento.preventDefault();
    const busqueda = evento.currentTarget.value.trim().toLocaleLowerCase("es");
    const exacto = [...document.querySelectorAll(".add-product")].find((boton) => {
      const tarjeta = boton.closest(".product-card");
      return boton.dataset.code.toLocaleLowerCase("es") === busqueda || tarjeta.dataset.barcode === busqueda;
    });
    if (exacto && !exacto.disabled) agregarProducto(exacto.dataset.id);
  });
  document.getElementById("categoryFilter").addEventListener("change", () => {
    document.getElementById("productSearch").dispatchEvent(new Event("input"));
  });
  document.getElementById("productGrid").addEventListener("click", (evento) => {
    const boton = evento.target.closest(".add-product");
    if (boton && !boton.disabled) agregarProducto(boton.dataset.id);
  });
  document.getElementById("discountGlobal").addEventListener("input", dibujarCarrito);
  document.getElementById("addPayment").addEventListener("click", () => {
    pagos.append(document.getElementById("paymentTemplate").content.cloneNode(true));
  });
  pagos.addEventListener("click", (evento) => {
    if (!evento.target.classList.contains("remove-payment")) return;
    if (pagos.querySelectorAll(".payment-entry").length > 1) evento.target.closest(".payment-entry").remove();
    else evento.target.closest(".payment-entry").querySelectorAll("input").forEach((campo) => { campo.value = ""; });
  });
  form.addEventListener("submit", (evento) => {
    try {
      const pagosCapturados = evento.submitter?.value === "PENDIENTE" ? [] : pagosDesdeFormulario();
      if (evento.submitter?.value !== "PENDIENTE" && !pagosCapturados.length) {
        throw new Error("Agrega un pago o elige registrar la venta como pendiente.");
      }
      document.getElementById("cartPayload").value = JSON.stringify([...carrito.values()].map((item) => ({
        producto_id: item.id,
        cantidad: decimal(item.cantidad, 3),
        precio_unitario: decimal(item.precio, 2),
        descuento: decimal(item.descuento, 2),
      })));
      document.getElementById("paymentsPayload").value = JSON.stringify(pagosCapturados);
    } catch (error) {
      evento.preventDefault();
      window.alert(error.message);
    }
  });

  try {
    const carritoInicial = JSON.parse(document.getElementById("cartPayload").value || "[]");
    carritoInicial.forEach((linea) => agregarProducto(linea.producto_id, escala(linea.cantidad, 3), escala(linea.descuento || "0", 2)));
    const pagosIniciales = JSON.parse(document.getElementById("paymentsPayload").value || "[]");
    pagosIniciales.forEach((pago, indice) => {
      const fila = indice === 0 ? pagos.querySelector(".payment-entry") : document.getElementById("paymentTemplate").content.cloneNode(true).firstElementChild;
      fila.querySelector(".payment-method").value = pago.metodo_pago_id;
      fila.querySelector(".payment-amount").value = pago.monto;
      fila.querySelector(".payment-reference").value = pago.referencia || "";
      if (indice > 0) pagos.append(fila);
    });
  } catch (_error) { /* Se inicia vacío si el carrito previo tenía datos inválidos. */ }
  dibujarCarrito();
})();
