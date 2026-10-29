import io
import os
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv(Path(__file__).with_name('.env'))
from database import initialize,save,histories,detail,delete
from ocr_service import recognize,parse,validate,COLUMNS

st.set_page_config(page_title='OCR Harga Minyak',page_icon='🛢️',layout='wide')
initialize()

def excel_bytes(df):
    output=io.BytesIO()
    summary=pd.DataFrame({'Keterangan':['Jumlah Data','Total Harga','Rata-rata Harga'],
        'Nilai':[len(df),float(df[COLUMNS[4]].sum()),float(df[COLUMNS[4]].mean())]})
    with pd.ExcelWriter(output,engine='openpyxl') as writer:
        df.to_excel(writer,sheet_name='Data Minyak',index=False)
        summary.to_excel(writer,sheet_name='Ringkasan',index=False)
        for sheet in writer.sheets.values():
            sheet.freeze_panes='A2'
            sheet.column_dimensions['A'].width=20
            sheet.column_dimensions['B'].width=30
            for c in 'CDE':sheet.column_dimensions[c].width=25
    return output.getvalue()

st.title('🛢️ OCR Harga Minyak Mentah')
st.caption('OCR.space API · Streamlit · SQLite · Excel')
tab_upload,tab_history=st.tabs(['📤 Upload & OCR','🗂️ Histori SQLite'])

with tab_upload:
    uploads=st.file_uploader('Unggah satu atau beberapa gambar',type=['png','jpg','jpeg','bmp','tif','tiff'],accept_multiple_files=True)
    if st.button('🔍 Jalankan OCR',type='primary',disabled=not uploads):
        for f in uploads or []:
            content=f.getvalue()
            max_bytes=int(os.getenv('OCR_MAX_FILE_MB','5'))*1024*1024
            if len(content)>max_bytes:
                st.error(f'{f.name}: file melebihi batas {max_bytes//(1024*1024)} MB');continue
            try:
                Image.open(io.BytesIO(content)).verify()
                with st.spinner(f'Memproses {f.name}...'):
                    text=recognize(f.name,content)
                digest=hashlib.sha256(content).hexdigest()
                st.session_state[f'ocr_{digest}']={'filename':f.name,'sha256':digest,'text':text}
                st.success(f'OCR berhasil: {f.name}')
            except Exception as exc:
                st.error(f'{f.name}: {exc}')
    for f in uploads or []:
        digest=hashlib.sha256(f.getvalue()).hexdigest()
        key=f'ocr_{digest}'
        if key not in st.session_state:continue
        item=st.session_state[key]
        with st.expander(f'📄 {item["filename"]}',expanded=True):
            left,right=st.columns([1,2])
            with left:st.image(f.getvalue(),caption=f.name,use_container_width=True)
            with right:
                text=st.text_area('Teks OCR (dapat dikoreksi)',value=item['text'],height=190,key=f'text_{digest}')
                if st.button('Parsing ulang dari teks',key=f'parse_{digest}'):
                    try:
                        st.session_state[f'df_{digest}']=parse(text)
                        st.success('Parsing berhasil. Verifikasi tabel sebelum menyimpan.')
                    except ValueError as exc:st.error(str(exc))
                st.download_button('Unduh TXT',text.encode('utf-8'),file_name=f'{Path(f.name).stem}_ocr.txt',mime='text/plain',key=f'txt_{digest}')
            if f'df_{digest}' not in st.session_state:
                try:st.session_state[f'df_{digest}']=parse(text)
                except ValueError as exc:st.warning(str(exc))
            if f'df_{digest}' in st.session_state:
                st.warning('Periksa kecocokan nama dan posisi angka dengan gambar asli. Parsing berbasis urutan angka tidak menjamin pemetaan kolom benar.')
                edited=st.data_editor(st.session_state[f'df_{digest}'],hide_index=True,use_container_width=True,
                    disabled=['No','Jenis Minyak Mentah Utama'],num_rows='fixed',key=f'editor_{digest}')
                try:
                    clean=validate(edited)
                    a,b,c=st.columns(3)
                    a.metric('Jumlah data',len(clean))
                    b.metric('Total harga',f'{clean[COLUMNS[4]].sum():,.2f}')
                    c.metric('Rata-rata (US$/bbl)',f'{clean[COLUMNS[4]].mean():,.4f}')
                    x,y=st.columns(2)
                    x.download_button('⬇️ Export Excel',excel_bytes(clean),file_name=f'{Path(f.name).stem}_hasil_ocr.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f'excel_{digest}')
                    if y.button('💾 Simpan ke SQLite',type='primary',key=f'save_{digest}'):
                        hid=save(f.name,digest,text,clean)
                        st.success(f'Tersimpan sebagai histori #{hid}')
                except (ValueError,TypeError) as exc:st.error(f'Validasi gagal: {exc}')

with tab_history:
    search=st.text_input('Cari berdasarkan nama file')
    history=histories(search)
    if not history:st.info('Belum ada histori.')
    else:
        st.dataframe(pd.DataFrame(history),hide_index=True,use_container_width=True)
        options={f'#{r["id"]} · {r["filename"]} · {r["created_at"]}':r['id'] for r in history}
        selected=st.selectbox('Pilih histori untuk melihat detail',list(options))
        hid=options[selected]
        header,rows=detail(hid)
        if header:
            df=pd.DataFrame(rows,columns=COLUMNS)
            st.dataframe(df,hide_index=True,use_container_width=True)
            a,b,c=st.columns(3)
            a.metric('Jumlah data',header['row_count'])
            b.metric('Total harga',f'{header["total_price"]:,.2f}')
            c.metric('Rata-rata',f'{header["average_price"]:,.4f}')
            st.text_area('Teks OCR asli',header['raw_text'],height=180)
            st.download_button('⬇️ Download ulang Excel',excel_bytes(df),file_name=f'histori_{hid}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            with st.expander('Hapus histori'):
                confirm=st.checkbox('Saya yakin ingin menghapus histori ini',key=f'confirm_{hid}')
                if st.button('Hapus permanen',disabled=not confirm):
                    delete(hid)
                    st.rerun()
