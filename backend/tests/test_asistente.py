"""El Asistente: protegido por sesión, no inventa cifras, protege los nombres,
sugiere (no ejecuta) acciones y se degrada bien sin llave. Sin llamadas reales
a NVIDIA: se simula el modelo."""

import json
import re

import pytest
from fastapi.testclient import TestClient

import modules.asistente.router as router_asistente
from ia.servicio import RespuestaIA
from main import app


@pytest.fixture()
def cliente():
    with TestClient(app) as cliente_http:
        yield cliente_http


@pytest.fixture()
def modelo(monkeypatch):
    """Modelo falso: guarda lo que recibe y responde lo que el test le indique."""
    recibido: dict = {"respuesta": "ok", "llamadas": []}

    async def falso(mensaje, contexto_json, historial=None):
        recibido["llamadas"].append({"mensaje": mensaje, "contexto": contexto_json, "historial": historial or []})
        texto = recibido["respuesta"](mensaje) if callable(recibido["respuesta"]) else recibido["respuesta"]
        from ia.acciones import extraer

        limpio, acciones = extraer(texto)
        return RespuestaIA(texto=limpio, modelo="modelo-de-prueba", acciones=acciones)

    monkeypatch.setattr(router_asistente, "preguntar", falso)
    return recibido


def preguntar(cliente, cabeceras, mensaje="hola", **extra):
    return cliente.post("/api/asistente/preguntar", json={"mensaje": mensaje, **extra}, headers=cabeceras)


def test_exige_sesion_iniciada(cliente):
    assert cliente.post("/api/asistente/preguntar", json={"mensaje": "hola"}).status_code == 401


def test_responde_usando_el_resumen_del_proyecto(cliente, cabeceras_demo, modelo):
    modelo["respuesta"] = "Vendiste S/ 485.50 hoy."
    respuesta = preguntar(cliente, cabeceras_demo, "¿cuánto vendí hoy?")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["respuesta"] == "Vendiste S/ 485.50 hoy."
    assert datos["acciones"] == [] and datos["modelo"] == "modelo-de-prueba"
    assert re.fullmatch(r"[0-9a-f-]{36}", datos["id_respuesta"])
    # El contexto que recibió el "modelo" es el resumen real de demo, no inventado
    assert "485.50" in modelo["llamadas"][0]["contexto"]


def test_anita_y_demo_reciben_contextos_distintos(cliente, cabeceras_anita, modelo):
    preguntar(cliente, cabeceras_anita)
    # Anita es una empresa real recién empezada: su contexto no tiene las cifras de demo
    assert "485.50" not in modelo["llamadas"][0]["contexto"]


