import re
NUM = r"(\d[\d,]*(?:\.\d+)?(?: \d\d \d\d)?)"
LAB = {
 "capital": (r"capital", "1"),
 "reservas": (r"reserves\s*(?:and|&)\s*surplus", "2"),
 "depositos": (r"deposits", "3"),
 "borrow": (r"borrowings", "4"),
 "outliab": (r"other\s+liabilities\s*(?:and|&)\s*provisions", "5"),
 "cash": (r"cash\s*(?:and|&)\s*(?:bank\s+)?balances?\s+with\s+(?:reserve\s+bank\s+of\s+india|r\s*b\s*i)", "6"),
 "banks": (r"balances?\s+with\s+banks?\s*(?:and|&)?\s*money\s+at\s+call\s*(?:and|&)?\s*short\s+notice", "7"),
 "invest": (r"investments", "8"),
 "adv": (r"(?:loans\s*(?:and|&)\s*)?advances", "9"),
 "fixed": (r"fixed\s+assets", "10"),
 "outasset": (r"other\s+assets", "11"),
}
def val(tok): return float(re.sub(r"[,\s]", "", tok))
def parse(t):
    r = {}
    for k, (lab, sc) in LAB.items():
        m = re.search(r"(?i)" + lab + r"[\s\.\|:\(\)]{0,300}?\b0?" + sc + r"\s+" + NUM + r"\s+" + NUM, t)
        if m: r[k] = (val(m.group(1)), val(m.group(2)))
    tots = re.findall(r"(?i)\btotal\b[^0-9\n]{0,60}?" + NUM + r"\s+" + NUM, t)
    return r, [(val(a), val(b)) for a, b in tots]
def check(r, tots):
    A = ("cash","banks","invest","adv","fixed","outasset"); Lb = ("capital","reservas","depositos","borrow","outliab")
    assets = sum(r[k][0] for k in A if k in r); liab = sum(r[k][0] for k in Lb if k in r)
    return assets, liab
