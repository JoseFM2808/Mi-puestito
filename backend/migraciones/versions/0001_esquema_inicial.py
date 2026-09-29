"""Esquema inicial: exactamente el que creaba create_all en la Demo 1 (commit ae4866c).

Las bases creadas antes de Alembic se marcan en esta revisión sin ejecutarla
(migraciones/ejecutar.py). Tipos SQLAlchemy genéricos: una migración nunca
importa tipos de la app, que pueden cambiar después.

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('clientes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('telefono', sa.String(length=20), nullable=True),
    sa.Column('limite_credito', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_clientes_nombre'), ['nombre'], unique=False)

    op.create_table('proveedores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('empresa', sa.String(length=120), nullable=True),
    sa.Column('ruc', sa.String(length=11), nullable=True),
    sa.Column('telefono', sa.String(length=20), nullable=True),
    sa.Column('categoria', sa.String(length=80), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ruc')
    )
    with op.batch_alter_table('proveedores', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_proveedores_empresa'), ['empresa'], unique=False)
        batch_op.create_index(batch_op.f('ix_proveedores_nombre'), ['nombre'], unique=False)

    op.create_table('ordenes_compra',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('proveedor_id', sa.Integer(), nullable=False),
    sa.Column('estado', sa.Enum('borrador', 'pendiente', 'en_camino', 'recibida', 'cerrada', name='estadoordencompra', native_enum=False), nullable=False),
    sa.Column('fecha_estimada_llegada', sa.Date(), nullable=True),
    sa.Column('monto_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('monto_real', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('notas', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ordenes_compra', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ordenes_compra_proveedor_id'), ['proveedor_id'], unique=False)
        batch_op.create_index('ix_ordenes_estado_llegada', ['estado', 'fecha_estimada_llegada'], unique=False)

    op.create_table('ventas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('orden_activa', 'fiado', 'venta_rapida', name='tipoventa', native_enum=False), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=True),
    sa.Column('nombre_orden', sa.String(length=120), nullable=True),
    sa.Column('estado', sa.Enum('abierta', 'pagada_cerrada', 'pendiente_formalizar', name='estadoventa', native_enum=False), nullable=False),
    sa.Column('monto_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('metodo_pago', sa.Enum('efectivo', 'yape_plin', name='metodopago', native_enum=False), nullable=True),
    sa.Column('abierta_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('cerrada_en', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("tipo != 'fiado' OR cliente_id IS NOT NULL", name='ck_fiado_requiere_cliente'),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ventas', schema=None) as batch_op:
        batch_op.create_index('ix_ventas_estado_abierta_en', ['estado', 'abierta_en'], unique=False)
        batch_op.create_index('ix_ventas_tipo_cliente', ['tipo', 'cliente_id'], unique=False)

    op.create_table('items_orden_compra',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('orden_compra_id', sa.Integer(), nullable=False),
    sa.Column('nombre_producto', sa.String(length=120), nullable=False),
    sa.Column('cantidad', sa.String(length=60), nullable=True),
    sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('estado_recepcion', sa.Enum('pendiente', 'recibido', 'no_recibido', 'cambiado', name='estadorecepcion', native_enum=False), nullable=False),
    sa.Column('producto_sustituto', sa.String(length=120), nullable=True),
    sa.Column('monto_sustituto', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['orden_compra_id'], ['ordenes_compra.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('items_orden_compra', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_items_orden_compra_orden_compra_id'), ['orden_compra_id'], unique=False)

    op.create_table('items_venta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('venta_id', sa.Integer(), nullable=False),
    sa.Column('nombre_producto', sa.String(length=120), nullable=False),
    sa.Column('cantidad', sa.String(length=60), nullable=True),
    sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('items_venta', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_items_venta_venta_id'), ['venta_id'], unique=False)

    op.create_table('pagos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('venta_id', sa.Integer(), nullable=True),
    sa.Column('cliente_id', sa.Integer(), nullable=True),
    sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('metodo_pago', sa.Enum('efectivo', 'yape_plin', name='metodopago', native_enum=False), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('venta_id IS NOT NULL OR cliente_id IS NOT NULL', name='ck_pago_tiene_destino'),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pagos_cliente_id'), ['cliente_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pagos_venta_id'), ['venta_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pagos_venta_id'))
        batch_op.drop_index(batch_op.f('ix_pagos_cliente_id'))

    op.drop_table('pagos')
    with op.batch_alter_table('items_venta', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_items_venta_venta_id'))

    op.drop_table('items_venta')
    with op.batch_alter_table('items_orden_compra', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_items_orden_compra_orden_compra_id'))

    op.drop_table('items_orden_compra')
    with op.batch_alter_table('ventas', schema=None) as batch_op:
        batch_op.drop_index('ix_ventas_tipo_cliente')
        batch_op.drop_index('ix_ventas_estado_abierta_en')

    op.drop_table('ventas')
    with op.batch_alter_table('ordenes_compra', schema=None) as batch_op:
        batch_op.drop_index('ix_ordenes_estado_llegada')
        batch_op.drop_index(batch_op.f('ix_ordenes_compra_proveedor_id'))

    op.drop_table('ordenes_compra')
    with op.batch_alter_table('proveedores', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proveedores_nombre'))
        batch_op.drop_index(batch_op.f('ix_proveedores_empresa'))

    op.drop_table('proveedores')
    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_clientes_nombre'))

    op.drop_table('clientes')
