from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import database
import models
import req_res_models

router = APIRouter(prefix="/cajeros", tags=["Cajeros"])


# Tiene que declararse antes de /{id}; si no, FastAPI interpreta "count" como un id.
@router.get("/count")
def get_cajeros_count(db: Session = Depends(database.get_db)):
    return db.query(models.Cajero).count()


@router.get("/{id}", response_model=req_res_models.CajeroResponse)
def get_cajero(id: str, db: Session = Depends(database.get_db)):
    cajero = db.get(models.Cajero, id)
    if not cajero:
        raise HTTPException(status_code=404, detail="Cajero no encontrado.")
    return cajero


@router.post("/", response_model=req_res_models.CajeroResponse)
def create_cajero(cajero: req_res_models.CajeroCreate, db: Session = Depends(database.get_db)):
    nuevo_cajero = models.Cajero(**cajero.model_dump())
    db.add(nuevo_cajero)
    db.commit()
    db.refresh(nuevo_cajero)
    return nuevo_cajero


@router.put("/{id}", response_model=req_res_models.CajeroResponse)
def update_cajero(id: str, cajero: req_res_models.CajeroCreate, db: Session = Depends(database.get_db)):
    db_cajero = db.get(models.Cajero, id)
    if not db_cajero:
        raise HTTPException(status_code=404, detail="Este cajero no existe.")
    for field, value in cajero.model_dump().items():
        setattr(db_cajero, field, value)
    db.commit()
    db.refresh(db_cajero)
    return db_cajero


@router.delete("/{id}")
def delete_cajero(id: str, db: Session = Depends(database.get_db)):
    db_cajero = db.get(models.Cajero, id)
    if not db_cajero:
        raise HTTPException(status_code=404, detail="Este cajero no existe.")
    db.delete(db_cajero)
    db.commit()
    return {"message": "Cajero eliminado."}


@router.get("/", response_model=List[req_res_models.CajeroResponse])
def get_all_cajero(skip: int = 0, limit: int = 30, db: Session = Depends(database.get_db)):
    return db.query(models.Cajero).order_by(models.Cajero.id).offset(skip).limit(limit).all()
