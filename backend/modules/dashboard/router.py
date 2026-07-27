"""Router del Dashboard / Caja Diaria.

Cada proyecto ve su propio resumen (autenticado por token, ver seguridad.py):
- **demo**: la información ficticia de siempre (Restaurante Doña Carmen,
  Sra. Flora, Distribuidora Norte…), fija, para mostrar la app sin arriesgar
  datos reales.
- **anita** (y cualquier proyecto real futuro): arranca en cero. En demos
  siguientes estas cifras se calcularán desde las tablas reales de Ventas y
  Compras de ese proyecto (lee de otros módulos pero no bloquea su
  funcionamiento).
"""

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends

from fechas import dia_peruano
from seguridad import proyecto_autenticado

from .schemas import OrdenActivaResumen, PedidoPorLlegar, ResumenDashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _resumen_demo(hoy) -> ResumenDashboard:
    return ResumenDashboard(
        ventas_hoy=Decimal("485.50"),
        ventas_cerradas=12,
        proyeccion_manana=Decimal("320.00"),
        motivo_proyeccion="Llega pedido de Distribuidora Norte",
        ordenes_activas=[
            OrdenActivaResumen(
                id=1, nombre="Restaurante Doña Carmen", tipo="orden_activa", monto=Decimal("86.00")
            ),
            OrdenActivaResumen(id=2, nombre="Orden 2", tipo="orden_activa", monto=Decimal("23.50")),
            OrdenActivaResumen(
                id=3,
                nombre="Sra. Flora",
                tipo="fiado",
                monto=Decimal("12.00"),
                deuda_cliente=Decimal("45.00"),
            ),
        ],
        fiados_por_cobrar=Decimal("132.50"),
        clientes_con_fiado=4,
        ventas_rapidas_pendientes=3,
        pedidos_por_llegar=[
            PedidoPorLlegar(
                id=1,
                proveedor="Distribuidora Norte",
                fecha_estimada=hoy + timedelta(days=1),
                monto=Decimal("320.00"),
            ),
            PedidoPorLlegar(
                id=2,
                proveedor="Avícola San Pedro",
                fecha_estimada=hoy + timedelta(days=2),
                monto=Decimal("145.00"),
            ),
        ],
    )


def _resumen_vacio() -> ResumenDashboard:
    """Una empresa real que recién empieza: cero en todo, sin datos inventados."""
    return ResumenDashboard(
        ventas_hoy=Decimal("0"),
        ventas_cerradas=0,
        proyeccion_manana=Decimal("0"),
        motivo_proyeccion="Aún no hay pedidos por llegar",
        ordenes_activas=[],
        fiados_por_cobrar=Decimal("0"),
        clientes_con_fiado=0,
        ventas_rapidas_pendientes=0,
        pedidos_por_llegar=[],
    )


@router.get("/resumen", response_model=ResumenDashboard)
def obtener_resumen(proyecto: str = Depends(proyecto_autenticado)) -> ResumenDashboard:
    """Resumen del día actual y proyección del día siguiente."""
    if proyecto == "demo":
        # El día del vendedor es el de Lima, no el del reloj del servidor
        return _resumen_demo(dia_peruano())
    return _resumen_vacio()
