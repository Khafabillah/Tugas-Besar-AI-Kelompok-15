"""
config.py
Konstanta global: Variabel (X), Domain (D), parameter constraint, warna, ukuran layar.
"""

# ----------------------------------------------------------------------
# Domain (D)
# ----------------------------------------------------------------------
TUAN_RUMAH = "Tuan_Rumah"
TAMU = "Tamu"
POLISI = "Polisi"
NETRAL = "Netral"

DOMAIN = [TUAN_RUMAH, TAMU, POLISI, NETRAL]
SHORT_NAMES = {TUAN_RUMAH: "TR", TAMU: "TM", POLISI: "PL", NETRAL: "NT"}

# Urutan nilai STATIS (dipakai baseline naif & sebagai tie-break LCV). Tombol [O].
STATIC_VALUE_ORDERS = {
    "asli": [TUAN_RUMAH, TAMU, POLISI, NETRAL],
    "tamu_dulu": [TAMU, TUAN_RUMAH, POLISI, NETRAL],
}

# ----------------------------------------------------------------------
# Variabel (X)
# ----------------------------------------------------------------------
# Urutan STATIS variabel (dipakai baseline naif)
VARIABLES = ["Utara", "Selatan", "Timur_1", "Timur_2", "Barat_VIP", "Barat_Reguler"]

# Urutan fisik melingkar (searah jarum jam) -> membangun graf tetangga
RING_ORDER = ["Utara", "Timur_1", "Timur_2", "Selatan", "Barat_VIP", "Barat_Reguler"]

VIP_SECTOR = "Barat_VIP"
MAX_TAMU_SECTORS = 1

# ----------------------------------------------------------------------
# Tampilan
# ----------------------------------------------------------------------
WINDOW_W, WINDOW_H = 1280, 760
LEFT_W = 720
FPS = 60
BASE_DELAY_MS = 650          # jeda dasar antar langkah (dikali bobot langkah)

BG = (27, 31, 39)
PANEL_BG = (13, 17, 23)
EMPTY_COLOR = (55, 71, 79)

GROUP_COLORS = {
    TUAN_RUMAH: (229, 57, 53),
    TAMU: (30, 136, 229),
    POLISI: (158, 158, 158),
    NETRAL: (253, 216, 53),
}
GROUP_TEXT_COLORS = {
    TUAN_RUMAH: (255, 255, 255),
    TAMU: (255, 255, 255),
    POLISI: (17, 17, 17),
    NETRAL: (17, 17, 17),
}

LOG_COLORS = {
    "sys": (158, 158, 158),
    "header": (144, 202, 249),
    "info": (201, 209, 217),
    "order": (176, 190, 197),
    "mrv": (128, 222, 234),
    "lcv": (206, 147, 216),
    "ac3": (255, 213, 79),
    "ac3_ok": (140, 130, 80),
    "assign": (165, 214, 167),
    "clash": (255, 82, 82),
    "backtrack": (255, 183, 77),
    "success": (105, 240, 174),
    "fail": (255, 138, 128),
}
