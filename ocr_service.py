import os
import re
import requests
import pandas as pd

OILS=['SLC','ATTAKA','DURI','BELIDA','SENIPAH CONDENSATE','BANYU URIP']
COLUMNS=['No','Jenis Minyak Mentah Utama','Dated Brent (US$/bbl)','Alpha (US$/bbl)','Harga (US$/bbl)']
PATTERN=r'(?<![\w.])-?\d+[,.]\d{2}(?!\d)'

def recognize(filename, content):
    key=os.getenv('OCR_SPACE_API_KEY','').strip()
    if not key or key=='your_api_key_here':
        raise ValueError('OCR_SPACE_API_KEY belum diatur dalam file .env')
    response=requests.post(os.getenv('OCR_SPACE_API_URL','https://api.ocr.space/parse/image'),
        files={'file':(filename,content)},headers={'apikey':key},
        data={'language':os.getenv('OCR_LANGUAGE','eng'),'isTable':'true',
              'OCREngine':os.getenv('OCR_ENGINE','2'),'scale':'true','detectOrientation':'true'},
        timeout=int(os.getenv('OCR_TIMEOUT','120')))
    response.raise_for_status()
    payload=response.json()
    if payload.get('IsErroredOnProcessing'):
        raise ValueError(str(payload.get('ErrorMessage') or payload.get('ErrorDetails') or 'OCR gagal'))
    parsed=payload.get('ParsedResults') or []
    text='\n'.join(str(p.get('ParsedText','')) for p in parsed).strip()
    if not text:
        raise ValueError('OCR tidak menghasilkan teks')
    return text

def parse(text):
    # Fallback positional: only trustworthy when the OCR text contains exactly 18 decimal values.
    values=[float(x.replace(',','.')) for x in re.findall(PATTERN,text)]
    if len(values)!=len(OILS)*3:
        raise ValueError(f'Terdeteksi {len(values)} angka desimal, diharapkan 18. Perbaiki teks OCR lalu parsing ulang.')
    return pd.DataFrame([{'No':i+1,'Jenis Minyak Mentah Utama':name,
        'Dated Brent (US$/bbl)':values[3*i], 'Alpha (US$/bbl)':values[3*i+1],
        'Harga (US$/bbl)':values[3*i+2]} for i,name in enumerate(OILS)])

def validate(df):
    if len(df)!=len(OILS):
        raise ValueError('Data harus terdiri dari tepat enam baris.')
    out=df.copy()
    for col in COLUMNS[2:]:
        out[col]=pd.to_numeric(out[col],errors='coerce')
        if out[col].isna().any():
            raise ValueError(f'Kolom {col} harus berisi angka yang valid.')
    if out['Jenis Minyak Mentah Utama'].astype(str).tolist()!=OILS:
        raise ValueError('Urutan dan nama enam jenis minyak harus sesuai daftar standar.')
    if not (out['No'].astype(int).tolist()==list(range(1,7))):
        raise ValueError('Nomor baris harus 1 sampai 6.')
    return out[COLUMNS]
