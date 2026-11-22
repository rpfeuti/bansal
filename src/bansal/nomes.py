"""Equivalência de nomes: bancos, grupos e itens das fontes para os nomes do paper."""

import re

# Os 42 bancos da Tabela 4, na ordem do paper: (bank_id, nome no paper, grupo).
BANCOS = [
    ("SBI", "State Bank of India", "publico"),
    ("SBBJ", "State Bank of Bikaner & Jaipur", "publico"),
    ("SBH", "State Bank of Hyderabad", "publico"),
    ("SBM", "State Bank of Mysore", "publico"),
    ("SBP", "State Bank of Patiala", "publico"),
    ("SBT", "State Bank of Travancore", "publico"),
    ("ALB", "Allahabad Bank", "publico"),
    ("ANDB", "Andhra Bank", "publico"),
    ("BOB", "Bank of Baroda", "publico"),
    ("BOI", "Bank of India", "publico"),
    ("BOM", "Bank of Maharashtra", "publico"),
    ("CAN", "Canara Bank", "publico"),
    ("CBI", "Central Bank of India", "publico"),
    ("CORP", "Corporation Bank", "publico"),
    ("DENA", "Dena Bank", "publico"),
    ("INDB", "Indian Bank", "publico"),
    ("IOB", "Indian Overseas Bank", "publico"),
    ("OBC", "Oriental Bank of Commerce", "publico"),
    ("PSB", "Punjab & Sind Bank", "publico"),
    ("PNB", "Punjab National Bank", "publico"),
    ("SYND", "Syndicate Bank", "publico"),
    ("UCO", "UCO Bank", "publico"),
    ("UBI", "Union Bank of India", "publico"),
    ("UNTD", "United Bank of India", "publico"),
    ("VIJB", "Vijaya Bank", "publico"),
    ("CSB", "Catholic Syrian Bank", "privado"),
    ("CUB", "City Union Bank", "privado"),
    ("DHAN", "Dhanalakshmi Bank", "privado"),
    ("FED", "Federal Bank", "privado"),
    ("JK", "Jammu & Kashmir Bank", "privado"),
    ("KTK", "Karnataka Bank", "privado"),
    ("KVB", "Karur Vysya Bank", "privado"),
    ("LVB", "Lakshmi Vilas Bank", "privado"),
    ("NAIN", "Nainital Bank", "privado"),
    ("RBL", "Ratnakar Bank", "privado"),
    ("SIB", "South Indian Bank", "privado"),
    ("TMB", "Tamilnad Mercantile Bank", "privado"),
    ("AXIS", "Axis Bank", "privado"),
    ("HDFC", "HDFC Bank", "privado"),
    ("ICICI", "ICICI Bank", "privado"),
    ("IIB", "Indusind Bank", "privado"),
    ("DCB", "Development Credit Bank", "privado"),
]

NOME = {b: n for b, n, _ in BANCOS}
GRUPO = {b: g for b, _, g in BANCOS}

# Grafia normalizada (ver chave()) -> bank_id. Inclui os nomes antigos e novos de bancos renomeados.
GRAFIAS = {
    "state bank of india": "SBI",
    "state bank of bikaner and jaipur": "SBBJ",
    "state bank of hyderabad": "SBH",
    "state bank of mysore": "SBM",
    "state bank of patiala": "SBP",
    "state bank of travancore": "SBT",
    "allahabad bank": "ALB",
    "andhra bank": "ANDB",
    "bank of baroda": "BOB",
    "bank of india": "BOI",
    "bank of maharashtra": "BOM",
    "canara bank": "CAN",
    "central bank of india": "CBI",
    "corporation bank": "CORP",
    "dena bank": "DENA",
    "indian bank": "INDB",
    "indian overseas bank": "IOB",
    "oriental bank of commerce": "OBC",
    "punjab and sind bank": "PSB",
    "punjab national bank": "PNB",
    "syndicate bank": "SYND",
    "uco bank": "UCO",
    "union bank of india": "UBI",
    "united bank of india": "UNTD",
    "vijaya bank": "VIJB",
    "catholic syrian bank": "CSB",
    "csb bank": "CSB",
    "city union bank": "CUB",
    "dhanalakshmi bank": "DHAN",
    "dhanlaxmi bank": "DHAN",
    "federal bank": "FED",
    "jammu and kashmir bank": "JK",
    "karnataka bank": "KTK",
    "karur vysya bank": "KVB",
    "lakshmi vilas bank": "LVB",
    "nainital bank": "NAIN",
    "ratnakar bank": "RBL",
    "rbl bank": "RBL",
    "south indian bank": "SIB",
    "tamilnad mercantile bank": "TMB",
    "axis bank": "AXIS",
    "hdfc bank": "HDFC",
    "icici bank": "ICICI",
    "indusind bank": "IIB",
    "development credit bank": "DCB",
    "dcb bank": "DCB",
}


def chave(nome: str) -> str:
    """Normaliza a grafia: minúsculas, & vira and, sem Ltd/Limited/pontuação final."""
    s = nome.lower().replace("&", " and ")
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(r"\b(ltd|limited|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def bank_id(nome: str):
    """bank_id da grafia, ou None se o banco não é um dos 42."""
    return GRAFIAS.get(chave(nome))
