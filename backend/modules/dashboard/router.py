"""Router del Dashboard / Caja Diaria.

Demo 1: devuelve datos ficticios coherentes con los del frontend para
demostrar el contrato del API. En demos siguientes agregará las cifras
reales desde las tablas de Ventas y Compras (lee de otros módulos pero no
bloquea su funcionamiento).
"""

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter

from fechas import dia_peruano

from .schemas import OrdenActivaResumen, PedidoPorLlegar, ResumenDashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=ResumenDashboard)
def obtener_resumen() -> ResumenDashboard:
    """Resumen del día actual y proyección del día siguiente."""
    # El día del vendedor es el de Lima, no el del reloj del servidor
    hoy = dia_peruano()
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
