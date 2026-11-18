"use strict";

/*
 * Sistema General de Ingresos — cliente del API GraphQL.
 *
 * Una sola aplicación con dos dashboards:
 *   - Financiero (Unidad III, actividad 1): período, indicadores y saldo por cuenta.
 *   - Administrativo (Unidad III, actividad 2): usuarios, cuentas y conceptos.
 *
 * Reglas:
 * - El backend es la única fuente de verdad. Cada tabla es una query, cada Guardar
 *   es una mutation y, después de guardar, la tabla se vuelve a consultar.
 * - El token vive en sessionStorage (se borra al cerrar la pestaña o la sesión).
 * - La empresa, el rol y los permisos salen de `myAccess`, que el API calcula con el
 *   token. El cliente no inventa la empresa ni el rol: el companyId que manda a las
 *   consultas es el que devolvió el propio API.
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

// ---------------------------------------------------------------------------
// Operaciones GraphQL
// ---------------------------------------------------------------------------

const MUTATION_LOGIN = `
  mutation IniciarSesion($input: LoginInput!) {
    login(input: $input) {
      token
      tokenType
      user { name email }
    }
  }`;

const QUERY_ACCESO = `
  query MiAcceso {
    myAccess {
      companyUserId
      companyId
      companyName
      userName
      isAdmin
      role { code name }
      permissions
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

const QUERY_USUARIOS = `
  query UsuariosEmpresa($companyId: ID!) {
    companyUsers(companyId: $companyId) {
      id
      isAdmin
      isActive
      role { code name }
      user { name email }
    }
  }`;

const MUTATION_CREAR_USUARIO = `
  mutation NuevoUsuario($input: CreateCompanyUserInput!) {
    createCompanyUser(input: $input) {
      id
      isAdmin
      isActive
      role { code name }
      user { name email }
    }
  }`;

const MUTATION_DESACTIVAR_USUARIO = `
  mutation DesactivarUsuario($id: ID!) {
    deactivateCompanyUser(id: $id) { id isActive user { name } }
  }`;

const QUERY_CUENTAS = `
  query CuentasEmpresa($companyId: ID!) {
    accounts(companyId: $companyId) {
      id
      name
      accountType
      bankName
      clabe
      cardLastDigits
      isActive
    }
  }`;

const MUTATION_CREAR_CUENTA = `
  mutation NuevaCuenta($input: CreateAccountInput!) {
    createAccount(input: $input) { id name accountType isActive }
  }`;

const QUERY_CONCEPTOS = `
  query ConceptosEmpresa($companyId: ID!) {
    concepts(companyId: $companyId) {
      id
      name
      conceptType
      isActive
    }
  }`;

const MUTATION_CREAR_CONCEPTO = `
  mutation NuevoConcepto($input: CreateConceptInput!) {
    createConcept(input: $input) { id name conceptType isActive }
  }`;

const QUERY_CONCEPTOS_CUENTA = `
  query ConceptosDeCuenta($accountId: ID!) {
    accountConcepts(accountId: $accountId) {
      id
      isActive
      concept { id name conceptType }
    }
  }`;

const MUTATION_ASIGNAR = `
  mutation AsignarConcepto($input: AssignConceptToAccountInput!) {
    assignConceptToAccount(input: $input) { id isActive concept { name } }
  }`;

const MUTATION_QUITAR = `
  mutation QuitarConcepto($accountId: ID!, $conceptId: ID!) {
    removeConceptFromAccount(accountId: $accountId, conceptId: $conceptId)
  }`;

// Mensajes del backend (app/access.py) que significan "la sesión ya no sirve".
const ERRORES_DE_SESION = [
  "Falta el token",
  "El token no es válido",
  "La membresía del token no existe o está inactiva",
];
// Mensajes que significan "hay sesión, pero el rol no puede hacer esto".
const ERRORES_DE_PERMISO = ["El rol no tiene el permiso", "La membresía no tiene un rol activo"];

// Catálogos del Parcial I: valor del API -> etiqueta en pantalla.
const TIPOS_CUENTA = [
  ["CASH", "Efectivo"],
  ["DEBIT", "Débito"],
  ["CREDIT", "Crédito"],
  ["SAVINGS", "Ahorro"],
  ["INVESTMENT", "Inversión"],
  ["WALLET", "Monedero"],
  ["OTHER", "Otro"],
];
const ETIQUETA_CUENTA = Object.fromEntries(TIPOS_CUENTA);
const ETIQUETA_CONCEPTO = { INCOME: "Ingreso", EXPENSE: "Egreso" };

const SECCIONES = {
  financiero: { titulo: "Dashboard financiero", cargar: () => consultarIndicadores() },
  usuarios: { titulo: "Dashboard administrativo", cargar: () => cargarUsuarios() },
  cuentas: { titulo: "Dashboard administrativo", cargar: () => cargarCuentas() },
  conceptos: { titulo: "Dashboard administrativo", cargar: () => cargarConceptos() },
};

const $ = (id) => document.getElementById(id);

let consultaActual = 0; // descarta respuestas de consultas viejas del financiero
let acceso = null; // resultado de myAccess
const estado = {
  usuarios: [],
  cuentas: [],
  conceptos: [],
  filtroCuenta: "",
  filtroConcepto: "",
  cuentaElegida: "",
};

class SesionTerminada extends Error {}

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

function puede(permiso) {
  return Boolean(acceso && acceso.permissions.includes(permiso));
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

function esErrorDeSesion(mensaje) {
  return ERRORES_DE_SESION.some((m) => mensaje.startsWith(m));
}

function esErrorDePermiso(mensaje) {
  return ERRORES_DE_PERMISO.some((m) => mensaje.startsWith(m));
}

/*
 * Petición con sesión. Si el token falta o el API lo rechaza, no se queda una
 * tabla a medias: se vuelve al login. Cualquier otro error se lanza con el
 * mensaje del API para mostrarlo en la pantalla.
 */
