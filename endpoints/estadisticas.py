from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import database
import deteccion
import models
from endpoints.anomalias_clientes import obtener_df_transacciones

router = APIRouter(prefix="/estadisticas", tags=["Anomalías"])


@router.get("/", response_model=Dict[str, float])
def get_stats(db: Session = Depends(database.get_db)):
    total_transacciones = db.query(models.Transaccion).count()
    total_clientes = db.query(models.Cliente).count()
    if total_transacciones == 0 or total_clientes == 0:
        raise HTTPException(status_code=404, detail="No hay datos suficientes para calcular estadísticas")

    min_fecha = db.query(func.min(models.Transaccion.fecha_hora)).scalar()
    max_fecha = db.query(func.max(models.Transaccion.fecha_hora)).scalar()
    if not min_fecha or not max_fecha or min_fecha == max_fecha:
        raise HTTPException(status_code=400, detail="No hay suficiente rango temporal para calcular promedio")

    minutos = (max_fecha - min_fecha).total_seconds() / 60
    clientes_sospechosos = deteccion.detectar_clientes_sospechosos(obtener_df_transacciones(db))

    return {
        "total_clientes": total_clientes,
        "porcentaje_clientes_sospechosos": round(len(clientes_sospechosos) / total_clientes * 100, 2),
        "total_transacciones": total_transacciones,
        "promedio_transacciones_por_minuto": round(total_transacciones / minutos, 2),
    }
