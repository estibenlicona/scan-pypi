from main import run_snyk_analysis

# Test con una librería simple
if __name__ == "__main__":
    try:
        print("Iniciando análisis de prueba con requests...")
        run_snyk_analysis(["requests"])
        print("Análisis completado exitosamente!")
    except Exception as e:
        print(f"Error en el análisis: {e}")
