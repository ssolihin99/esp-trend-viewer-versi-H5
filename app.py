import streamlit as st
import pandas as pd
import h5py
import tempfile
import plotly.express as px
import os

# Konfigurasi Halaman
st.set_page_config(page_title="ESP Trend Viewer", layout="wide")
st.title("ESP Trend Viewer ari H5 File")

# Parameter yang ingin dipertahankan
DESIRED_COLUMNS = [
    'time', 'DHDischargePressure', 'DHDischargeTemperature', 'DHDifferentialPressure', 
    'DHIntakePressure', 'DHIntakePressure2', 'DHIntakeTemp', 'DHMotorTemp', 'DHMotorYpoint', 
    'DHVibration', 'DHVibrationAX1', 'DHVibrationAY1', 'DHVibrationAZ1', 'DHVibrationY', 'DHVibrationZ', 
    'DH Cf', 'DH Cz', 'VsdFreqOut', 'VsdAmps', 'VsdMotAmps', 'VSD Power In', 'VSD Power Out', 
    'VSD Volts In', 'VSD Volts Out', 'VSD Torque Percentage Live', 'VSDG7 Load', 'VSDG7 Speed Cmd WR', 
    'Motor Load', 'Starts', 'Temperature', 'SupplyVolts', 'Drive Run Status', 'COS PHI Live',
    'Active Current Leakage', 'Passive Current Leakage'
]

# Modul Upload File
uploaded_file = st.file_uploader("Upload File HDF5 Anda (.h5)", type=['h5', 'hdf5'])

if uploaded_file is not None:
    st.info("Memproses data, mohon tunggu...")
    
    # Simpan sementara file upload agar bisa dibaca h5py
    with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    dfs = []
    try:
        # Proses Ekstraksi HDF5
        with h5py.File(tmp_path, 'r') as f:
            ts_group = f.get('Non-Conforming Time Series')
            if ts_group:
                for tag_name in ts_group.keys():
                    if tag_name in DESIRED_COLUMNS: # FILTERING LOGIC
                        dataset = ts_group[tag_name]
                        if len(dataset) > 0:
                            data = dataset[:]
                            if 'time' in data.dtype.names and 'value' in data.dtype.names:
                                df = pd.DataFrame(data)
                                df = df.rename(columns={'value': tag_name})
                                df['time'] = pd.to_datetime(df['time'], unit='s')
                                dfs.append(df)
        
        if dfs:
            # Menggabungkan semua data
            merged_df = dfs[0]
            for df in dfs[1:]:
                merged_df = pd.merge(merged_df, df, on='time', how='outer')
            
            merged_df = merged_df.sort_values('time').reset_index(drop=True)
            
            # LOGIKA FORWARD FILL
            merged_df = merged_df.ffill().bfill()
            
            st.success("Data berhasil diekstrak dan dibersihkan!")
            
            # Opsi Pilih Parameter untuk Grafik
            st.subheader("Visualisasi Grafik")
            parameter_pilihan = st.multiselect(
                "Pilih parameter yang ingin ditampilkan (Bisa lebih dari 1):",
                options=[col for col in merged_df.columns if col != 'time'],
                default=['VsdFreqOut', 'VsdAmps'] # Default yang langsung muncul
            )
            
            if parameter_pilihan:
                # Bikin Grafik pakai Plotly (Interaktif)
                fig = px.line(merged_df, x='time', y=parameter_pilihan, 
                              title="Tren Parameter Terhadap Waktu",
                              labels={"value": "Nilai Parameter", "time": "Waktu"})
                st.plotly_chart(fig, use_container_width=True)
            
            # Opsi Download Data Bersih
            st.subheader("Data Tabel Bersih (Siap Unduh)")
            st.dataframe(merged_df.head(100)) # Tampilkan 100 baris pertama
            
            csv = merged_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data CSV Bersih",
                data=csv,
                file_name='Filtered_Pump_Data_FFilled.csv',
                mime='text/csv',
            )
        else:
            st.warning("Tidak ditemukan data time-series yang relevan di file ini.")
            
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
    finally:
        os.remove(tmp_path) # Hapus file sementara
