from typing import List

import plotly.express as px
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

import database
import deteccion
import models
import req_res_models

router = APIRouter(prefix="/anomalias", tags=["Anomalías"])


def obtener_df_transacciones(db: Session):
    transacciones = db.query(models.Transaccion).all()
    if not transacciones:
        raise HTTPException(status_code=404, detail="No hay transacciones registradas")
    return deteccion.transacciones_a_df(transacciones)


@router.get("/clientes_sospechosos", response_model=List[req_res_models.ClienteSospechosoResponse])
def get_clientes_sospechosos(db: Session = Depends(database.get_db)):
    sospechosos = deteccion.detectar_clientes_sospechosos(obtener_df_transacciones(db))

    ids = [id_cliente for id_cliente, _ in sospechosos]
    clientes = {c.id: c for c in db.query(models.Cliente).filter(models.Cliente.id.in_(ids))}

    resultados = []
    for id_cliente, motivos in sospechosos:
        cliente = clientes.get(id_cliente)
        resultados.append(req_res_models.ClienteSospechosoResponse(
            id_cliente=id_cliente,
            nombre=cliente.nombre if cliente else "Desconocido",
            apellido=cliente.apellido if cliente else "Desconocido",
            sospechoso_por=motivos,
        ))
    return resultados


@router.get("/graficos/clientes_sospechosos", response_class=HTMLResponse)
def grafico_clientes_sospechosos(db: Session = Depends(database.get_db)):
    transacciones = db.query(models.Transaccion).all()
    if not transacciones:
        return "<h3>No hay transacciones</h3>"

    clientes = deteccion.clasificar_clientes_para_grafico(deteccion.transacciones_a_df(transacciones))
    fig = px.scatter(
        clientes,
        x="monto_promedio",
        y="tiempo_entre_transacciones",
        color=clientes["sospechoso"].map({1: "Normal", -1: "Sospechoso"}),
        hover_data=["id_cliente"],
    )
    # Se devuelve el HTML completo de Plotly para que el front lo inserte sin depender de la librería en Python.
    return fig.to_html(full_html=True)