async function pedir(query, variables) {
  const token = leerSesion(CLAVE_TOKEN);
  if (!token) {
    cerrarSesion("Inicia sesión para ver el dashboard.");
    throw new SesionTerminada();
  }
  const cuerpo = await gql(query, variables, token);
  const error = primerError(cuerpo);
  if (error) {
    if (esErrorDeSesion(error)) {
      cerrarSesion("Tu sesión expiró o el token no es válido. Inicia sesión de nuevo.");
      throw new SesionTerminada();
    }
    throw new Error(error);
  }
  if (leerSesion(CLAVE_TOKEN) !== token) throw new SesionTerminada(); // cerró sesión mientras tanto
  return cuerpo.data;
}

function mensajeDeLectura(fallo, que) {
  return esErrorDePermiso(fallo.message)
    ? `Acceso denegado: tu rol no tiene permiso para ver ${que}. (${fallo.message})`
    : `No se pudieron consultar ${que}: ${fallo.message}`;
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

// En la tabla no hace falta la CLABE completa: solo los últimos 4 dígitos.
function referenciaCuenta(cuenta) {
  const clabe = (cuenta.clabe || "").replace(/\s+/g, "");
  if (clabe) return `****${clabe.slice(-4)}`;
  if (cuenta.cardLastDigits) return `****${cuenta.cardLastDigits}`;
  return "";
}

function textoOVacio(valor) {
  const texto = String(valor || "").trim();
  return texto || null;
}

// ---------------------------------------------------------------------------
// Utilidades de pantalla
// ---------------------------------------------------------------------------

function mostrarAviso(elemento, mensaje) {
  elemento.textContent = mensaje || "";
  elemento.hidden = !mensaje;
}

function celda(texto, clase) {
  const td = document.createElement("td");
  if (clase) td.className = clase;
  td.textContent = texto;
  return td;
}

function etiqueta(texto, clase) {
  const marca = document.createElement("span");
  marca.className = `etiqueta ${clase}`;
  marca.textContent = texto;
  return marca;
}

function celdaEstado(activo, femenino) {
  const td = document.createElement("td");
  td.append(
    activo
      ? etiqueta(femenino ? "Activa" : "Activo", "etiqueta-activa")
      : etiqueta(femenino ? "Inactiva" : "Inactivo", "etiqueta-inactiva")
  );
  return td;
}

function ponerOcupado(boton, ocupado, textoOcupado) {
  if (ocupado) {
    boton.dataset.texto = boton.textContent;
    boton.textContent = textoOcupado;
  } else if (boton.dataset.texto) {
    boton.textContent = boton.dataset.texto;
  }
  boton.disabled = ocupado;
}

function abrirFormulario(idForm) {
  const form = $(idForm);
  form.hidden = false;
  mostrarAviso(form.querySelector(".aviso"), "");
  const primero = form.querySelector("input, select, textarea");
  if (primero) primero.focus();
}

function cerrarFormulario(idForm) {
  const form = $(idForm);
  form.reset();
  mostrarAviso(form.querySelector(".aviso"), "");
  form.hidden = true;
}

// ---------------------------------------------------------------------------
// Vistas y navegación
// ---------------------------------------------------------------------------

function mostrarLogin(mensaje) {
  $("vista-dashboard").hidden = true;
  $("vista-login").hidden = false;
  $("login-password").value = "";
  mostrarAviso($("login-aviso"), mensaje);
  $("login-email").focus();
}

function seccionDelHash() {
  const nombre = location.hash.replace(/^#\/(admin\/)?/, "");
  return SECCIONES[nombre] ? nombre : "financiero";
}

async function mostrarDashboard() {
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

  // Empresa, rol y permisos de la sesión: salen del API, no del navegador.
  try {
    const datos = await pedir(QUERY_ACCESO, {});
    acceso = datos.myAccess;
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    acceso = null;
    $("empresa-nombre").textContent = "Empresa";
    mostrarSeccion("financiero");
    mostrarAviso($("dash-aviso"), `No se pudo leer la sesión: ${fallo.message}`);
    return;
  }

  guardarSesion(CLAVE_EMPRESA, JSON.stringify({ id: acceso.companyId, name: acceso.companyName }));
  $("empresa-nombre").textContent = acceso.companyName;
  $("usuario-nombre").textContent = acceso.userName;
  $("usuario-rol").textContent = acceso.role ? `· ${acceso.role.name}` : "· Sin rol";
  aplicarPermisos();
  mostrarSeccion(seccionDelHash());
}

// Quien no tiene el permiso de escritura no ve la acción de alta.
function aplicarPermisos() {
  $("usr-nuevo").hidden = !puede("company.users.write");
  $("cta-nueva").hidden = !puede("accounts.write");
  $("con-nuevo").hidden = !puede("concepts.write");
  $("ac-asignar").hidden = !puede("concepts.write");
  document.querySelectorAll(".col-accion").forEach((col) => {
    col.hidden = !puede("company.users.write");
  });
  if (!puede("company.users.write")) cerrarFormulario("usr-form");
  if (!puede("accounts.write")) cerrarFormulario("cta-form");
  if (!puede("concepts.write")) cerrarFormulario("con-form");
}

function mostrarSeccion(nombre) {
  const seccion = SECCIONES[nombre];
  for (const clave of Object.keys(SECCIONES)) {
    $(`sec-${clave}`).hidden = clave !== nombre;
  }
  document.querySelectorAll(".menu a").forEach((enlace) => {
    if (enlace.dataset.seccion === nombre) enlace.setAttribute("aria-current", "page");
    else enlace.removeAttribute("aria-current");
  });
  $("titulo-app").textContent = seccion.titulo;
  // Período y moneda solo tienen sentido en el financiero; en administración se cuentan personas.
  $("periodo-consultado").hidden = nombre !== "financiero";
  $("moneda-bloque").hidden = nombre !== "financiero";
  document.title = `${seccion.titulo} · Sistema General de Ingresos`;
  seccion.cargar();
}

function cerrarSesion(mensaje) {
  consultaActual += 1; // cualquier respuesta pendiente se ignora
  borrarSesion();
  acceso = null;
  estado.usuarios = [];
  estado.cuentas = [];
  estado.conceptos = [];
  estado.cuentaElegida = "";
  limpiarResultados();
  for (const id of ["usr-tabla", "cta-tabla", "con-tabla", "ac-lista"]) $(id).replaceChildren();
  for (const id of ["usr-form", "cta-form", "con-form"]) cerrarFormulario(id);
  for (const id of ["usr-aviso", "usr-ok", "cta-aviso", "cta-ok", "con-aviso", "con-ok", "dash-aviso"]) {
    mostrarAviso($(id), "");
  }
  $("empresa-nombre").textContent = "Empresa";
  $("usuario-rol").textContent = "";
  mostrarLogin(mensaje);
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

// ===========================================================================
// DASHBOARD FINANCIERO (actividad 1)
// ===========================================================================

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
      if (esErrorDeSesion(error)) {
        cerrarSesion("Tu sesión expiró o el token no es válido. Inicia sesión de nuevo.");
        return;
      }
      limpiarResultados();
      if (esErrorDePermiso(error)) {
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
  $("tabla-cuentas").replaceChildren(...balance.accounts.map(filaBalance));

  $("resultados").hidden = false;
}

function filaBalance(cuenta) {
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
  return celda(formatoImporte(valor), "num");
}

// ===========================================================================
// USUARIOS
// ===========================================================================

async function cargarUsuarios() {
  mostrarAviso($("usr-aviso"), "");
  if (!acceso) return;
  try {
    const datos = await pedir(QUERY_USUARIOS, { companyId: acceso.companyId });
    estado.usuarios = datos.companyUsers;
    pintarUsuarios();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    estado.usuarios = [];
    pintarUsuarios();
    mostrarAviso($("usr-aviso"), mensajeDeLectura(fallo, "los usuarios"));
  }
}

function pintarUsuarios() {
  const todos = estado.usuarios;

  // Tres conteos calculados con la misma lista, sin otra consulta. Son personas, no importes.
  const activos = todos.filter((u) => u.isActive).length;
  const admins = todos.filter((u) => u.isAdmin && u.isActive).length;
  $("usr-activos").textContent = String(activos);
  $("usr-inactivos").textContent = String(todos.length - activos);
  $("usr-admin").textContent = String(admins);
  // Debe ser 0 o 1. Más de uno es un error de datos del Parcial I: se muestra, no se oculta.
  $("usr-admin-tarjeta").classList.toggle("alerta", admins > 1);
  $("usr-admin-tarjeta").title = admins > 1 ? "Error de datos: hay más de un administrador principal." : "";

  const texto = $("usr-buscar").value.trim().toLowerCase();
  const filtro = $("usr-filtro").value;
  const visibles = todos.filter((u) => {
    if (filtro === "activos" && !u.isActive) return false;
    if (filtro === "inactivos" && u.isActive) return false;
    if (!texto) return true;
    return (
      u.user.name.toLowerCase().includes(texto) || u.user.email.toLowerCase().includes(texto)
    );
  });

  const vacio = $("usr-vacio");
  if (!todos.length) {
    mostrarAviso(vacio, "La empresa no tiene usuarios registrados.");
  } else if (!visibles.length) {
    mostrarAviso(vacio, "Ningún usuario coincide con la búsqueda o el filtro.");
  } else {
    mostrarAviso(vacio, "");
  }
  $("usr-tabla-contenedor").hidden = !visibles.length;
  $("usr-tabla").replaceChildren(...visibles.map(filaUsuario));
}

function filaUsuario(membresia) {
  const fila = document.createElement("tr");
  if (!membresia.isActive) fila.className = "fila-inactiva";

  fila.append(celda(membresia.user.name));
  fila.append(celda(membresia.user.email));
  fila.append(
    membresia.role ? celda(membresia.role.name) : celda("Sin rol asignado", "texto-suave")
  );
  fila.append(celda(membresia.isAdmin ? "Sí" : "No"));
  fila.append(celdaEstado(membresia.isActive, false));

  if (puede("company.users.write")) {
    const accion = document.createElement("td");
    accion.className = "col-accion";
    if (membresia.isActive && !membresia.isAdmin) {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "btn-texto btn-quitar";
      boton.textContent = "Desactivar";
      boton.title = "Deja de operar en la empresa; su historial se conserva.";
      boton.addEventListener("click", () => desactivarUsuario(membresia, boton));
      accion.append(boton);
    } else {
      accion.textContent = "—";
      accion.classList.add("texto-suave");
    }
    fila.append(accion);
  }
  return fila;
}

async function crearUsuario(evento) {
  evento.preventDefault();
  const aviso = $("usr-form-aviso");
  const name = $("usr-nombre").value.trim();
  const email = $("usr-correo").value.trim();
  const password = $("usr-password").value;
  if (!name || !email || !password) {
    mostrarAviso(aviso, "Escribe nombre, correo y contraseña.");
    return;
  }

  const boton = evento.submitter || $("usr-form").querySelector("[type=submit]");
  ponerOcupado(boton, true, "Guardando…");
  mostrarAviso(aviso, "");
  try {
    const datos = await pedir(MUTATION_CREAR_USUARIO, {
      input: { companyId: acceso.companyId, name, email, password },
    });
    const nuevo = datos.createCompanyUser;
    cerrarFormulario("usr-form");
    mostrarAviso(
      $("usr-ok"),
      `Se dio de alta a ${nuevo.user.name} (${nuevo.user.email}) con el rol ` +
        `${nuevo.role ? nuevo.role.name : "sin rol"}.`
    );
    await cargarUsuarios();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    mostrarAviso(aviso, `No se guardó: ${fallo.message}`);
  } finally {
    ponerOcupado(boton, false);
    $("usr-password").value = ""; // la contraseña no se queda en pantalla
  }
}

async function desactivarUsuario(membresia, boton) {
  ponerOcupado(boton, true, "Desactivando…");
  mostrarAviso($("usr-aviso"), "");
  mostrarAviso($("usr-ok"), "");
  try {
    await pedir(MUTATION_DESACTIVAR_USUARIO, { id: membresia.id });
    mostrarAviso(
      $("usr-ok"),
      `${membresia.user.name} ya no puede operar en la empresa. Su historial se conserva.`
    );
    await cargarUsuarios();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    ponerOcupado(boton, false);
    mostrarAviso($("usr-aviso"), `No se pudo desactivar: ${fallo.message}`);
  }
}

// ===========================================================================
// CUENTAS
// ===========================================================================

function prepararFiltrosCuenta() {
  const chips = [["", "Todas"], ...TIPOS_CUENTA].map(([valor, texto]) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = valor === estado.filtroCuenta ? "chip activo" : "chip";
    chip.dataset.tipo = valor;
    chip.textContent = texto;
    return chip;
  });
  $("cta-filtros").replaceChildren(...chips);

  const opciones = TIPOS_CUENTA.map(([valor, texto]) => new Option(texto, valor));
  $("cta-tipo").replaceChildren(new Option("Elige un tipo", ""), ...opciones);
}

async function cargarCuentas() {
  mostrarAviso($("cta-aviso"), "");
  if (!acceso) return;
  try {
    const datos = await pedir(QUERY_CUENTAS, { companyId: acceso.companyId });
    estado.cuentas = datos.accounts;
    pintarCuentas();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    estado.cuentas = [];
    pintarCuentas();
    mostrarAviso($("cta-aviso"), mensajeDeLectura(fallo, "las cuentas"));
  }
}

function pintarCuentas() {
  const todas = estado.cuentas;
  const soloActivas = $("cta-solo-activas").checked;
  const visibles = todas.filter(
    (c) =>
      (!estado.filtroCuenta || c.accountType === estado.filtroCuenta) &&
      (!soloActivas || c.isActive)
  );

  $("cta-filtros").querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("activo", chip.dataset.tipo === estado.filtroCuenta);
    chip.setAttribute("aria-pressed", String(chip.dataset.tipo === estado.filtroCuenta));
  });

  const vacio = $("cta-vacio");
  if (!todas.length) {
    mostrarAviso(vacio, "La empresa no tiene cuentas registradas.");
  } else if (!visibles.length) {
    mostrarAviso(vacio, "No hay cuentas con ese filtro.");
  } else {
    mostrarAviso(vacio, "");
  }
  $("cta-tabla-contenedor").hidden = !visibles.length;
  $("cta-tabla").replaceChildren(
    ...visibles.map((cuenta) => {
      const fila = document.createElement("tr");
      if (!cuenta.isActive) fila.className = "fila-inactiva";
      fila.append(celda(cuenta.name));
      fila.append(celda(ETIQUETA_CUENTA[cuenta.accountType] || cuenta.accountType));
      fila.append(celda(cuenta.bankName || ""));
      fila.append(celda(referenciaCuenta(cuenta), "referencia"));
      fila.append(celdaEstado(cuenta.isActive, true));
      return fila;
    })
  );
}

