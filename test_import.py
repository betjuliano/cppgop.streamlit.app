import sys
sys.path.append('/home/ubuntu/streamlit_app')

from streamlit_app import init_db, import_alunos_from_excel

# Garante que o banco de dados está limpo e com a estrutura correta
print("Inicializando o banco de dados...")
init_db()

# Caminho para o arquivo Excel
excel_file_path = '/home/ubuntu/upload/Controle discentes Doutorado.xlsx'

print(f"Iniciando a importação do arquivo: {excel_file_path}")
# Chama a função de importação passando o caminho do arquivo
stats = import_alunos_from_excel(excel_file_path)

print("\n--- Resultado da Importação ---")
print(f"Total de linhas no arquivo: {stats['total']}")
print(f"Alunos importados com sucesso: {stats['importados']}")
print(f"Registros ignorados/com erro: {stats['ignorados']}")

if stats['erros']:
    print("\n--- Detalhes dos Erros/Alertas ---")
    for erro in stats['erros']:
        print(f"- {erro}")
else:
    print("\nNenhum erro ou alerta durante a importação.")

print("\nTeste de importação concluído.")

