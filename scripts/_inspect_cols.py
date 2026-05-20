import io, requests, pandas as pd
HEADERS = {"User-Agent": "Mozilla/5.0"}
sheets = [
    ("Manta Arealva", "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW", "1544210185"),
    ("Manta Iacanga", "14OFOAxrV_DkyrwG6KG8NZT-PeXUV4jezPrPO90rh1DU", "1362699684"),
    ("Lencol", "1BAbgM0zLWBHPn06LfzEvH4aPH84eZvAV", "1396046910"),
]
for nome, sid, gid in sheets:
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv"
    if gid:
        url += f"&gid={gid}"
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.encoding = "utf-8"
    df = pd.read_csv(io.StringIO(r.text), header=0, dtype=str, nrows=2)
    print(f"\n=== {nome} ===")
    for c in df.columns:
        val = str(df[c].iloc[0]) if len(df) > 0 else ""
        print(f"  {c!r}: {val!r}")
