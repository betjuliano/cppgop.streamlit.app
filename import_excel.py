import pandas as pd
import sqlite3
import datetime
import os

def import_alunos_from_excel(excel_file_path):
    """
    Importa alunos do arquivo Excel para o banco de dados.
    
    Args:
        excel_file_path: Caminho para o arquivo Excel
        
    Returns:
        dict: Estatísticas da importação (total, importados, ignorados)
    """
    # Ler o arquivo Excel
    df = pd.read_excel(excel_file_path, header=None)
    
    # Encontrar a linha do cabeçalho (que contém "Matrícula", "Nome", etc.)
    header_row = None
    for i, row in df.iterrows():
        if row[0] == "Matrícula":
            header_row = i
            break
    
    if header_row is None:
        return {"error": "Formato de arquivo inválido. Cabeçalho não encontrado."}
    
    # Extrair os dados a partir da linha após o cabeçalho
    data_df = df.iloc[header_row+1:].copy()
    data_df.columns = df.iloc[header_row]
    
    # Remover linhas sem nome (provavelmente vazias)
    data_df = data_df[data_df["Nome"].notna()]
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('ppgop.db')
    cursor = conn.cursor()
    
    # Estatísticas
    stats = {
        "total": len(data_df),
        "importados": 0,
        "ignorados": 0
    }
    
    # Inserir cada aluno no banco de dados
    for _, row in data_df.iterrows():
        try:
            # Verificar se o aluno já existe (pelo email)
            cursor.execute("SELECT id FROM alunos WHERE email = ?", (row["E-mail"],))
            existing = cursor.fetchone()
            
            if existing:
                stats["ignorados"] += 1
                continue
            
            # Formatar datas
            data_ingresso = pd.to_datetime(row["Ingresso"]).strftime('%Y-%m-%d') if pd.notna(row["Ingresso"]) else None
            prazo_defesa_projeto = pd.to_datetime(row["Prazo defesa do Projeto"]).strftime('%Y-%m-%d') if pd.notna(row["Prazo defesa do Projeto"]) else None
            prazo_defesa_tese = pd.to_datetime(row["Prazo para Defesa da Tese"]).strftime('%Y-%m-%d') if pd.notna(row["Prazo para Defesa da Tese"]) else None
            
            # Inserir aluno
            cursor.execute("""
            INSERT INTO alunos (
                matricula, nome, email, orientador, linha_pesquisa, 
                data_ingresso, prazo_defesa_projeto, prazo_defesa_tese
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Matrícula"] if pd.notna(row["Matrícula"]) else None,
                row["Nome"],
                row["E-mail"],
                row["Orientador(a)"] if pd.notna(row["Orientador(a)"]) else None,
                row["Linha de Pesquisa"] if pd.notna(row["Linha de Pesquisa"]) else None,
                data_ingresso,
                prazo_defesa_projeto,
                prazo_defesa_tese
            ))
            
            stats["importados"] += 1
            
        except Exception as e:
            print(f"Erro ao importar aluno {row['Nome']}: {str(e)}")
            stats["ignorados"] += 1
    
    # Commit e fechar conexão
    conn.commit()
    conn.close()
    
    return stats

if __name__ == "__main__":
    # Teste de importação
    excel_path = "/home/ubuntu/upload/Controle discentes Doutorado.xlsx"
    if os.path.exists(excel_path):
        stats = import_alunos_from_excel(excel_path)
        print(f"Importação concluída: {stats}")
    else:
        print(f"Arquivo não encontrado: {excel_path}")
