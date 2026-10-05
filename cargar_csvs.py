from datetime import datetime
from decimal import Decimal

import pandas as pd

from database import Base, SessionLocal, engine
from models import Cajero, Cliente, TipoTransaccion, Transaccion

# Carga en la base los CSV ya procesados de data/. Se corre una sola vez, con la base vacía.

Base.metadata.create_all(bind=engine)
db = SessionLocal()

for _, row in pd.read_csv("data/clientes.csv").iterrows():
    db.add(Cliente(
        id=row["id"],
        nombre=row["nombre"],
        apellido=row["apellido"],
        genero=row["genero"],
        fecha_nacimiento=datetime.strptime(row["fecha_nacimiento"], "%Y-%m-%d").date(),
        ocupacion=row["ocupacion"],
        tipo_cuenta=row["tipo_cuenta"],
    ))

for _, row in pd.read_csv("data/cajeros.csv").iterrows():
    db.add(Cajero(
        id=row["id"],
        nombre=row["nombre"],
        ciudad=row["ciudad"],
        provincia=row["provincia"],
        pais=row["pais"],
    ))

for _, row in pd.read_csv("data/tipos_transacciones.csv").iterrows():
    db.add(TipoTransaccion(nombre=row["nombre"]))

for _, row in pd.read_csv("data/transacciones.csv").iterrows():
    db.add(Transaccion(
        id=row["id"],
        fecha_hora=datetime.strptime(row["fecha_hora"], "%Y-%m-%d %H:%M:%S"),
        id_cliente=row["id_cliente"],
        id_cajero=row["id_cajero"],
        id_tipo_transaccion=row["id_tipo_transaccion"],
        # Pasar por str evita arrastrar el error de redondeo del float al Decimal.
        monto=Decimal(str(row["monto"])),
    ))

db.commit()
db.close()

print("Datos cargados correctamente")