async function crearCuenta(evento) {
  evento.preventDefault();
  const aviso = $("cta-form-aviso");
  const name = $("cta-nombre").value.trim();
  const accountType = $("cta-tipo").value;
  if (!name || !accountType) {
    mostrarAviso(aviso, "Escribe el nombre y elige el tipo de cuenta.");
    return;
  }

  const input = { companyId: acceso.companyId, name, accountType };
  const bankName = textoOVacio($("cta-banco").value);
  const clabe = textoOVacio($("cta-clabe").value);
  const shortDescription = textoOVacio($("cta-descripcion").value);
  if (bankName) input.bankName = bankName;
  if (clabe) input.clabe = clabe;
  if (shortDescription) input.shortDescription = shortDescription;

  const boton = evento.submitter || $("cta-form").querySelector("[type=submit]");
  ponerOcupado(boton, true, "Guardando…");
  mostrarAviso(aviso, "");
  try {
    const datos = await pedir(MUTATION_CREAR_CUENTA, { input });
    cerrarFormulario("cta-form");
    mostrarAviso($("cta-ok"), `Se creó la cuenta ${datos.createAccount.name}.`);
    await cargarCuentas();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    mostrarAviso(aviso, `No se guardó: ${fallo.message}`);
  } finally {
    ponerOcupado(boton, false);
  }
}

