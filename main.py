"""
main.py - Entry point.   Jalankan:  python main.py

Tombol:
  1  Min-Conflicts                       2  Backtracking Naif + NC (baseline)
  3  Backtracking + MRV                  4  Backtracking + LCV
  5  Backtracking + Forward Checking     6  Backtracking + MAC/AC-3
  7  MRV + LCV                           8  MRV + LCV + MAC/AC-3
  R reset | Spasi pause | N 1 langkah | +/- kecepatan | O urutan nilai | S skenario uji
"""

from app import App


def main():
    App().run()


if __name__ == "__main__":
    main()
