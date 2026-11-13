"use strict";

/*
 * Dashboard financiero — cliente del API GraphQL del Sistema General de Ingresos.
 *
 * - El backend es la única fuente de cálculo: aquí no se suma ni se resta nada,
 *   solo se da formato a los valores que devuelve generalBalance.
 * - El token vive en sessionStorage (se borra al cerrar la pestaña o la sesión).
 * - La empresa sale del token; el cliente nunca envía companyId ni actorCompanyUserId.
 */

// Servido por el propio API (http://127.0.0.1:8000/dashboard/) se usa el mismo origen.
// Abierto desde otro puerto (Live Server, etc.) se apunta al API local; requiere CORS.
const API_URL =
  location.protocol.startsWith("http") && location.pathname.startsWith("/dashboard")
    ? "/graphql"
    : "http://127.0.0.1:8000/graphql";

const CLAVE_TOKEN = "sgi.token";
const CLAVE_USUARIO = "sgi.usuario";
const CLAVE_EMPRESA = "sgi.empresa";
const CLAVE_PERIODO = "sgi.periodo";

const MUTATION_LOGIN = `
  mutation IniciarSesion($input: LoginInput!) {
    login(input: $input) {
      token
      tokenType
      user { name email }
    }
  }`;

const QUERY_INDICADORES = `
  query IndicadoresEmpresa($from: Date!, $to: Date!) {
    generalBalance(fromDate: $from, toDate: $to) {
      companyId
      currency
      fromDate
      toDate
      openingBalance
      totalIncome
      totalExpense
      profit
      closingBalance
      isInRed
      accountsInRed
      accounts {
        accountId
        accountName
        isActive
        openingBalance
        totalIncome
        totalExpense
        profit
        closingBalance
        isInRed
      }
    }
  }`;

const QUERY_EMPRESA = `
  query NombreEmpresa($id: ID!) {
    company(id: $id) { id name }
  }`;

// Mensajes del backend (app/access.py) que significan "la sesión ya no sirve".
const ERRORES_DE_SESION = [
  "Falta el token",
  "El token no es válido",
  "La membresía del token no existe o está inactiva",
];
// Mensajes que significan "hay sesión, pero el rol no puede leer balances".
const ERRORES_DE_PERMISO = ["El rol no tiene el permiso", "La membresía no tiene un rol activo"];

const $ = (id) => document.getElementById(id);

let consultaActual = 0; // descarta respuestas de consultas viejas

// ---------------------------------------------------------------------------
// Sesión
// ---------------------------------------------------------------------------

function leerSesion(clave) {
  try {
    return sessionStorage.getItem(clave);
  } catch {
    return null;
  }
}

function guardarSesion(clave, valor) {
  try {
    sessionStorage.setItem(clave, valor);
  } catch {
    /* sin almacenamiento: la sesión dura lo que dure la página */
  }
}

function borrarSesion() {
  for (const clave of [CLAVE_TOKEN, CLAVE_USUARIO, CLAVE_EMPRESA, CLAVE_PERIODO]) {
    try {
      sessionStorage.removeItem(clave);
    } catch {
      /* nada que borrar */
    }
  }
}

// ---------------------------------------------------------------------------
// Peticiones GraphQL
// ---------------------------------------------------------------------------

async function gql(query, variables, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let respuesta;
  try {
    respuesta = await fetch(API_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({ query, variables }),
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el API. Verifica que el backend esté levantado en el puerto 8000."
    );
  }

  let cuerpo;
  try {
    cuerpo = await respuesta.json();
  } catch {
    throw new Error(`El API respondió algo inesperado (HTTP ${respuesta.status}).`);
  }
  return cuerpo;
}

function primerError(cuerpo) {
  const errores = cuerpo && cuerpo.errors;
  return errores && errores.length ? String(errores[0].message || "Error desconocido.") : null;
}

// ---------------------------------------------------------------------------
// Formato (sin float: los importes llegan como texto "1800.00" y así se tratan)
// ---------------------------------------------------------------------------