// ===========================================================================
// CONCEPTOS
// ===========================================================================

async function cargarConceptos() {
  mostrarAviso($("con-aviso"), "");
  if (!acceso) return;
  const errores = [];

  const [conceptos, cuentas] = await Promise.allSettled([
    pedir(QUERY_CONCEPTOS, { companyId: acceso.companyId }),
    pedir(QUERY_CUENTAS, { companyId: acceso.companyId }),
  ]);
  if ([conceptos, cuentas].some((r) => r.status === "rejected" && r.reason instanceof SesionTerminada)) {
    return;
  }

  if (conceptos.status === "fulfilled") {
    estado.conceptos = conceptos.value.concepts;
  } else {
    estado.conceptos = [];
    errores.push(mensajeDeLectura(conceptos.reason, "el catálogo de conceptos"));
  }
  if (cuentas.status === "fulfilled") {
    estado.cuentas = cuentas.value.accounts;
  } else {
    estado.cuentas = [];
    errores.push(mensajeDeLectura(cuentas.reason, "las cuentas"));
  }

  mostrarAviso($("con-aviso"), errores.join(" "));
  pintarCatalogo();
  pintarSelectorCuentas();
  await cargarConceptosDeCuenta();
}

function pintarCatalogo() {
  const todos = estado.conceptos;
  const soloActivos = $("con-solo-activos").checked;
  const visibles = todos.filter(
    (c) =>
      (!estado.filtroConcepto || c.conceptType === estado.filtroConcepto) &&
      (!soloActivos || c.isActive)
  );

  $("con-filtros").querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("activo", chip.dataset.tipo === estado.filtroConcepto);
    chip.setAttribute("aria-pressed", String(chip.dataset.tipo === estado.filtroConcepto));
  });

  const vacio = $("con-vacio");
  if (!todos.length) {
    mostrarAviso(vacio, "La empresa no tiene conceptos registrados.");
  } else if (!visibles.length) {
    mostrarAviso(vacio, "No hay conceptos con ese filtro.");
  } else {
    mostrarAviso(vacio, "");
  }
  $("con-tabla-contenedor").hidden = !visibles.length;
  $("con-tabla").replaceChildren(
    ...visibles.map((concepto) => {
      const fila = document.createElement("tr");
      if (!concepto.isActive) fila.className = "fila-inactiva";
      fila.append(celda(concepto.name));
      fila.append(celda(ETIQUETA_CONCEPTO[concepto.conceptType] || concepto.conceptType));
      fila.append(celdaEstado(concepto.isActive, false));
      return fila;
    })
  );

  // Opciones para asignar: conceptos activos del catálogo. Si ya está asignado,
  // el API rechaza el duplicado y la pantalla lo dice.
  const activos = todos.filter((c) => c.isActive);
  $("ac-concepto").replaceChildren(
    ...(activos.length
      ? activos.map(
          (c) => new Option(`${c.name} (${ETIQUETA_CONCEPTO[c.conceptType] || c.conceptType})`, c.id)
        )
      : [new Option("No hay conceptos activos", "")])
  );
  $("ac-btn-asignar").disabled = !activos.length;
}

