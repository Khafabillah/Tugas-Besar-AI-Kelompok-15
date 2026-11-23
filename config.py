"""
config.py
Konstanta global: 16 sub-zona (X), 5 nilai domain (D), domain unary per skenario,
warna, dan ukuran layar.
"""

# ----------------------------------------------------------------------
# Domain (D): 5 nilai generik
# ----------------------------------------------------------------------
TUAN_RUMAH = "Tuan_Rumah"
TAMU = "Tamu"
VIP = "VIP"          # VVIP, VIP, sponsor, korporat
MEDIA = "Media"      # pers, komentator, kru kamera
NETRAL = "Netral"    # umum, keluarga, difabel, transit, buffer

DOMAIN = [TUAN_RUMAH, TAMU, VIP, MEDIA, NETRAL]
SHORT_NAMES = {TUAN_RUMAH: "TR", TAMU: "TM", VIP: "VP", MEDIA: "MD", NETRAL: "NT"}

# Urutan nilai STATIS (baseline naif & tie-break LCV). Tombol [O].
STATIC_VALUE_ORDERS = {
    "asli": [TUAN_RUMAH, TAMU, VIP, MEDIA, NETRAL],
    "tamu_dulu": [TAMU, TUAN_RUMAH, VIP, MEDIA, NETRAL],
}

# ----------------------------------------------------------------------
# Variabel (X): 16 sub-zona
# (nomor, nama variabel, label di node, sektor besar)
# ----------------------------------------------------------------------
ZONES = [
    (1, "Royal_Box", "Royal Box", "BARAT"),
    (2, "VIP_Lounge", "VIP Lounge", "BARAT"),
    (3, "Press_Box", "Press Box", "BARAT"),
    (4, "Komentator", "Komentator", "BARAT"),
    (5, "Difabel_B", "Difabel B", "BARAT"),
    (6, "Reguler_B", "Reguler B", "BARAT"),
    (7, "Skybox", "Skybox", "TIMUR"),
    (8, "Keluarga", "Keluarga", "TIMUR"),
    (9, "Ekonomi_Atas", "Ekon. Atas", "TIMUR"),
    (10, "Difabel_T", "Difabel T", "TIMUR"),
    (11, "Home_Core", "Home Core", "HOME END"),
    (12, "Ekonomi_US", "Ekon. U/S", "HOME END"),
    (13, "Transit", "Transit", "HOME END"),
    (14, "Away_Utama", "Away", "AWAY"),
    (15, "Buffer_Kiri", "Buffer Kr", "AWAY"),
    (16, "Buffer_Kanan", "Buffer Kn", "AWAY"),
]

VARIABLES = [z[1] for z in ZONES]                      # urutan statis (1..16)
ZONE_NUMBER = {z[1]: z[0] for z in ZONES}
ZONE_LABEL = {z[1]: z[2] for z in ZONES}
ZONE_SECTOR = {z[1]: z[3] for z in ZONES}
_BY_NUMBER = {z[0]: z[1] for z in ZONES}

# Urutan fisik melingkar (searah jarum jam):
# Barat(1-6) -> Home End(13,12,11) -> Away(15,14,16) -> Timur(10,9,8,7) -> kembali ke 1
RING_NUMBERS = [1, 2, 3, 4, 5, 6, 13, 12, 11, 15, 14, 16, 10, 9, 8, 7]
RING_ORDER = [_BY_NUMBER[n] for n in RING_NUMBERS]

# ----------------------------------------------------------------------
# Constraint
# ----------------------------------------------------------------------
MAX_TAMU_SECTORS = 1
FORBIDDEN_TAMU_NEIGHBORS = [TUAN_RUMAH]          # (a)
FORBIDDEN_PREMIUM_NEIGHBORS = [VIP, MEDIA]       # (d)

_STRICT = {
    "Royal_Box": [VIP], "VIP_Lounge": [VIP], "Press_Box": [MEDIA],
    "Komentator": [MEDIA], "Skybox": [VIP],
}

# Skenario STANDAR: 13 zona terkunci 1 nilai, 3 fleksibel (sesuai spesifikasi).
UNARY_STANDAR = {
    **_STRICT,
    "Difabel_B": [NETRAL], "Reguler_B": [TUAN_RUMAH, NETRAL],
    "Keluarga": [NETRAL], "Ekonomi_Atas": [TUAN_RUMAH, NETRAL],
    "Difabel_T": [NETRAL], "Home_Core": [TUAN_RUMAH],
    "Ekonomi_US": [TUAN_RUMAH, NETRAL], "Transit": [NETRAL],
    "Away_Utama": [TAMU], "Buffer_Kiri": [NETRAL], "Buffer_Kanan": [NETRAL],
}

# Skenario LONGGAR (uji): hanya zona VIP/Media yang terkunci; zona lain
# boleh Tuan_Rumah/Tamu/Netral -> ruang pencarian ramai, clash & AC-3 terlihat.
_FLEX = [TUAN_RUMAH, TAMU, NETRAL]
UNARY_LONGGAR = {
    **_STRICT,
    "Difabel_B": _FLEX, "Reguler_B": _FLEX, "Keluarga": _FLEX,
    "Ekonomi_Atas": _FLEX, "Difabel_T": _FLEX, "Home_Core": [TUAN_RUMAH, NETRAL],
    "Ekonomi_US": _FLEX, "Transit": _FLEX, "Away_Utama": [TAMU, NETRAL],
    "Buffer_Kiri": _FLEX, "Buffer_Kanan": _FLEX,
}

UNARY_BY_SCENARIO = {"standar": UNARY_STANDAR, "longgar": UNARY_LONGGAR}

# ----------------------------------------------------------------------
# Tampilan
# ----------------------------------------------------------------------
WINDOW_W, WINDOW_H = 1280, 760
LEFT_W = 720
FPS = 60
BASE_DELAY_MS = 400

BG = (27, 31, 39)
PANEL_BG = (13, 17, 23)
EMPTY_COLOR = (55, 71, 79)

GROUP_COLORS = {
    TUAN_RUMAH: (229, 57, 53),
    TAMU: (30, 136, 229),
    VIP: (171, 71, 188),
    MEDIA: (255, 152, 0),
    NETRAL: (253, 216, 53),
}
GROUP_TEXT_COLORS = {
    TUAN_RUMAH: (255, 255, 255),
    TAMU: (255, 255, 255),
    VIP: (255, 255, 255),
    MEDIA: (17, 17, 17),
    NETRAL: (17, 17, 17),
}

LOG_COLORS = {
    "sys": (158, 158, 158),
    "header": (144, 202, 249),
    "info": (201, 209, 217),
    "order": (176, 190, 197),
    "mrv": (128, 222, 234),
    "lcv": (206, 147, 216),
    "fc": (129, 212, 250),
    "ac3": (255, 213, 79),
    "ac3_ok": (140, 130, 80),
    "assign": (165, 214, 167),
    "clash": (255, 82, 82),
    "backtrack": (255, 183, 77),
    "success": (105, 240, 174),
    "fail": (255, 138, 128),
}
