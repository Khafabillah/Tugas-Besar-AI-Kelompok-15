"""
main.py - Entry point.   Jalankan:  python main.py

Tombol:
  1  Local Search Min-Conflicts          2  Backtracking Naif (baseline)
  3  Backtracking + MRV                  4  Backtracking + MRV + LCV
  5  Backtracking + MRV + LCV + AC-3
  R reset | Spasi pause | N 1 langkah | +/- kecepatan | O urutan nilai | S skenario uji
"""

from app import App


def main():
    App().run()


if __name__ == "__main__":
    main()