function pintarSelectorCuentas() {
  const cuentas = estado.cuentas;
  if (!cuentas.some((c) => c.id === estado.cuentaElegida)) {
    const primera = cuentas.find((c) => c.isActive) || cuentas[0];
    estado.cuentaElegida = primera ? primera.id : "";
  }
  $("ac-cuenta").replaceChildren(
    ...cuentas.map((c) => new Option(c.isActive ? c.name : `${c.name} (inactiva)`, c.id))
  );
  $("ac-cuenta").value = estado.cuentaElegida;
  $("ac-cuenta").disabled = !cuentas.length;
}

async function cargarConceptosDeCuenta() {
  const cuenta = estado.cuentas.find((c) => c.id === estado.cuentaElegida);
  $("ac-titulo").textContent = cuenta ? `Conceptos de la cuenta ${cuenta.name}` : "Conceptos de la cuenta";
  $("ac-lista").replaceChildren();

  if (!cuenta) {
    mostrarAviso($("ac-vacio"), "La empresa no tiene cuentas. Crea una en la sección Cuentas.");
    $("ac-asignar").hidden = true;
    return;
  }
  $("ac-asignar").hidden = !puede("concepts.write");

  try {
    const datos = await pedir(QUERY_CONCEPTOS_CUENTA, { accountId: cuenta.id });
    if (estado.cuentaElegida !== cuenta.id) return; // cambió de cuenta mientras tanto
    const asignados = datos.accountConcepts.filter((r) => r.isActive);
    mostrarAviso(
      $("ac-vacio"),
      asignados.length ? "" : `La cuenta ${cuenta.name} todavía no tiene conceptos asignados.`
    );
    $("ac-lista").replaceChildren(...asignados.map((r) => filaAsignado(cuenta, r.concept)));
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    mostrarAviso($("ac-vacio"), mensajeDeLectura(fallo, "los conceptos de la cuenta"));
  }
}