function formatoImporte(valor) {
  const texto = String(valor).trim();
  const partes = /^(-?)(\d+)(?:\.(\d+))?$/.exec(texto);
  if (!partes) return texto;
  const enteros = partes[2].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const decimales = (partes[3] || "").padEnd(2, "0").slice(0, 2);
  return `${partes[1]}${enteros}.${decimales}`;
}

function esCero(valor) {
  return /^-?0*(\.0*)?$/.test(String(valor).trim());
}

function esNegativo(valor) {
  return String(valor).trim().startsWith("-") && !esCero(valor);
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function formatoFecha(iso) {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso));
  if (!partes) return String(iso);
  return `${Number(partes[3])} ${MESES[Number(partes[2]) - 1]} ${partes[1]}`;
}

function fechaLocalISO(fecha) {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

// ---------------------------------------------------------------------------
// Vistas
// ---------------------------------------------------------------------------

function mostrarAviso(elemento, mensaje) {
  elemento.textContent = mensaje || "";
  elemento.hidden = !mensaje;
}

function mostrarLogin(mensaje) {
  $("vista-dashboard").hidden = true;
  $("vista-login").hidden = false;
  $("login-password").value = "";
  mostrarAviso($("login-aviso"), mensaje);
  $("login-email").focus();
}

function mostrarDashboard() {
  $("vista-login").hidden = true;
  $("vista-dashboard").hidden = false;

  let usuario = null;
  try {
    usuario = JSON.parse(leerSesion(CLAVE_USUARIO) || "null");
  } catch {
    usuario = null;
  }
  $("usuario-nombre").textContent = usuario && usuario.name ? usuario.name : "";

  let periodo = null;
  try {
    periodo = JSON.parse(leerSesion(CLAVE_PERIODO) || "null");
  } catch {
    periodo = null;
  }
  const hoy = new Date();
  // Por defecto: del día 1 del mes en curso a hoy.
  $("fecha-desde").value =
    (periodo && periodo.from) || fechaLocalISO(new Date(hoy.getFullYear(), hoy.getMonth(), 1));
  $("fecha-hasta").value = (periodo && periodo.to) || fechaLocalISO(hoy);

  consultarIndicadores();
}

function cerrarSesion(mensaje) {
  consultaActual += 1; // cualquier respuesta pendiente se ignora
  borrarSesion();
  limpiarResultados();
  $("empresa-nombre").textContent = "Empresa";
  mostrarAviso($("dash-aviso"), "");
  mostrarLogin(mensaje);
}

function limpiarResultados() {
  $("resultados").hidden = true;
  $("resultados").classList.remove("cargando");
  $("tabla-cuentas").replaceChildren();
  $("periodo-consultado").textContent = "Período: sin consultar";
}

function ponerCargando(activo) {
  $("estado-carga").hidden = !activo;
  $("btn-actualizar").disabled = activo;
  $("resultados").classList.toggle("cargando", activo);
}

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------

async function iniciarSesion(evento) {
  evento.preventDefault();
  const email = $("login-email").value.trim();
  const password = $("login-password").value;

  if (!email || !password) {
    mostrarAviso($("login-aviso"), "Escribe tu correo electrónico y tu contraseña.");
    return;
  }

  const boton = $("btn-entrar");
  boton.disabled = true;
  boton.textContent = "Entrando…";
  mostrarAviso($("login-aviso"), "");

  try {
    const cuerpo = await gql(MUTATION_LOGIN, { input: { email, password } });
    const error = primerError(cuerpo);
    const login = cuerpo.data && cuerpo.data.login;
    if (error || !login || !login.token) {
      mostrarAviso($("login-aviso"), error || "No se pudo iniciar sesión.");
      return;
    }
    guardarSesion(CLAVE_TOKEN, login.token);
    guardarSesion(CLAVE_USUARIO, JSON.stringify({ name: login.user.name, email: login.user.email }));
    $("login-password").value = "";
    mostrarDashboard();
  } catch (fallo) {
    mostrarAviso($("login-aviso"), fallo.message);
  } finally {
    boton.disabled = false;
    boton.textContent = "Entrar";
  }
}

// ---------------------------------------------------------------------------
// Indicadores
// ---------------------------------------------------------------------------

async function consultarIndicadores(evento) {
  if (evento) evento.preventDefault();

  const token = leerSesion(CLAVE_TOKEN);
  if (!token) {
    cerrarSesion("Inicia sesión para ver el dashboard.");
    return;
  }

  const from = $("fecha-desde").value;
  const to = $("fecha-hasta").value;

  // Fechas inválidas: no se llama al API y no se dejan números del período anterior.
  if (!from || !to) {
    limpiarResultados();
    mostrarAviso($("dash-aviso"), "Elige las dos fechas del período (Desde y Hasta).");
    return;
  }
  if (from > to) {
    limpiarResultados();
    mostrarAviso(
      $("dash-aviso"),
      'La fecha "Desde" no puede ser posterior a la fecha "Hasta". Corrige el período.'
    );
    return;
  }

  const miConsulta = ++consultaActual;
  mostrarAviso($("dash-aviso"), "");
  ponerCargando(true);

  try {
    const cuerpo = await gql(QUERY_INDICADORES, { from, to }, token);
    if (miConsulta !== consultaActual) return; // llegó tarde: ya hay otra consulta

    const error = primerError(cuerpo);
    if (error) {
      if (ERRORES_DE_SESION.some((m) => error.startsWith(m))) {
        cerrarSesion("Tu sesión expiró o el token no es válido. Inicia sesión de nuevo.");
        return;
      }
      limpiarResultados();
      if (ERRORES_DE_PERMISO.some((m) => error.startsWith(m))) {
        mostrarAviso(
          $("dash-aviso"),
          `Acceso denegado: tu rol no tiene permiso de lectura para ver los balances. (${error})`
        );
      } else {
        mostrarAviso($("dash-aviso"), `No se pudieron consultar los indicadores: ${error}`);
      }
      return;
    }

    const balance = cuerpo.data && cuerpo.data.generalBalance;
    if (!balance) {
      limpiarResultados();
      mostrarAviso($("dash-aviso"), "El API no devolvió el balance general.");
      return;
    }

    guardarSesion(CLAVE_PERIODO, JSON.stringify({ from, to }));
    pintarBalance(balance);
    cargarNombreEmpresa(balance.companyId, token);
  } catch (fallo) {
    if (miConsulta !== consultaActual) return;
    limpiarResultados();
    mostrarAviso($("dash-aviso"), fallo.message);
  } finally {
    if (miConsulta === consultaActual) ponerCargando(false);
  }
}

function ponerImporte(elemento, valor, moneda) {
  const unidad = document.createElement("small");
  unidad.textContent = moneda;
  elemento.replaceChildren(formatoImporte(valor), unidad);
}

function pintarBalance(balance) {
  const moneda = balance.currency;

  // El período mostrado sale de la respuesta, no de los campos de fecha.
  $("periodo-consultado").textContent =
    `Período: ${formatoFecha(balance.fromDate)} – ${formatoFecha(balance.toDate)}`;
  $("moneda").textContent = moneda;

  ponerImporte($("kpi-inicial"), balance.openingBalance, moneda);
  ponerImporte($("kpi-ingresos"), balance.totalIncome, moneda);
  ponerImporte($("kpi-egresos"), balance.totalExpense, moneda);
  ponerImporte($("kpi-profit"), balance.profit, moneda);
  ponerImporte($("kpi-final"), balance.closingBalance, moneda);

  $("kpi-profit").classList.toggle("profit-negativo", esNegativo(balance.profit));
  $("tarjeta-final").classList.toggle("en-rojo", balance.isInRed);

  $("sin-movimientos").hidden = !(esCero(balance.totalIncome) && esCero(balance.totalExpense));

  // Estado de riesgo: isInRed y accountsInRed tal como los manda el backend.
  $("riesgo-general").classList.toggle("alerta", balance.isInRed);
  $("riesgo-general-valor").textContent = balance.isInRed ? "Sí" : "No";

  const enRojo = balance.accounts.filter((cuenta) => cuenta.isInRed);
  $("riesgo-cuentas").classList.toggle("alerta", balance.accountsInRed > 0);
  $("riesgo-cuentas-valor").textContent = String(balance.accountsInRed);
  $("riesgo-cuentas-nombres").textContent = enRojo.length
    ? `(${enRojo.map((cuenta) => cuenta.accountName).join(", ")})`
    : "";

  // Detalle por cuenta.
  const hayCuentas = balance.accounts.length > 0;
  $("sin-cuentas").hidden = hayCuentas;
  $("tabla-contenedor").hidden = !hayCuentas;
  $("tabla-cuentas").replaceChildren(...balance.accounts.map(filaCuenta));

  $("resultados").hidden = false;
}

function filaCuenta(cuenta) {
  const fila = document.createElement("tr");

  const nombre = document.createElement("th");
  nombre.scope = "row";
  nombre.textContent = cuenta.accountName;
  if (!cuenta.isActive) nombre.append(etiqueta("Inactiva", "etiqueta-inactiva"));
  if (cuenta.isInRed) nombre.append(etiqueta("En rojo", "etiqueta-rojo"));
  fila.append(nombre);

  fila.append(celdaImporte(cuenta.openingBalance));
  fila.append(celdaImporte(cuenta.totalIncome));
  fila.append(celdaImporte(cuenta.totalExpense));

  const profit = celdaImporte(cuenta.profit);
  if (esNegativo(cuenta.profit)) profit.classList.add("profit-negativo");
  fila.append(profit);

  const final = celdaImporte(cuenta.closingBalance);
  if (cuenta.isInRed) {
    const marca = document.createElement("span");
    marca.className = "saldo-rojo";
    marca.textContent = final.textContent;
    final.replaceChildren(marca);
  }
  fila.append(final);

  return fila;
}

function celdaImporte(valor) {
  const celda = document.createElement("td");
  celda.className = "num";
  celda.textContent = formatoImporte(valor);
  return celda;
}

function etiqueta(texto, clase) {
  const marca = document.createElement("span");
  marca.className = `etiqueta ${clase}`;
  marca.textContent = texto;
  return marca;
}

// El nombre de la empresa se pide una vez por sesión, con el companyId que
// devolvió el propio balance (es decir, el del token).
async function cargarNombreEmpresa(companyId, token) {
  let guardada = null;
  try {
    guardada = JSON.parse(leerSesion(CLAVE_EMPRESA) || "null");
  } catch {
    guardada = null;
  }
  if (guardada && guardada.id === companyId) {
    $("empresa-nombre").textContent = guardada.name;
    return;
  }

  $("empresa-nombre").textContent = `Empresa #${companyId}`;
  try {
    const cuerpo = await gql(QUERY_EMPRESA, { id: companyId }, token);
    const empresa = cuerpo.data && cuerpo.data.company;
    if (empresa && empresa.name && leerSesion(CLAVE_TOKEN) === token) {
      guardarSesion(CLAVE_EMPRESA, JSON.stringify({ id: companyId, name: empresa.name }));
      $("empresa-nombre").textContent = empresa.name;
    }
  } catch {
    /* se queda el identificador visible "Empresa #id" */
  }
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

$("form-login").addEventListener("submit", iniciarSesion);
$("form-periodo").addEventListener("submit", consultarIndicadores);
$("fecha-desde").addEventListener("change", () => consultarIndicadores());
$("fecha-hasta").addEventListener("change", () => consultarIndicadores());
$("btn-salir").addEventListener("click", () => cerrarSesion(""));

$("btn-ver-password").addEventListener("click", () => {
  const campo = $("login-password");
  const visible = campo.type === "text";
  campo.type = visible ? "password" : "text";
  $("btn-ver-password").textContent = visible ? "Ver" : "Ocultar";
  $("btn-ver-password").setAttribute("aria-pressed", String(!visible));
});

if (leerSesion(CLAVE_TOKEN)) {
  mostrarDashboard();
} else {
  mostrarLogin("");
}
