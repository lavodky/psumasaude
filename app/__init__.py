# Carrega .env se existir (não é obrigatório)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
