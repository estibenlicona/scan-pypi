import os
from datetime import timedelta
import datetime as dt
from typing import List
from dotenv import load_dotenv
from models import PackageInfo

load_dotenv()

def filter_maintained_packages(pypi_infos: List[PackageInfo]) -> List[PackageInfo]:
    """
    Filtra paquetes publicados en los últimos N años (configurable por .env).
    
    Args:
        pypi_infos: Lista de objetos PackageInfo con información de PyPI por paquete y versión.
        
    Returns:
        Lista de paquetes mantenidos (filtrados por fecha de publicación).
    """
    years = int(os.getenv("MAINTAINED_YEARS", "2"))
    cutoff_date = dt.datetime.now(dt.timezone.utc) - timedelta(days=years*365)
    filtered: List[PackageInfo] = []
    
    for info in pypi_infos:
        upload_time = info.upload_time
        if upload_time:
            try:
                pub_date = dt.datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                # Si pub_date no tiene tzinfo, asume UTC
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=dt.timezone.utc)
                if pub_date >= cutoff_date:
                    filtered.append(info)
            except Exception:
                pass
    return filtered
