import re
from typing import Dict
import unicodedata

# ---------- Normalização de texto/número/unidade ----------

def _normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()

def _has_digit(s: str) -> bool:
    return bool(re.search(r"\d", s or ""))

def _truncate_at_ref_meta_tail(s: str) -> str:
    """
    Corta o texto no início de blocos de referência/metadados comuns.
    """
    pats = [
        r"valores\s+de\s+refer", r"intervalo\s+de\s+refer",
        r"\bcoleta\b", r"\bcoletad?o?\b", r"\bhoras?\b",
        r"\bmaterial\b", r"\bm[ée]todo\b", r"\bsistema\s+automatico\b",
        r"\bparametros\b", r"\bfase\b", r"\bpos[-\s]?menopausa\b",
        r"\bgestantes?\b",
    ]
    cut = len(s or "")
    for p in pats:
        m = re.search(p, s or "", flags=re.I)
        if m:
            cut = min(cut, m.start())
    return (s or "")[:cut]

def _norm_unit(u: str | None) -> str | None:
    if not u:
        return None
    u = u.lower().strip().replace("µ", "u").replace(" ", "")
    u = u.replace("ugdl", "ug/dl").replace("gdl", "g/dl").replace("mgdl", "mg/dl")
    u = u.replace("ngml", "ng/ml").replace("pgml", "pg/ml")
    u = u.replace("miu/ml", "ui/ml").replace("mui/ml", "ui/ml").replace("u/ml", "ui/ml")
    u = u.replace("/mm³", "/mm3").replace("10^6/mm³", "10^6/mm3")
    return u

def _normalize_number(raw: str) -> float | None:
    if raw is None:
        return None
    s = raw.strip()
    has_dot = "." in s
    has_comma = "," in s
    try:
        if has_dot and has_comma:
            last_dot = s.rfind(".")
            last_comma = s.rfind(",")
            if last_comma > last_dot:
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
            return float(s)
        if has_comma:
            if s.count(",") >= 2:
                s = s.replace(",", "")
            else:
                s = s.replace(",", ".")
            return float(s)
        if has_dot:
            if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
                s = s.replace(".", "")
            return float(s)
        return float(s)
    except Exception:
        return None

# ---------- Números com unidade e filtragem de intervalos ----------

_NUM_WITH_UNIT = re.compile(
    r"""(?P<op>[<>≈~])?\s*
        (?P<num>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)
        \s*(?P<unit>
            %|
            g/?d[il]l|mg/?d[il]l|ug/?d[il]l|
            m?ui/?/?ml|u/?ml|ng/?ml|pg/?ml|
            /mm3|10\^6/?mm3|fl|pg|nmol/l
        )?
    """,
    re.I | re.X
)

def _looks_interval(after: str) -> bool:
    return bool(after and re.search(r"\b(a|ate|até|–|-)\b", after, flags=re.I) and _NUM_WITH_UNIT.search(after))

# ---------- Hints de unidade por analito ----------

UNIT_HINTS = {
    "PT": ["g/dl"],
    "A_G": [None],
    "ALB": ["g/dl"],
    "ALB_PCT": ["%"],
    "A1": ["%"], "A2": ["%"], "B1": ["%"], "B2": ["%"], "GAMMA": ["%"],
    "RBC": ["/mm3", "10^6/mm3"], "HGB": ["g/dl"], "HCT": ["%"],
    "MCV": ["fl"], "MCH": ["pg"], "MCHC": ["g/dl"], "RDW": ["%"],
    "WBC": ["/mm3"], "PLT": ["/mm3"], "MPV": ["fl"],
    "TSH": ["ui/ml"], "FT4": ["ng/dl"], "LH": ["ui/ml"], "FSH": ["ui/ml"],
    "PRL": ["ng/ml"], "PROG": ["ng/ml"], "E2": ["pg/ml"], "PTH": ["pg/ml"],
    "INS": ["ui/ml"], "HOMA_IR": [None],
    "CA19_9": ["ui/ml"], "CA15_3": ["ui/ml"], "CA125": ["ui/ml"],
    "B12": ["pg/ml"], "VITD": ["ng/ml"], "CEA": ["ng/ml"],
    "CORT": ["ug/dl"], "C_PEP": ["ng/ml"], "SHBG": ["nmol/l"], "TESTO": ["ng/dl"], "TESTO_FREE": ["ng/dl"],
    "RT3": ["ng/dl"],
    "PCR": ["mg/dl"], "CRE": ["mg/dl"], "URE": ["mg/dl"], "GLU": ["mg/dl"], "CA": ["mg/dl"], "P": ["mg/dl"],
    "AST": ["u/l"], "ALT": ["u/l"], "ALP": ["u/l"], "GGT": ["u/l"], "AML": ["u/l"],
    "FE": ["ug/dl"], "TIBC": ["ug/dl"], "TRF": ["ug/dl"],
    "CT": ["mg/dl"], "TG": ["mg/dl"], "HDL": ["mg/dl"], "VLDL": ["mg/dl"], "LDL": ["mg/dl"],
    "HBA1C": ["%"],
}

