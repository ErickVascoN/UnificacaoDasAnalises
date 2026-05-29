import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from utils.lencol_loader_smart import load_lencol_smart_csv
df = load_lencol_smart_csv()
print(f'\n✓ Carregado: {len(df)} linhas')
if len(df) > 0:
    print(f'Primeiras OPs: {df["OP"].head().tolist()}')
    print(f'Range de datas: {df["DATA"].min()} → {df["DATA"].max()}')
