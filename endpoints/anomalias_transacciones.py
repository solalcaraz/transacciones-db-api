from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import database
import deteccion
import models
import req_res_models
from endpoints.anomalias_clientes import obtener_df_transacciones

router = APIRouter(prefix="/anomalias", tags=["Anomalías"])


@router.get("/cantidad_transacciones_sospechosas", response_model=int)
def contar_transacciones_sospechosas(db: Session = Depends(database.get_db)):
    _, sospechosas = deteccion.detectar_anomalias_transacciones(obtener_df_transacciones(db))
    return len(sospechosas)


@router.get("/transacciones_por_cliente/{id_cliente}", response_model=List[req_res_models.TransaccionSospechosaResponse])
def get_transacciones_por_cliente(id_cliente: str, db: Session = Depends(database.get_db)):
    """Devuelve todas las transacciones del cliente, analizadas solo contra su propio historial, con las sospechosas primero."""
    transacciones = db.query(models.Transaccion).filter(models.Transaccion.id_cliente == id_cliente).all()
    if not transacciones:
        raise HTTPException(status_code=404, detail=f"No se encontraron transacciones para el cliente {id_cliente}")

    cliente = db.get(models.Cliente, id_cliente)
    nombre = cliente.nombre if cliente else "Desconocido"
    apellido = cliente.apellido if cliente else "Desconocido"

    # LOF necesita al menos un vecino, así que con una sola transacción no hay con qué compararla.
    if len(transacciones) < 2:
        datos = req_res_models.TransaccionResponse.model_validate(transacciones[0]).model_dump()
        return [req_res_models.TransaccionSospechosaResponse(
            **datos, nombre=nombre, apellido=apellido, sospechosa_por=[], score_anomalia=0.0,
        )]

    df = deteccion.transacciones_a_df(transacciones)
    monto_promedio, monto_std = df["monto"].mean(), df["monto"].std()
    df, sospechosas = deteccion.detectar_anomalias_transacciones(df)
    ids_sospechosas = set(sospechosas["id"])

    resultados = []
    for _, row in df.iterrows():
        es_sospechosa = row["id"] in ids_sospechosas
        resultados.append(req_res_models.TransaccionSospechosaResponse(
            id=row["id"],
            id_cliente=row["id_cliente"],
            id_cajero=row["id_cajero"],
            id_tipo_transaccion=row["id_tipo_transaccion"],
            monto=row["monto"],
            fecha_hora=row["fecha_hora"],
            nombre=nombre,
            apellido=apellido,
            sospechosa_por=deteccion.motivos_transaccion(row, monto_promedio, monto_std) if es_sospechosa else [],
            score_anomalia=float(row["score_anomalia"]),
        ))

    resultados.sort(key=lambda x: x.score_anomalia, reverse=True)
    return resultados
