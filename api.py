from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from typing import List
import os
import json
from main import run_snyk_analysis_async

app = FastAPI()

REPORT_PATH = os.path.join(os.getcwd(), "consolidated_report.json")

@app.post("/scan/")
async def scan_requirements(libraries: List[str] = Body(..., embed=True)):
    """
    Recibe un array de strings (librerías), las pasa a run_snyk_analysis_async,
    ejecuta el análisis y retorna el reporte consolidado.
    """

    try:
        await run_snyk_analysis_async(libraries)
    except RuntimeError as e:
        return JSONResponse(content={"error": f"Error en análisis: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": f"Error inesperado: {str(e)}"}, status_code=500)

    if os.path.exists(REPORT_PATH):
        try:
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
            return JSONResponse(content=report)
        except Exception as e:
            return JSONResponse(content={"error": f"Error leyendo el reporte: {str(e)}"}, status_code=500)
    return JSONResponse(content={"error": "No se generó el reporte"}, status_code=500)

# Para correr: uvicorn api:app --reload
