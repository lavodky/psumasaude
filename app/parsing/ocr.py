import os
import io
import datetime as dt
from PIL import Image
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from werkzeug.utils import secure_filename
from .. import config

# Aponta tesseract (se necessário no Windows)
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

def _dump_text_file(txt: str, prefix: str = "pdf", original_name: str | None = None) -> str | None:
    """
    Salva texto extraído em um .txt dentro de TEXT_DUMP_DIR para auditoria/depuração.
    """
    try:
        os.makedirs(config.TEXT_DUMP_DIR, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        base = secure_filename(original_name or "document")
        path = os.path.join(config.TEXT_DUMP_DIR, f"{prefix}-{base}-{stamp}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt or "")
        return path
    except Exception:
        return None

def extract_text_from_image_bytes(b: bytes) -> str:
    img = Image.open(io.BytesIO(b))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) < 1800:
        img = img.resize((w*2, h*2), Image.LANCZOS)
    gray = img.convert("L")
    bw = gray.point(lambda p: 255 if p > 200 else (0 if p < 140 else p))
    config_str = "--oem 3 --psm 6"
    try:
        txt = pytesseract.image_to_string(bw, lang=config.OCR_LANGS, config=config_str)
        if len((txt or "").strip()) < 40:
            txt = pytesseract.image_to_string(bw, lang=config.OCR_LANGS, config="--oem 3 --psm 4")
    except Exception:
        txt = pytesseract.image_to_string(bw, lang=config.OCR_LANGS)
    return txt or ""

def extract_text_from_pdf_bytes(b: bytes, src_name: str | None = None) -> str:
    text_pages = []
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            text_pages.append(t)
    joined = "\n".join(text_pages).strip()
    method = "pdfplumber"

    if len(joined) < 100:
        kwargs = {"dpi": 300}
        if config.POPPLER_PATH:
            kwargs["poppler_path"] = config.POPPLER_PATH
        imgs = convert_from_bytes(b, **kwargs)
        ocr_txt = []
        for im in imgs:
            ocr_txt.append(pytesseract.image_to_string(im, lang=config.OCR_LANGS))
        joined = "\n".join(ocr_txt)
        method = "ocr"

    _dump_text_file(joined, prefix=f"pdftext-{method}", original_name=src_name)
    return joined or ""

def extract_text_from_upload(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    data = file_storage.read()
    file_storage.stream.seek(0)
    if ext == ".pdf":
        return extract_text_from_pdf_bytes(data, filename)
    elif ext in {".png", ".jpg", ".jpeg"}:
        return extract_text_from_image_bytes(data)
    else:
        raise ValueError("Formato não suportado. Envie PDF/JPG/PNG.")