function filaAsignado(cuenta, concepto) {
  const item = document.createElement("li");
  const nombre = document.createElement("span");
  nombre.className = "asignado";
  nombre.textContent = concepto.name;
  const tipo = document.createElement("small");
  tipo.textContent = ETIQUETA_CONCEPTO[concepto.conceptType] || concepto.conceptType;
  nombre.append(" ", tipo);
  item.append(nombre);

  if (puede("concepts.write")) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "btn-texto btn-quitar";
    boton.textContent = "Quitar";
    boton.addEventListener("click", () => quitarConcepto(cuenta, concepto, boton));
    item.append(boton);
  }
  return item;
}

async function crearConcepto(evento) {
  evento.preventDefault();
  const aviso = $("con-form-aviso");
  const name = $("con-nombre").value.trim();
  const tipo = document.querySelector('input[name="con-tipo"]:checked');
  if (!name || !tipo) {
    mostrarAviso(aviso, "Escribe el nombre y elige si es ingreso o egreso.");
    return;
  }
  const input = { companyId: acceso.companyId, name, conceptType: tipo.value };
  const shortDescription = textoOVacio($("con-descripcion").value);
  if (shortDescription) input.shortDescription = shortDescription;

  const boton = evento.submitter || $("con-form").querySelector("[type=submit]");
  ponerOcupado(boton, true, "Guardando…");
  mostrarAviso(aviso, "");
  try {
    const datos = await pedir(MUTATION_CREAR_CONCEPTO, { input });
    const nuevo = datos.createConcept;
    cerrarFormulario("con-form");
    mostrarAviso(
      $("con-ok"),
      `Se creó el concepto ${nuevo.name} (${ETIQUETA_CONCEPTO[nuevo.conceptType]}).`
    );
    await cargarConceptos();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    mostrarAviso(aviso, `No se guardó: ${fallo.message}`);
  } finally {
    ponerOcupado(boton, false);
  }
}

