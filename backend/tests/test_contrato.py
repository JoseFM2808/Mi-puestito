"""El contrato que lee el frontend (frontend/src/api/openapi.json) debe ser el
del API real. Si falla: `cd backend && python exportar_openapi.py` y revisar
que `frontend/src/api/contrato.ts` siga coincidiendo (su test lo dice)."""

import exportar_openapi


def test_el_contrato_del_frontend_esta_al_dia():
    guardado = exportar_openapi.DESTINO.read_text(encoding="utf-8")
    assert guardado == exportar_openapi.texto_del_contrato(), (
        "El API cambió: ejecuta `python exportar_openapi.py` en backend/"
    )
