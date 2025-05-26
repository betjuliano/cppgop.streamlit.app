import sys
import os # Import os
sys.path.append('/home/ubuntu/streamlit_app')

from streamlit_app import init_db, import_alunos_from_excel

DB_FILE = 		'/home/ubuntu/streamlit_app/ppgop.db'		 # Define DB path

# Explicitly delete DB file first
if os.path.exists(DB_FILE):
    try:
        os.remove(DB_FILE)
        print(f"Arquivo DB 		{DB_FILE}		 removido explicitamente antes do teste.")
    except OSError as e:
        print(f"Erro ao remover DB explicitamente: {e}")
        sys.exit(1) # Exit if we can		t ensure a clean state

# Garante que o banco de dados está limpo e com a estrutura correta
print("Inicializando o banco de dados...")
init_db() # No need for force_recreate now, as we deleted it above

# Caminho para o arquivo Excel
excel_file_path = 		'/home/ubuntu/upload/Controle discentes Doutorado.xlsx'		

print(f"Iniciando a importação do arquivo: {excel_file_path}")
# Chama a função de importação passando o caminho do arquivo
stats = import_alunos_from_excel(excel_file_path)

print("\n--- Resultado da Importação ---")
print(f"Total de linhas no arquivo: {stats[		'total'		]}")
print(f"Alunos importados com sucesso: {stats[		'importados'		]}")
print(f"Registros ignorados/com erro: {stats[		'ignorados'		]}")

if stats[		'erros'		]:
    print("\n--- Detalhes dos Erros/Alertas ---")
    for erro in stats[		'erros'		]:
        print(f"- {erro}")
else:
    print("\nNenhum erro ou alerta durante a importação.")

print("\nTeste de importação concluído.")

# Add a check to see if data was actually inserted
import sqlite3
try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM alunos")
    count = cursor.fetchone()[0]
    print(f"\nVerificação final: {count} alunos encontrados na tabela.")
    # Check for 'nivel' column data
    if count > 0:
        cursor.execute("SELECT nivel, COUNT(*) FROM alunos GROUP BY nivel")
        nivel_counts = cursor.fetchall()
        print("Contagem por Nível:")
        for nivel, num in nivel_counts:
            print(f"- {nivel if nivel else 		(NULL)		}: {num}")
    conn.close()
except Exception as e:
    print(f"Erro ao verificar dados no banco: {e}")