async function asignarConcepto() {
  const cuenta = estado.cuentas.find((c) => c.id === estado.cuentaElegida);
  const conceptId = $("ac-concepto").value;
  if (!cuenta || !conceptId) return;

  const boton = $("ac-btn-asignar");
  ponerOcupado(boton, true, "Asignando…");
  mostrarAviso($("con-aviso"), "");
  mostrarAviso($("con-ok"), "");
  try {
    const datos = await pedir(MUTATION_ASIGNAR, { input: { accountId: cuenta.id, conceptId } });
    mostrarAviso(
      $("con-ok"),
      `${datos.assignConceptToAccount.concept.name} ya se puede usar en la cuenta ${cuenta.name}.`
    );
    await cargarConceptosDeCuenta();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    mostrarAviso($("con-aviso"), `No se asignó: ${fallo.message}`);
  } finally {
    ponerOcupado(boton, false);
  }
}

async function quitarConcepto(cuenta, concepto, boton) {
  ponerOcupado(boton, true, "Quitando…");
  mostrarAviso($("con-aviso"), "");
  mostrarAviso($("con-ok"), "");
  try {
    await pedir(MUTATION_QUITAR, { accountId: cuenta.id, conceptId: concepto.id });
    mostrarAviso(
      $("con-ok"),
      `${concepto.name} ya no se permite en la cuenta ${cuenta.name}. Sigue en el catálogo.`
    );
    await cargarConceptosDeCuenta();
  } catch (fallo) {
    if (fallo instanceof SesionTerminada) return;
    ponerOcupado(boton, false);
    mostrarAviso($("con-aviso"), `No se quitó: ${fallo.message}`);
  }
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

prepararFiltrosCuenta();

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

window.addEventListener("hashchange", () => {
  if (acceso && !$("vista-dashboard").hidden) mostrarSeccion(seccionDelHash());
});

document.querySelectorAll("[data-cerrar]").forEach((boton) => {
  boton.addEventListener("click", () => cerrarFormulario(boton.dataset.cerrar));
});

// Usuarios
$("usr-buscar").addEventListener("input", pintarUsuarios);
$("usr-filtro").addEventListener("change", pintarUsuarios);
$("usr-nuevo").addEventListener("click", () => {
  mostrarAviso($("usr-ok"), "");
  abrirFormulario("usr-form");
});
$("usr-form").addEventListener("submit", crearUsuario);

// Cuentas
$("cta-filtros").addEventListener("click", (evento) => {
  const chip = evento.target.closest(".chip");
  if (!chip) return;
  estado.filtroCuenta = chip.dataset.tipo;
  pintarCuentas();
});
$("cta-solo-activas").addEventListener("change", pintarCuentas);
$("cta-nueva").addEventListener("click", () => {
  mostrarAviso($("cta-ok"), "");
  abrirFormulario("cta-form");
});
$("cta-form").addEventListener("submit", crearCuenta);

// Conceptos
$("con-filtros").addEventListener("click", (evento) => {
  const chip = evento.target.closest(".chip");
  if (!chip) return;
  estado.filtroConcepto = chip.dataset.tipo;
  pintarCatalogo();
});
$("con-solo-activos").addEventListener("change", pintarCatalogo);
$("con-nuevo").addEventListener("click", () => {
  mostrarAviso($("con-ok"), "");
  abrirFormulario("con-form");
});
$("con-form").addEventListener("submit", crearConcepto);
$("ac-cuenta").addEventListener("change", () => {
  estado.cuentaElegida = $("ac-cuenta").value;
  mostrarAviso($("con-ok"), "");
  cargarConceptosDeCuenta();
});
$("ac-btn-asignar").addEventListener("click", asignarConcepto);

if (leerSesion(CLAVE_TOKEN)) {
  mostrarDashboard();
} else {
  mostrarLogin("");
}