# ---------- Sinônimos por analito (para encontrar rótulos no laudo) ----------

ANALYTE_SYNONYMS = {
    "GLU": ["glicose", "glucose", r"\bglu\b"],
    "URE": ["ureia", "uréia", r"\bure\b"],
    "CRE": ["creatinina", r"\bcre\b"],
    "PCR": ["proteina c reativa", "proteína c reativa", r"\bpcr\b"],
    "CA":  [r"\bcalcio\b", "cálcio", "calcio total"],
    "P":   ["fosforo", "fósforo"],
    "AST": ["ast", "tgo", "aspartato aminotransferase"],
    "ALT": ["alt", "tgp", "alanina aminotransferase"],
    "ALP": ["fosfatase alcalina", r"\balp\b", r"\bfa\b"],
    "GGT": ["ggt", "gama glutamil", "gamma glutamil"],
    "AML": ["amilase", "amilase total"],
    "FE":  ["ferro serico", "ferro sérico", r"\bferro\b", r"\bfe\b"],
    "TIBC": ["capacidade total de fixacao do ferro", "capacidade total de ligacao do ferro", r"\btibc\b", r"\bctlf\b"],
    "TRF": ["transferrina", r"\btrf\b"],
    "CT": ["colesterol total", r"\bct\b"],
    "TG": ["triglicerid(e|é)os", r"\btg\b"],
    "HDL": [r"\bhdl\b"],
    "VLDL": [r"\bvldl\b"],
    "LDL": [r"\bldl\b"],
    "ALB": ["albumina", "albúmina"],
    "PT": ["proteinas totais", "proteínas totais"],
    "A_G": ["relacao a/g", "relação a/g", r"\ba/g\b"],
    "ALB_PCT": ["albumina............:", r"% albumina", "albumina %"],
    "A1": [" alfa 1[- ]?globulina", r"alpha[- ]?1"],
    "A2": [" alfa 2[- ]?globulina", r"alpha[- ]?2"],
    "B1": ["beta 1[- ]?globulina"],
    "B2": ["beta 2[- ]?globulina"],
    "GAMMA": ["gama[- ]?globulina", "gamma[- ]?globulin"],
    "HBA1C": ["hemoglobina glicada", r"\ba1c\b", r"\bhba1c\b"],
    "RBC": ["rbc", "hemacias", "hemácias", r"\brbc\b", r"hemacias(?:\s+em\s+milhoes)?", r"hemacias\s*/?\s*gr", r"globulos\s+vermelhos", r"hemácias em milhões"],
    "HGB": ["hgb", r"\bhgb\b", r"hemoglobina\b"],
    "HCT": ["hct", "hematocrito", "hematócrito", r"\bhct\b"],
    "MCV": ["vcm", "mcv", r"\bmcv\b", r"\bvcm\b", r"vol\.?\s*glob\.?\s*medio", r"\bvgm\b"],
    "MCH": ["hcm", "mch", r"\bmch\b", r"\bhcm\b", r"hem\.?\s*glob\.?\s*media", r"\bhgm\b"],
    "MCHC": ["chcm", "mchc", r"\bmchc\b", r"\bchcm\b", r"c\.?\s*h\.?\s*glob\.?\s*media", r"\bchgm\b"],
    "RDW": ["rdw", r"\brdw\b", r"amplitude\s+de\s+distrib.*eritrocito", r"amplitude\s+de\s+distrib.*globulos.*vermelhos"],
    "WBC": ["leucocitos", "leucócitos", r"\bwbc\b", "globulos brancos", "glóbulos brancos"],
    "BAND": ["bastonetes", r"\bbands?\b"],
    "SEG": ["segmentados", "neutrofilos", "neutrófilos"],
    "EOS": ["eosinofilos", "eosinófilos"],
    "BASO": ["basofilos", "basófilos"],
    "LYMPH": ["linfocitos tipicos", "linfócitos tipicos", "linfocitos", "linfócitos", r"\blymph\b"],
    "LYMPH_ATYP": ["linfocitos atipicos", "linfócitos atípicos"],
    "MONO": ["monocitos", "monócitos"],
    "PLT": ["plaquetas", r"\bplt\b"],
    "MPV": ["vpm", "mpv", "volume plaquetario medio", "volume plaquetário médio"],
    "E2": ["estradiol", r"\be2\b"],
    "FSH": ["fsh"],
    "INS": ["insulina"],
    "HOMA_IR": ["homa[- ]?ir", "indice homa", "índice homa"],
    "LH": ["lh", "hormonio luteinizante"],
    "PTH": ["paratormonio", "paratormônio", r"\bpth\b"],
    "PROG": ["progesterona"],
    "PRL": ["prolactina", r"\bprl\b"],
    "TESTO": ["testosterona total"],
    "TSH": ["tsh"],
    "FT4": ["t4 livre", r"\bft4\b"],
    "FOLATE": ["acido folico", "ácido fólico", r"\bfol(ato|ate)?\b"],
    "ANTI_TPO": ["anti[- ]?tireo(ide|ide) peroxidase", "anti tpo", r"\banti[- ]?tpo\b"],
    "ANTI_TG": ["anti[- ]?tireoglobulina", "anti[- ]?tg"],
    "CA15_3": [r"\bca[- ]?15[- ]?3\b"],
    "CA19_9": [r"\bca[- ]?19[- ]?9\b"],
    "FER": ["ferritina"],
    "B12": ["vitamina b12", r"\bb12\b"],
    "VITD": [r"\b25[- ]?hidroxi vitamina d\b", r"\b25[- ]?oh\b", r"\bvitamina d\b", r"\bvitd\b"],
    "CEA": ["antigeno carcinoembr(i|e)ogenico", "antígeno carcinoembr(i|e)ogênico", r"\bcea\b"],
    "CA125": [r"\bca[- ]?125\b"],
    "CORT": [r"\bcortisol\b", r"cortisol\s*seric[oa]"],
    "C_PEP": ["peptideo c", "peptídeo c", r"\bc[- ]?pep\b"],
    "SHBG": [r"\bshbg\b", r"\bglobulina\s+ligadora\s+de\s+hormon(?:i|í)os\s+sexuais\b"],
    "TESTO_FREE": ["testosterona livre", r"\bfree testosterone\b"],
    "RT3": [r"\brt3\b", r"\bt3\s*reverso\b", r"\btriiodotironina\s*revers[oa]\b"],
}

