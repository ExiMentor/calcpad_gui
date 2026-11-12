"""Application identity, unchanged settings schema and symbol tables (no GTK)."""
from pathlib import Path

APP_ID    = "org.community.calcpadce.linuxgui"

APP_TITLE = "CalcpadCE"

_SUPER_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

_SUB_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

DEFAULT_SETTINGS = {
    "recent": [], "dark_preview": False, "auto_refresh": True,
    "last_dir": str(Path.home()), "schema": 1,
    "decimal_comma": False,
    "decimal_places": 3,
    "keyboard_favorites": [],
    "keyboard_visible": True,
}

DEFAULT_SAMPLE = """' CalcpadCE Demo
' Electrical power across a resistor
U = 230 V
R = 47 Ω
I = U / R
P = U * I

' Using micro prefix:
C = 4.7 μF
τ = R * C
"""

GREEK_TABLE = [
    ("α","alpha","`a"),("β","beta","`b"),("χ","chi","`c"),
    ("δ","delta","`d"),("ε","epsilon","`e"),("φ","phi","`f"),
    ("γ","gamma","`g"),("η","eta","`h"),("ι","iota","`i"),
    ("κ","kappa","`k"),("λ","lambda","`l"),("μ","mu","`m"),
    ("ν","nu","`n"),("ο","omicron","`o"),("π","pi","`p"),
    ("θ","theta","`q"),("ρ","rho","`r"),("σ","sigma","`s"),
    ("τ","tau","`t"),("υ","upsilon","`u"),("ω","omega","`w"),
    ("ξ","xi","`x"),("ψ","psi","`y"),("ζ","zeta","`z"),
    ("Α","Alpha","`A"),("Β","Beta","`B"),("Γ","Gamma","`G"),
    ("Δ","Delta","`D"),("Ε","Epsilon","`E"),("Ζ","Zeta","`Z"),
    ("Η","Eta","`H"),("Θ","Theta","`Q"),("Κ","Kappa","`K"),
    ("Λ","Lambda","`L"),("Μ","Mu","`M"),("Ν","Nu","`N"),
    ("Ξ","Xi","`X"),("Π","Pi","`P"),("Ρ","Rho","`R"),
    ("Σ","Sigma","`S"),("Τ","Tau","`T"),("Υ","Upsilon","`U"),
    ("Φ","Phi","`F"),("Ψ","Psi","`Y"),("Ω","Omega","`W"),
]

SYMBOL_TABLE = [
    ("°","degree","`@"),("′","prime","`'"),
    ("″","double prime",'`\"'),("±","plus-minus",""),
    ("·","middle dot",""),("×","times",""),
    ("÷","divide",""),("≤","less or eq","<="),
    ("≥","greater or eq","≥"),("≠","not equal","≠"),
    ("≈","approx",""),("∞","infinity",""),
    ("√","sqrt",""),("∑","sum",""),
    ("∫","integral",""),("∂","partial",""),
    ("²","squared",""),("³","cubed",""),
]

QUICK_TOOLBAR = ["Ω","μ","π","°","²","³",
                 "±","·","≤","≥","≠","√",
                 "∑","∫","∞"]

QUICK_HOTKEYS = {"o":"Ω","m":"μ","p":"π","a":"α",
                 "b":"β","d":"δ","t":"τ","l":"λ",
                 "s":"σ","g":"γ"}
