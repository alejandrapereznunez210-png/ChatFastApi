from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from typing import Dict
import json

app = FastAPI()




class Alumno(BaseModel):
    nombre: str
    edad: int
    carrera: str
    semestre: int


alumnos = [
    {
        "id": 1,
        "nombre": "Sergio V",
        "edad": 20,
        "carrera": "Ingeniería en IA",
        "semestre": 3
    },
    {
        "id": 2,
        "nombre": "Carlos López",
        "edad": 21,
        "carrera": "Ingeniería Informática",
        "semestre": 5
    }
]




class AdministradorConexiones:

    def __init__(self):
        self.conexiones: Dict[WebSocket, str] = {}

    async def conectar(self, websocket: WebSocket, nombre: str):
        await websocket.accept()
        self.conexiones[websocket] = nombre

    def desconectar(self, websocket: WebSocket):
        if websocket in self.conexiones:
            del self.conexiones[websocket]

    async def enviar_personal(self, mensaje: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(mensaje, ensure_ascii=False))

    async def difundir(self, mensaje: dict):
        desconectados = []

        for conexion in list(self.conexiones.keys()):
            try:
                await conexion.send_text(
                    json.dumps(mensaje, ensure_ascii=False)
                )
            except Exception:
                desconectados.append(conexion)

        for conexion in desconectados:
            self.desconectar(conexion)

    async def actualizar_usuarios(self):
        mensaje = {
            "tipo": "usuarios",
            "usuarios": sorted(set(self.conexiones.values()))
        }

        await self.difundir(mensaje)


administrador = AdministradorConexiones()




@app.get("/")
def read_root():
    ruta_cliente = Path(__file__).resolve().parent / "cliente.html"

    if ruta_cliente.exists():
        return FileResponse(ruta_cliente)

    return {"mensaje": "Servidor FastAPI funcionando"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}


@app.get("/alumnos")
def obtener_alumnos():
    return alumnos


@app.get("/alumnos/{alumno_id}")
def obtener_alumno(alumno_id: int):

    for alumno in alumnos:
        if alumno["id"] == alumno_id:
            return alumno

    return {"mensaje": "Alumno no encontrado"}


@app.post("/alumnos")
def crear_alumno(alumno: Alumno):

    nuevo_id = max(
        (alumno["id"] for alumno in alumnos),
        default=0
    ) + 1

    nuevo_alumno = {
        "id": nuevo_id,
        "nombre": alumno.nombre,
        "edad": alumno.edad,
        "carrera": alumno.carrera,
        "semestre": alumno.semestre
    }

    alumnos.append(nuevo_alumno)

    return nuevo_alumno




@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    nombre = ""

    try:
       
        await websocket.accept()

        nombre = (await websocket.receive_text()).strip()

        if not nombre:
            await websocket.send_text(json.dumps({
                "tipo": "error",
                "mensaje": "Debes ingresar un nombre."
            }, ensure_ascii=False))

            await websocket.close()
            return

        administrador.conexiones[websocket] = nombre

        await administrador.enviar_personal(
            {
                "tipo": "sistema",
                "mensaje": f"Te has conectado al chat como {nombre}."
            },
            websocket
        )

        await administrador.difundir({
            "tipo": "sistema",
            "mensaje": f"{nombre} se ha unido al chat.",
            "fecha": datetime.now().astimezone().isoformat()
        })

       
        await administrador.actualizar_usuarios()

     
        while True:

            contenido = await websocket.receive_text()
            contenido = contenido.strip()

            if not contenido:
                continue

            mensaje = {
                "tipo": "mensaje",
                "nombre": nombre,
                "contenido": contenido,
                "fecha": datetime.now().astimezone().isoformat()
            }

            await administrador.difundir(mensaje)

    except WebSocketDisconnect:
        pass

    except Exception as error:
        print(f"Error en la conexión de {nombre}: {error}")

    finally:
     
        estaba_conectado = websocket in administrador.conexiones

        administrador.desconectar(websocket)

        if estaba_conectado:
            await administrador.difundir({
                "tipo": "sistema",
                "mensaje": f"{nombre} ha salido del chat.",
                "fecha": datetime.now().astimezone().isoformat()
            })

            await administrador.actualizar_usuarios()