def test_se_degrada_con_claridad_sin_llave_configurada(cliente, cabeceras_demo, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("MI_PUESTITO_IA_PROVEEDOR", raising=False)
    respuesta = preguntar(cliente, cabeceras_demo)
    assert respuesta.status_code == 503
    assert "NVIDIA_API_KEY" in respuesta.json()["detail"]


# ---- Privacidad (ADR-034): el proveedor externo nunca ve nombres reales ----

def test_el_modelo_no_ve_nombres_y_el_operador_si(cliente, cabeceras_demo, modelo):
    def responder(pregunta):
        # El modelo responde con el alias que vino en la pregunta, que debe ser
        # el mismo con el que la Sra. Flora aparece en el contexto
        alias = re.search(r"Cliente \d+", pregunta).group(0)
        assert f'"nombre": "{alias}"' in modelo["llamadas"][-1]["contexto"]
        return f"{alias} debe S/ 45.00."

    modelo["respuesta"] = responder
    respuesta = preguntar(cliente, cabeceras_demo, "¿Cuánto debe la sra. flora?")

    enviado = modelo["llamadas"][0]
    for nombre in ("Flora", "Doña Carmen", "Distribuidora Norte", "Avícola"):
        assert nombre.lower() not in enviado["contexto"].lower()
    assert "flora" not in enviado["mensaje"].lower()
    assert "485.50" in enviado["contexto"]  # las cifras sí viajan: sin ellas no sirve
    assert respuesta.json()["respuesta"] == "Sra. Flora debe S/ 45.00."


def test_el_historial_tambien_viaja_seudonimizado(cliente, cabeceras_demo, modelo):
    historial = [
        {"rol": "operador", "texto": "¿Cuánto debe la Sra. Flora?"},
        {"rol": "asistente", "texto": "La Sra. Flora debe S/ 45.00."},
    ]
    preguntar(cliente, cabeceras_demo, "¿Y desde cuándo?", historial=historial)
    turnos = modelo["llamadas"][0]["historial"]
    assert [rol for rol, _ in turnos] == ["operador", "asistente"]
    assert all("flora" not in texto.lower() for _, texto in turnos)


def test_los_rotulos_genericos_no_se_ocultan():
    from ia.privacidad import Seudonimos

    alias = Seudonimos()
    assert alias.cliente("Orden 2") == "Orden 2"
    assert alias.cliente("Sra. Flora") == "Cliente 1"
    assert alias.cliente("Sra. Flora") == "Cliente 1"  # estable dentro de la consulta


def test_reidentificar_no_confunde_cliente_1_con_cliente_12():
    from ia.privacidad import Seudonimos

    alias = Seudonimos()
    for nombre in [f"Persona {i}" for i in range(1, 13)]:
        alias.cliente(nombre)
    assert alias.reidentificar("Cliente 12 y Cliente 1") == "Persona 12 y Persona 1"


def test_una_pregunta_enorme_se_rechaza(cliente, cabeceras_demo):
    assert preguntar(cliente, cabeceras_demo, "x" * 501).status_code == 422


def test_sin_dashboard_el_asistente_sigue_respondiendo(cliente, cabeceras_demo, modelo, monkeypatch):
    # D-06: el Asistente ya no depende del router del Dashboard
    import modules.dashboard.servicio as servicio_dashboard

    def roto(*_):
        raise RuntimeError("tabla dañada")

    monkeypatch.setattr(servicio_dashboard, "calcular_resumen", roto)
    modelo["respuesta"] = lambda _p: modelo["llamadas"][-1]["contexto"]
    respuesta = preguntar(cliente, cabeceras_demo)
    assert respuesta.status_code == 200
    assert "no están disponibles" in respuesta.json()["respuesta"]


# ---- Acciones sugeridas (ADR-037) ----

def test_la_accion_se_convierte_en_boton_y_sale_del_texto(cliente, cabeceras_demo, modelo):
    modelo["respuesta"] = "Puedes cobrarla en Ventas.\nACCION: ir_a ventas"
    datos = preguntar(cliente, cabeceras_demo, "¿Cómo cobro la orden 2?").json()
    assert datos["respuesta"] == "Puedes cobrarla en Ventas."
    assert datos["acciones"] == [{"tipo": "ir_a", "pantalla": "ventas", "etiqueta": "Ir a Ventas"}]


@pytest.mark.parametrize(
    "texto",
    ["ACCION: ir_a configuracion", "ACCION: borrar ventas", "ACCION: ir_a http://malo.example"],
)
def test_acciones_fuera_de_la_lista_blanca_se_descartan(texto):
    from ia.acciones import extraer

    assert extraer(f"Hola.\n{texto}")[1] == []


def test_maximo_dos_acciones_y_sin_repetir():
    from ia.acciones import extraer

    _, acciones = extraer("x\nACCION: ir_a ventas\nACCION: ir_a ventas\nACCIÓN: ir_a fiados\nACCION: ir_a caja")
    assert [a["pantalla"] for a in acciones] == ["ventas", "fiados"]


# ---- Proveedor y orden de modelos (ADR-036) ----

def test_el_proveedor_quita_el_razonamiento_interno():
    from ia.compatible_openai import limpiar

    assert limpiar("<think>sumo 120+45</think>\nTendrás S/ 165.00.") == "Tendrás S/ 165.00."


def test_si_un_modelo_falla_se_prueba_el_siguiente(monkeypatch):
    import asyncio

    from ia import servicio
    from ia.compatible_openai import ProveedorCompatibleOpenAI

    probados = []

    async def responder(self, mensajes, modelo, tiempo_limite, extra=None):
        probados.append(modelo)
        if modelo == "lento":
            raise TimeoutError
        return "Listo.\nACCION: ir_a fiados"

    monkeypatch.setattr(ProveedorCompatibleOpenAI, "responder", responder)
    monkeypatch.setenv("NVIDIA_API_KEY", "llave-de-prueba")
    monkeypatch.setenv("MI_PUESTITO_IA_MODELOS", "lento,rapido")
    respuesta = asyncio.run(servicio.preguntar("hola", "{}"))
    assert probados == ["lento", "rapido"]
    assert (respuesta.modelo, respuesta.texto, respuesta.acciones[0]["pantalla"]) == ("rapido", "Listo.", "fiados")


def test_el_orden_verificado_se_usa_si_no_hay_variable(monkeypatch, tmp_path):
    import rutas
    from ia import configuracion

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.delenv("MI_PUESTITO_IA_MODELOS", raising=False)
    monkeypatch.delenv("NVIDIA_MODELOS_PRIORIDAD", raising=False)
    monkeypatch.delenv("MI_PUESTITO_IA_PROVEEDOR", raising=False)
    (tmp_path / configuracion.ARCHIVO_MODELOS).write_text(json.dumps({
        "proveedor": "nvidia",
        "modelos": [{"modelo": "b", "responde": True}, {"modelo": "a", "responde": True},
                    {"modelo": "caido", "responde": False}],
    }))
    assert configuracion.leer().modelos == ("b", "a")
    # Sin archivo, la lista por defecto: el orden medido el 2026-10-08 (correctos y rápidos
    # primero); Gemma 4, la familia del modelo local futuro, queda de respaldo
    (tmp_path / configuracion.ARCHIVO_MODELOS).unlink()
    assert configuracion.leer().modelos == tuple(configuracion.MODELOS_NVIDIA)
    assert configuracion.MODELOS_NVIDIA[0] == "nvidia/nemotron-3.5-bolt-e4b"


def test_un_proveedor_local_no_necesita_llave(monkeypatch):
    from ia import configuracion

    monkeypatch.setenv("MI_PUESTITO_IA_PROVEEDOR", "local")
    monkeypatch.setenv("MI_PUESTITO_IA_MODELOS", "gemma-local")
    monkeypatch.delenv("MI_PUESTITO_IA_URL", raising=False)
    config = configuracion.leer()
    assert config.lista and config.url_base == "http://127.0.0.1:11434/v1"


def test_la_verificacion_no_guarda_la_llave(monkeypatch, tmp_path):
    import asyncio

    import rutas
    from ia import verificar
    from ia.compatible_openai import ProveedorCompatibleOpenAI

    async def responder(self, mensajes, modelo, tiempo_limite, extra=None):
        if modelo == "no-existe":
            raise RuntimeError("404")
        return "Tendrás S/ 165."

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.setattr(ProveedorCompatibleOpenAI, "responder", responder)
    monkeypatch.setenv("NVIDIA_API_KEY", "llave-falsa-que-no-debe-quedar-en-disco")
    datos = asyncio.run(verificar.verificar(["no-existe", "bueno"]))
    guardado = (tmp_path / "ia_modelos.json").read_text(encoding="utf-8")
    assert "llave-falsa" not in guardado
    assert [m["modelo"] for m in datos["modelos"]] == ["bueno", "no-existe"]


# ---- Registro para fine-tuning (ADR-038) ----

def test_el_registro_esta_apagado_por_defecto(cliente, cabeceras_demo, modelo, monkeypatch, tmp_path):
    import rutas

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.delenv("MI_PUESTITO_IA_REGISTRO", raising=False)
    preguntar(cliente, cabeceras_demo, "¿Cuánto debe la Sra. Flora?")
    assert list(tmp_path.glob("ia_registro_*.jsonl")) == []


def test_en_modo_demo_registra_solo_demo_y_sin_nombres(cliente, cabeceras_demo, cabeceras_anita, modelo,
                                                        monkeypatch, tmp_path):
    import rutas

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.setenv("MI_PUESTITO_IA_REGISTRO", "demo")
    modelo["respuesta"] = lambda p: re.search(r"Cliente \d+", p).group(0) + " debe S/ 45.00."
    datos = preguntar(cliente, cabeceras_demo, "¿Cuánto debe la Sra. Flora?").json()
    modelo["respuesta"] = "ok"
    preguntar(cliente, cabeceras_anita, "hola")  # negocio real: no se registra en modo demo

    assert cliente.post("/api/asistente/valoracion", json={"id_respuesta": datos["id_respuesta"], "util": True},
                        headers=cabeceras_demo).status_code == 204
    assert [p.name for p in tmp_path.glob("ia_registro_*.jsonl")] == ["ia_registro_demo.jsonl"]
    filas = [json.loads(linea) for linea in (tmp_path / "ia_registro_demo.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [f["tipo"] for f in filas] == ["intercambio", "valoracion"]
    texto = json.dumps(filas, ensure_ascii=False).lower()
    assert "flora" not in texto and "doña carmen" not in texto
    # Formato de chat listo para entrenar: system, user y la respuesta del modelo
    assert [m["role"] for m in filas[0]["mensajes"]] == ["system", "user", "assistant"]


def test_un_modelo_rapido_que_suma_mal_no_queda_primero(monkeypatch, tmp_path):
    # Caso real del 2026-10-08: gpt-oss-20b respondió en 4 s "Tendrás S/ 75"
    # (120 + 45 = 165) y la versión anterior lo ponía primero por ser el más rápido
    import asyncio

    import rutas
    from ia import configuracion, verificar
    from ia.compatible_openai import ProveedorCompatibleOpenAI

    async def responder(self, mensajes, modelo, tiempo_limite, extra=None):
        return "Tendrás S/ 75." if modelo == "rapido-pero-mal" else "Tendrás S/ 165 en total."

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    monkeypatch.setattr(ProveedorCompatibleOpenAI, "responder", responder)
    monkeypatch.setenv("NVIDIA_API_KEY", "llave-falsa")
    monkeypatch.delenv("MI_PUESTITO_IA_MODELOS", raising=False)
    monkeypatch.delenv("NVIDIA_MODELOS_PRIORIDAD", raising=False)
    monkeypatch.delenv("MI_PUESTITO_IA_PROVEEDOR", raising=False)

    datos = asyncio.run(verificar.verificar(["rapido-pero-mal", "correcto"]))
    assert [(m["modelo"], m["correcto"]) for m in datos["modelos"]] == [
        ("correcto", True), ("rapido-pero-mal", False),
    ]
    # El Asistente ni siquiera intenta con el que suma mal
    assert configuracion.leer().modelos == ("correcto",)


def test_un_timeout_tiene_un_reintento(monkeypatch):
    import asyncio

    import httpx

    from ia import verificar

    llamadas = []

    class Lento:
        async def responder(self, mensajes, modelo, tiempo_limite, extra=None):
            llamadas.append(modelo)
            if len(llamadas) == 1:
                raise httpx.ReadTimeout("frío")
            return "S/ 165"

    fila = asyncio.run(verificar.probar(Lento(), "gemma-en-frio"))
    assert len(llamadas) == 2 and fila["responde"] and fila["correcto"]


# ---- Modelos de razonamiento (visto con la llave real el 2026-10-08) ----

def test_un_borrador_de_razonamiento_nunca_llega_al_operador(monkeypatch):
    # Nemotron 3.5 sin ajustes devolvió "Here's a thinking process: ..." en inglés,
    # cortado por max_tokens: se descarta y se prueba el siguiente modelo
    import asyncio

    import httpx

    from ia import servicio

    def respuesta_http(contenido, razonamiento=None):
        mensaje = {"content": contenido}
        if razonamiento:
            mensaje["reasoning_content"] = razonamiento
        return httpx.Response(200, json={"choices": [{"message": mensaje, "finish_reason": "stop"}]},
                              request=httpx.Request("POST", "http://x"))

    respuestas = {
        "piensa-en-voz-alta": respuesta_http("Here's a thinking process:\n1. Analyze user input..."),
        "duplica": respuesta_http("Analizo la pregunta...", razonamiento="Analizo la pregunta..."),
        "bueno": respuesta_http("Cliente 1 debe **S/ 45.00**.\nACCION: ir_a fiados"),
    }
    enviados = []

    async def post(self, url, headers=None, json=None):
        enviados.append(json)
        return respuestas[json["model"]]

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    monkeypatch.setenv("NVIDIA_API_KEY", "llave-falsa")
    monkeypatch.setenv("MI_PUESTITO_IA_MODELOS", "piensa-en-voz-alta,duplica,bueno")
    respuesta = asyncio.run(servicio.preguntar("¿Cuánto debe Cliente 1?", '{"deuda_cliente": "45.00"}'))
    assert respuesta.modelo == "bueno"
    assert respuesta.texto == "Cliente 1 debe S/ 45.00."  # sin asteriscos de markdown
    assert respuesta.acciones[0]["pantalla"] == "fiados"


def test_cada_familia_lleva_su_ajuste_para_apagar_el_razonamiento():
    from ia.configuracion import ajustes_para

    assert ajustes_para("nvidia/nemotron-3.5-lightning-30b-a3b") == {"chat_template_kwargs": {"enable_thinking": False}}
    assert ajustes_para("openai/gpt-oss-20b") == {"reasoning_effort": "low"}
    assert ajustes_para("google/gemma-4-31b-it") == {}


def test_el_ajuste_viaja_en_la_peticion(monkeypatch):
    import asyncio

    import httpx

    from ia import servicio

    enviados = []

    async def post(self, url, headers=None, json=None):
        enviados.append(json)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Listo."}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    monkeypatch.setenv("NVIDIA_API_KEY", "llave-falsa")
    monkeypatch.setenv("MI_PUESTITO_IA_MODELOS", "nvidia/nemotron-3.5-lightning-30b-a3b")
    asyncio.run(servicio.preguntar("hola", "{}"))
    assert enviados[0]["chat_template_kwargs"] == {"enable_thinking": False}


def test_un_historial_largo_se_recorta_en_vez_de_fallar(cliente, cabeceras_demo, modelo):
    historial = [{"rol": "asistente", "texto": "x" * 5000}]
    assert preguntar(cliente, cabeceras_demo, "¿y ahora?", historial=historial).status_code == 200
    assert len(modelo["llamadas"][0]["historial"][0][1]) == 1000


# ---- Ajustes tras la prueba real en Staging (2026-10-10) ----

def test_el_articulo_se_ajusta_al_restituir_el_nombre():
    # El modelo escribió "El Cliente 1 te debe…" y quedaba "El Sra. Flora"
    from ia.privacidad import Seudonimos

    alias = Seudonimos()
    alias.cliente("Sra. Flora")
    alias.cliente("Restaurante Doña Carmen")
    assert alias.reidentificar("El Cliente 1 te debe. Cobra al Cliente 2 y anota la deuda del Cliente 1.") == (
        "Sra. Flora te debe. Cobra a Restaurante Doña Carmen y anota la deuda de Sra. Flora."
    )


def test_si_el_modelo_nombra_una_pantalla_sin_la_linea_accion_igual_hay_boton():
    from ia.acciones import extraer

    texto, acciones = extraer("Para ver todos los fiados, ve a la pantalla fiados.")
    assert texto == "Para ver todos los fiados, ve a la pantalla fiados."
    assert acciones == [{"tipo": "ir_a", "pantalla": "fiados", "etiqueta": "Ir a Fiados"}]
    assert extraer("Puedes cobrarla en Ventas.")[1] == []  # sin "pantalla", no se adivina


def test_el_asistente_ve_a_todos_los_que_deben_seudonimizados(cliente, cabeceras_demo, modelo):
    # Antes solo veía la deuda de quien tenía una orden abierta y "adivinaba" el mayor
    preguntar(cliente, cabeceras_demo, "¿Quién me debe más?")
    contexto = json.loads(modelo["llamadas"][0]["contexto"])
    deudas = [c["deuda"] for c in contexto["clientes_que_deben"]]
    assert deudas == sorted(deudas, key=float, reverse=True) and deudas[0] == "45.00"
    assert all(c["nombre"].startswith("Cliente ") for c in contexto["clientes_que_deben"])


# ---- Garantías halladas con la evaluación real (2026-11-01) ----

def test_cifras_inventadas_no_pasan():
    # Casos reales: "te deben S/ 130.00" con 132.50 en los datos; "este mes S/ 12.50"
    from decimal import Decimal

    from ia.cifras import cifras_no_respaldadas

    contexto = '{"fiados_por_cobrar": "132.50", "deuda": "45.00", "otra": "32.50"}'
    assert cifras_no_respaldadas("Te deben S/ 130.00", contexto) == {Decimal("130.00")}
    assert cifras_no_respaldadas("Este mes suman S/ 12.50", contexto) == {Decimal("12.50")}  # 45 − 32.50 no vale
    assert cifras_no_respaldadas("Debe 99.90 soles", contexto) == {Decimal("99.90")}
    assert cifras_no_respaldadas("Te deben S/ 132.50 y Flora debe 45.00.", contexto) == set()
    assert cifras_no_respaldadas("Tienes 3 ventas y 12 órdenes el 2026-11-02", contexto) == set()  # no son dinero


def test_se_permite_la_cuenta_con_cifras_que_dio_el_operador():
    from ia.cifras import cifras_no_respaldadas

    assert cifras_no_respaldadas("Tendrás S/ 165.", "{}", "Vendí S/ 120 y me deben 45") == set()
    assert cifras_no_respaldadas("Te quedan S/ 75.", "{}", "Vendí S/ 120 y me deben 45") == set()


def _falsear_modelos(monkeypatch, respuestas: dict):
    """Cada modelo devuelve su texto, o lanza si lo que se le dio es una excepción."""
    import ia.compatible_openai as proveedor

    llamadas = []

    async def responder(self, mensajes, modelo, tiempo_limite, extra=None):
        llamadas.append(modelo)
        salida = respuestas[modelo]
        if isinstance(salida, list):
            salida = salida.pop(0)
        if isinstance(salida, Exception):
            raise salida
        return salida

    monkeypatch.setattr(proveedor.ProveedorCompatibleOpenAI, "responder", responder)
    monkeypatch.setenv("NVIDIA_API_KEY", "llave-falsa")
    monkeypatch.setenv("MI_PUESTITO_IA_MODELOS", ",".join(respuestas))
    return llamadas


def test_si_un_modelo_inventa_una_cifra_responde_el_siguiente(monkeypatch):
    import asyncio

    from ia import servicio

    _falsear_modelos(monkeypatch, {"inventa": "Te deben S/ 130.00.", "exacto": "Te deben S/ 132.50."})
    respuesta = asyncio.run(servicio.preguntar("¿Cuánto me deben?", '{"fiados_por_cobrar": "132.50"}'))
    assert (respuesta.modelo, respuesta.texto) == ("exacto", "Te deben S/ 132.50.")


def test_si_todos_inventan_lo_dice_y_ofrece_la_caja(monkeypatch):
    import asyncio

    from ia import servicio

    _falsear_modelos(monkeypatch, {"inventa": "Te deben S/ 130.00.", "otro": "Te deben S/ 131.00."})
    respuesta = asyncio.run(servicio.preguntar("¿Cuánto me deben?", '{"fiados_por_cobrar": "132.50"}'))
    assert "130" not in respuesta.texto and "131" not in respuesta.texto
    assert respuesta.modelo == servicio.MODELO_VERIFICADOR
    assert respuesta.acciones[0]["pantalla"] == "caja"


def test_un_404_intermitente_se_reintenta_en_el_mismo_modelo(monkeypatch):
    # nemotron-3.5-bolt-e4b devolvió 404 en 1 de cada 3 llamadas (2026-11-01)
    import asyncio

    import httpx

    from ia import servicio

    pedido = httpx.Request("POST", "http://x")
    error = httpx.HTTPStatusError("404", request=pedido, response=httpx.Response(404, request=pedido))
    llamadas = _falsear_modelos(monkeypatch, {"inestable": [error, "Listo."]})
    assert asyncio.run(servicio.preguntar("hola", "{}")).texto == "Listo."
    assert llamadas == ["inestable", "inestable"]


def test_la_llave_invalida_no_se_reintenta(monkeypatch):
    import asyncio

    import httpx

    from ia import servicio

    pedido = httpx.Request("POST", "http://x")
    error = httpx.HTTPStatusError("401", request=pedido, response=httpx.Response(401, request=pedido))
    llamadas = _falsear_modelos(monkeypatch, {"modelo": [error]})
    with pytest.raises(servicio.AsistenteNoDisponible):
        asyncio.run(servicio.preguntar("hola", "{}"))
    assert llamadas == ["modelo"]


def test_la_accion_pegada_al_final_de_la_frase_no_se_muestra():
    from ia.acciones import extraer

    texto, acciones = extraer("Sra. Flora debe 45.00. ACCION: ir_a fiados")
    assert texto == "Sra. Flora debe 45.00."
    assert acciones[0]["pantalla"] == "fiados"


def test_el_modelo_sabe_que_dia_es_y_que_pedido_se_atraso(cliente, cabeceras_demo, modelo):
    from fechas import dia_peruano

    preguntar(cliente, cabeceras_demo, "¿Qué pedido está atrasado?")
    contexto = json.loads(modelo["llamadas"][0]["contexto"])
    assert contexto["hoy"] == dia_peruano().isoformat()
    assert [p["atrasado"] for p in contexto["pedidos_por_llegar"]] == [True, False, False]
    # Identificadores internos no salen hacia el proveedor
    assert "uuid" not in contexto["ordenes_activas"][0] and "id" not in contexto["pedidos_por_llegar"][0]


def test_abstenerse_no_es_equivocarse_pero_un_monto_falso_si():
    from ia.verificar import es_correcta

    assert es_correcta("Tendrás S/ 165 en total.")
    assert es_correcta("Vendiste S/ 120.00 y Cliente 1 debe S/ 45.00. No puedo calcular el total.")
    assert not es_correcta("Tendrás S/ 75.")
    assert not es_correcta("S/ 165 " + "x" * 700)  # acierta, pero demasiado largo para el puesto


# ---- Dataset para fine-tuning (D-20) ----

def _fila_de_registro(id_, respuesta, modelo="m", contexto='{"deuda": "45.00"}'):
    mensajes = [
        {"role": "system", "content": contexto},
        {"role": "user", "content": "¿Cuánto debe Cliente 1?"},
        {"role": "assistant", "content": respuesta},
    ]
    return json.dumps({"tipo": "intercambio", "id": id_, "modelo": modelo, "mensajes": mensajes})


def test_el_dataset_solo_toma_lo_util_y_descarta_errores(monkeypatch, tmp_path):
    import rutas
    from ia import dataset
    from ia.servicio import MODELO_VERIFICADOR

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    valorar = lambda id_, util: json.dumps({"tipo": "valoracion", "id": id_, "util": util})  # noqa: E731
    lineas = [
        _fila_de_registro("bueno", "Cliente 1 debe S/ 45.00."),
        _fila_de_registro("repetido", "Cliente 1 debe S/ 45.00."),
        _fila_de_registro("sin-valorar", "Cliente 1 debe S/ 45.00, ya."),
        _fila_de_registro("no-sirvio", "Cliente 1 debe 45.00 soles."),
        _fila_de_registro("cambio-de-opinion", "Debe S/ 45.00."),
        _fila_de_registro("borrador", "Here's a thinking process:\n1. Analyze"),
        _fila_de_registro("cifra-falsa", "Cliente 1 debe S/ 99.00."),
        _fila_de_registro("respaldo", "No tengo esa cifra.", modelo=MODELO_VERIFICADOR),
        valorar("bueno", True), valorar("repetido", True), valorar("no-sirvio", False),
        valorar("cambio-de-opinion", True), valorar("cambio-de-opinion", False),
        valorar("borrador", True), valorar("cifra-falsa", True), valorar("respaldo", True),
    ]
    (tmp_path / "ia_registro_demo.jsonl").write_text("\n".join(lineas), encoding="utf-8")
    ejemplos = dataset.armar("demo")
    assert [e["messages"][-1]["content"] for e in ejemplos] == ["Cliente 1 debe S/ 45.00."]


def test_el_dataset_de_un_proyecto_sin_registro_esta_vacio(monkeypatch, tmp_path):
    import rutas
    from ia import dataset

    monkeypatch.setattr(rutas, "directorio_datos", lambda: tmp_path)
    assert dataset.armar("demo") == []