# Ajustes extras em pt-br sem acento
ANALYTE_SYNONYMS.update({
    "WBC": ANALYTE_SYNONYMS.get("WBC", []) + ["leucocitos"],
    "HCT": ANALYTE_SYNONYMS.get("HCT", []) + ["hematocrito"],
    "MCV": ANALYTE_SYNONYMS.get("MCV", []) + ["vcm"],
    "MCH": ANALYTE_SYNONYMS.get("MCH", []) + ["hcm"],
    "MCHC": ANALYTE_SYNONYMS.get("MCHC", []) + ["chcm"],
    "MPV": ANALYTE_SYNONYMS.get("MPV", []) + ["vpm"],
    "RBC": ANALYTE_SYNONYMS.get("RBC", []) + ["hemacias", "hemacias em milhoes"],
    "PLT": ANALYTE_SYNONYMS.get("PLT", []) + ["plaquetas"],
    "SEG": ANALYTE_SYNONYMS.get("SEG", []) + ["segmentados"],
    "EOS": ANALYTE_SYNONYMS.get("EOS", []) + ["eosinofilos"],
    "BASO": ANALYTE_SYNONYMS.get("BASO", []) + ["basofilos"],
    "MONO": ANALYTE_SYNONYMS.get("MONO", []) + ["monocitos"],
    "LYMPH": ANALYTE_SYNONYMS.get("LYMPH", []) + ["linfocitos"],
})

def _looks_like_regex(p: str) -> bool:
    return bool(re.search(r"[.\^\$\*\+\?\{\}\[\]\|\(\)\\]", p or ""))

def _to_fuzzy_regex(token: str) -> str:
    t = _normalize_text(token)
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[^a-z0-9]+", "", t)
    if not t:
        return token
    parts = [re.escape(ch) for ch in t]
    return r"\b" + r"[\s\W_]*".join(parts) + r"\b"

