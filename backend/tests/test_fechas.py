"""Las fechas guardadas deben volver siempre con zona horaria (UTC).

SQLite no almacena la zona por su cuenta: sin el tipo FechaHoraUTC las fechas
volverían "ingenuas" y compararlas con fechas con zona rompe al sincronizar.
"""

from datetime import datetime, timezone
from decimal import Decimal

from database import Base, SesionLocal, engine
from modules.compras.models import Proveedor
from modules.ventas.models import TipoVenta, Venta


def test_fechas_vuelven_con_zona_utc():
    Base.metadata.create_all(bind=engine)
    sesion = SesionLocal()
    try:
        venta = Venta(tipo=TipoVenta.VENTA_RAPIDA, monto_total=Decimal("5.00"))
        proveedor = Proveedor(nombre="Distribuidora de prueba")
        sesion.add_all([venta, proveedor])
        sesion.commit()
        sesion.expire_all()

        venta_leida = sesion.query(Venta).first()
        proveedor_leido = sesion.query(Proveedor).first()

        assert venta_leida.abierta_en.tzinfo is not None
        assert venta_leida.abierta_en.utcoffset().total_seconds() == 0
        assert proveedor_leido.creado_en.tzinfo is not None

        # Comparar con una fecha con zona no debe lanzar TypeError
        assert venta_leida.abierta_en <= datetime.now(timezone.utc)
    finally:
        sesion.rollback()
        sesion.close()
