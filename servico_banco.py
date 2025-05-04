from database import conectar

def salvar_trabalho(titulo, tema, autor, texto, pdf=True, docx=True):
    conn = conectar()
    if not conn:
        print("❌ Conexão com o banco falhou.")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trabalhos (titulo, tema, autor, texto_gerado, gerado_pdf, gerado_docx)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (titulo, tema, autor, texto, pdf, docx))
        conn.commit()
        print("✅ Trabalho salvo com sucesso.")
        return True
    except Exception as e:
        print("❌ Erro ao salvar no banco:", e)
        return False
    finally:
        conn.close()

def listar_trabalhos():
    conn = conectar()
    if not conn:
        print("❌ Erro ao conectar para listar trabalhos.")
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, titulo, autor, data_criacao, gerado_pdf, gerado_docx 
                FROM trabalhos 
                ORDER BY data_criacao DESC
            """)
            resultados = cur.fetchall()
            return resultados
    except Exception as e:
        print("❌ Erro ao buscar trabalhos:", e)
        return []
    finally:
        conn.close()