def _is_reference_or_meta_line(s: str) -> bool:
    t = _normalize_text(s or "")
    gatilhos = [
        "valores de refer", "intervalo de refer", "parametros para doencas",
        "fase folicular", "pico do meio do ciclo", "fase lutea", "pos-menopausa",
        "gestantes", "homens", "mulheres", "crianca",
        "material", "metodo", "sistema automatico", "observacao",
        "coletado em", "coleta entre", "coleta", "horas", "data de liberacao",
        "responsavel", "laboratorio", "medico", "resultado(s) anterior(es)",
    ]
    if any(g in t for g in gatilhos):
        return True
    if re.search(r"\d[\d\.,]*\s*(a|ate|até|–|-)\s*\d", t):
        return True
    return False

def _extract_value_for_key(s: str, key: str):
    """
    1) Corta referência/metadados.
    2) Varre números+unidades, ignora intervalos "x a y".
    3) Prefere unidade coerente (UNIT_HINTS) e pega o 1º candidato remanescente.
    """
    s = _truncate_at_ref_meta_tail(s or "")
    if not s:
        return None, None

    cands = []
    for m in _NUM_WITH_UNIT.finditer(s):
        after = s[m.end(): m.end()+40]
        if _looks_interval(after):
            continue
        op = (m.group("op") or None)
        val = _normalize_number(m.group("num"))
        if val is None:
            continue
        unit = _norm_unit(m.group("unit"))
        cands.append({"val": val, "op": op, "unit": unit, "pos": m.start()})

    if not cands:
        return None, None

    hints = [u and _norm_unit(u) for u in UNIT_HINTS.get(key, [])]
    if hints:
        prefer = [c for c in cands if (c["unit"] in hints) or (c["unit"] is None and None in hints)]
        if prefer:
            cands = prefer

    best = sorted(cands, key=lambda c: c["pos"])[0]
    return best["val"], best["op"]

def parse_lab_text_to_form(text: str) -> Dict[str, float]:
    """
    Converte texto OCR/PDF em {key: valor} usando ANALYTE_SYNONYMS (fuzzy).
    - Procura rótulo e tenta ler o valor na mesma linha (após ':' próximo).
    - Se não achar, olha até 6 linhas à frente (pulando referências/metadados).
    - Guarda operador (ex.: '<', '>') em {key}__op quando existir (auxiliar, se precisar).
    - Extrai meta simples: _patient_name e _age_years, quando presentes.
    """
    tnorm = _normalize_text(text or "")
    lines = [ln.strip() for ln in tnorm.splitlines() if ln.strip()]
    form: Dict[str, float] = {}

    compiled = {}
    for key, names in ANALYTE_SYNONYMS.items():
        pats = []
        for nm in names:
            pat = nm if _looks_like_regex(nm) else _to_fuzzy_regex(nm)
            pats.append(re.compile(pat, re.I))
        compiled[key] = pats

    for i, ln in enumerate(lines):
        for key, pats in compiled.items():
            if key in form:
                continue
            for pat in pats:
                m = pat.search(ln)
                if not m:
                    continue
                tail = ln[m.end():].strip()
                val = op = None
                if _has_digit(tail):
                    colon = tail.find(":")
                    if 0 <= colon <= 40:
                        tail = tail[colon + 1:].strip()
                    tail = _truncate_at_ref_meta_tail(tail)
                    val, op = _extract_value_for_key(tail, key)

                if val is None:
                    hop = 0
                    while (i + 1 + hop) < len(lines) and hop < 6:
                        cand = lines[i + 1 + hop]
                        hop += 1
                        if _is_reference_or_meta_line(cand) or not _has_digit(cand):
                            continue
                        v2, op2 = _extract_value_for_key(cand, key)
                        if v2 is not None:
                            val, op = v2, op2
                            break

                if val is not None:
                    form[key] = val
                    if op:
                        form[f"{key}__op"] = op
                    break

    # Metadados simples (paciente / idade)
    m_name = re.search(r"paciente\s*:\s*([^\n]+)", tnorm)
    if m_name:
        form["_patient_name"] = m_name.group(1).strip().upper()[:120]
    m_age = re.search(r"\bidade\s*:\s*(\d{1,3})\b", tnorm)
    if m_age:
        form["_age_years"] = int(m_age.group(1))

    return form
