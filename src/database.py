import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# 1. Carrega as variáveis do ficheiro .env
load_dotenv()


# 2. Lê as configurações do banco
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# 3. Monta o endereço de conexão
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)


# 4. Cria o engine de conexão
engine = create_engine(DATABASE_URL)


# 5. Função para testar a conexão
def testar_conexao():
    try:
        with engine.connect() as connection:

            resultado = connection.execute(
                text("SELECT current_database(), current_user;")
            )

            linha = resultado.fetchone()

            print("Conexao realizada com sucesso!")
            print(f"Database: {linha[0]}")
            print(f"Usuario: {linha[1]}")

    except Exception as erro:
        print("Erro ao conectar ao PostgreSQL:")
        print(erro)


# 6. Executa o teste quando este ficheiro for executado diretamente
if __name__ == "__main__":
    testar_conexao()