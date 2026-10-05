from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from endpoints import anomalias_clientes, anomalias_transacciones, cajeros, clientes, estadisticas, tipos_transacciones, transacciones

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Transacciones bancarias")

# El front se sirve con Live Server (puerto 5500), que es otro origen distinto al de la API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Agregue '/docs' al final del enlace para ingresar a la API de transacciones bancarias."}


app.include_router(cajeros.router)
app.include_router(clientes.router)
app.include_router(transacciones.router)
app.include_router(tipos_transacciones.router)
app.include_router(anomalias_transacciones.router)
app.include_router(anomalias_clientes.router)
app.include_router(estadisticas.router)
