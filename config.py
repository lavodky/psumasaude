import os

APP_TITLE = os.getenv("APP_TITLE", "Hemograma + Bioquímica — Registro & Gráfico")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_SUPER_SECRET")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "teste")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# OCR / PDF
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"D:\tesseract\tesseract.exe")
POPPLER_PATH = os.getenv("POPPLER_PATH", None)
OCR_LANGS = os.getenv("OCR_LANGS", "por+eng")

# Onde salvar os dumps de texto extraído
TEXT_DUMP_DIR = os.getenv("TEXT_DUMP_DIR", os.path.join(os.getcwd(), "pdf_text_dumps"))
