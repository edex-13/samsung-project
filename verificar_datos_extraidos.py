import pandas as pd

def verificar_datos_extraidos():
    """Verifica los datos extraídos de los nombres de productos"""
    
    try:
        # Verificar archivo de Falabella
        print("🔍 Verificando datos extraídos de Falabella:")
        df_falabella = pd.read_excel('resultados_falabella_verificado.xlsx')
        
        if 'datos_extraidos_nombre' in df_falabella.columns:
            print(f"✅ Columna 'datos_extraidos_nombre' encontrada")
            print(f"📊 Total de productos: {len(df_falabella)}")
            
            # Mostrar ejemplos de datos extraídos
            print("\n📋 Ejemplos de datos extraídos:")
            for idx, row in df_falabella.head(10).iterrows():
                nombre = row['nombre'][:80] + "..." if len(row['nombre']) > 80 else row['nombre']
                datos = row['datos_extraidos_nombre']
                print(f"   • {nombre}")
                print(f"     Datos extraídos: {datos}")
                print()
        
        # Verificar archivo de Éxito si existe
        try:
            print("🔍 Verificando datos extraídos de Éxito:")
            df_exito = pd.read_excel('resultados_exito_verificado.xlsx')
            
            if 'datos_extraidos_nombre' in df_exito.columns:
                print(f"✅ Columna 'datos_extraidos_nombre' encontrada")
                print(f"📊 Total de productos: {len(df_exito)}")
                
                # Mostrar ejemplos de datos extraídos
                print("\n📋 Ejemplos de datos extraídos:")
                for idx, row in df_exito.head(10).iterrows():
                    nombre = row['nombre'][:80] + "..." if len(row['nombre']) > 80 else row['nombre']
                    datos = row['datos_extraidos_nombre']
                    print(f"   • {nombre}")
                    print(f"     Datos extraídos: {datos}")
                    print()
                    
        except FileNotFoundError:
            print("⚠️ Archivo de Éxito no encontrado")
        except Exception as e:
            print(f"❌ Error con archivo de Éxito: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    verificar_datos_extraidos() 