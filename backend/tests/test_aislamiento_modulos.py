"""El fallo de un módulo no debe derribar a los demás (regla de AGENTS.md)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def app_con_ventas_rota(monkeypatch):
    """Monta la aplicación simulando que el módulo Ventas no puede importarse."""
    importar_real = main.importlib.import_module

    def importar(nombre, *args, **kwargs):
        if nombre.startswith("modules.ventas"):
            raise ImportError("columna inexistente en el modelo")
        return importar_real(nombre, *args, **kwargs)

    monkeypatch.setattr(main.importlib, "import_module", importar)
    monkeypatch.setattr(main, "modulos_degradados", {})

    app = FastAPI()
    main.cargar_modulos(app)
    return app


def test_un_modulo_roto_no_tumba_a_los_demas(app_con_ventas_rota):
    from seguridad import crear_token

    cliente = TestClient(app_con_ventas_rota)
    cabeceras = {"Authorization": f"Bearer {crear_token('demo')}"}

    # Ventas cayó: sus rutas no existen...
    assert cliente.get("/api/ventas/", headers=cabeceras).status_code == 404
    # ...pero Compras y el Dashboard siguen respondiendo
    assert cliente.get("/api/compras/proveedores", headers=cabeceras).status_code == 200
    assert cliente.get("/api/dashboard/resumen", headers=cabeceras).status_code == 200


def test_el_modulo_caido_queda_registrado(app_con_ventas_rota):
    assert "ventas" in main.modulos_degradados
    assert "compras" not in main.modulos_degradados
