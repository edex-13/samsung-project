import pandas as pd

def verificar_datos_completados():
    """Verifica cómo se completaron los datos faltantes"""
    
    try:
        # Verificar archivo de Falabella
        print("🔍 Verificando datos completados en Falabella:")
        df_falabella = pd.read_excel('resultados_falabella_verificado.xlsx')
        
        if 'caracteristicas_extraidas' in df_falabella.columns:
            print(f"✅ Columna 'caracteristicas_extraidas' encontrada")
            print(f"📊 Total de productos: {len(df_falabella)}")
            
            # Mostrar productos con datos completados
            productos_completados = df_falabella[df_falabella['caracteristicas_extraidas'] != "Sin datos extraídos"]
            print(f"🔧 Productos con datos completados: {len(productos_completados)}")
            
            print("\n📋 Ejemplos de datos completados:")
            for idx, row in productos_completados.head(10).iterrows():
                nombre = row['nombre'][:60] + "..." if len(row['nombre']) > 60 else row['nombre']
                caracteristicas = row['caracteristicas_extraidas']
                print(f"   • {nombre}")
                print(f"     Datos completados: {caracteristicas}")
                print()
        
        # Verificar archivo de Éxito
        try:
            print("🔍 Verificando datos completados en Éxito:")
            df_exito = pd.read_excel('resultados_exito_verificado.xlsx')
            
            if 'caracteristicas_extraidas' in df_exito.columns:
                print(f"✅ Columna 'caracteristicas_extraidas' encontrada")
                print(f"📊 Total de productos: {len(df_exito)}")
                
                # Mostrar productos con datos completados
                productos_completados = df_exito[df_exito['caracteristicas_extraidas'] != "Sin datos extraídos"]
                print(f"🔧 Productos con datos completados: {len(productos_completados)}")
                
                print("\n📋 Ejemplos de datos completados:")
                for idx, row in productos_completados.head(10).iterrows():
                    nombre = row['nombre'][:60] + "..." if len(row['nombre']) > 60 else row['nombre']
                    caracteristicas = row['caracteristicas_extraidas']
                    print(f"   • {nombre}")
                    print(f"     Datos completados: {caracteristicas}")
                    print()
                    
        except FileNotFoundError:
            print("⚠️ Archivo de Éxito no encontrado")
        except Exception as e:
            print(f"❌ Error con archivo de Éxito: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    verificar_datos_completados() 