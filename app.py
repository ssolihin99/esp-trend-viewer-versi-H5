import streamlit as st
import pandas as pd
import h5py
import tempfile
import plotly.express as px
import os

# 1. Konfigurasi Halaman (Harus di paling atas)
st.set_page_config(page_title="Grafik Generator", page_icon="⚡", layout="wide")

# Sembunyikan menu bawaan Streamlit agar terlihat lebih bersih (Opsional)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Parameter yang ingin dipertahankan
DESIRED_COLUMNS = [
    'time', 'VsdFreqOut', 'VsdAmps', 'VsdMotAmps', 'VSD Power In', 'VSD Power Out', 
    'VSD Volts In', 'VSD Volts Out', 'VSD Torque Percentage Live', 'VSDG7 Load', 'VSDG7 Speed Cmd WR', 
    'Motor Load', 'Starts', 'Temperature', 'SupplyVolts', 'Drive Run Status', 'COS PHI Live',
    'Active Current Leakage', 'Passive Current Leakage', 'DH Cf', 'DH Cz'
] # Saya hapus parameter DH yang kosong agar lebih ringan

# 2. SIDEBAR (Panel Samping untuk Kontrol)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2933/2933116.png", width=80) # Icon dummy
    st.title("⚙️ Control Panel")
    st.write("Silakan unggah log data sumur di sini.")
    
    uploaded_file = st.file_uploader("Upload File .h5", type=['h5', 'hdf5'])

# 3. AREA UTAMA (Main Page)
st.title("📊 Grafik Generator")
st.markdown("---")

if uploaded_file is not None:
    with st.spinner("Mengekstrak dan memproses data... ⏳"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        dfs = []
        try:
            with h5py.File(tmp_path, 'r') as f:
                ts_group = f.get('Non-Conforming Time Series')
                if ts_group:
                    for tag_name in ts_group.keys():
                        if tag_name in DESIRED_COLUMNS:
                            dataset = ts_group[tag_name]
                            if len(dataset) > 0:
                                data = dataset[:]
                                if 'time' in data.dtype.names and 'value' in data.dtype.names:
                                    df = pd.DataFrame(data)
                                    df = df.rename(columns={'value': tag_name})
                                    df['time'] = pd.to_datetime(df['time'], unit='s')
                                    dfs.append(df)
            
            if dfs:
                merged_df = dfs[0]
                for df in dfs[1:]:
                    merged_df = pd.merge(merged_df, df, on='time', how='outer')
                
                merged_df = merged_df.sort_values('time').reset_index(drop=True)
                merged_df = merged_df.ffill().bfill()
                
                # 4. KARTU METRIK (KPI) di atas grafik
                st.subheader("Ringkasan Nilai Maksimum (Berdasarkan Log)")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    max_freq = merged_df['VsdFreqOut'].max() if 'VsdFreqOut' in merged_df else 0
                    st.metric(label="Max Frequency", value=f"{max_freq:.2f} Hz")
                with col2:
                    max_amp = merged_df['VsdAmps'].max() if 'VsdAmps' in merged_df else 0
                    st.metric(label="Max VSD Amps", value=f"{max_amp:.2f} A")
                with col3:
                    max_volt = merged_df['VSD Volts Out'].max() if 'VSD Volts Out' in merged_df else 0
                    st.metric(label="Max Volts Out", value=f"{max_volt:.2f} V")
                with col4:
                    max_leak = merged_df['Active Current Leakage'].max() if 'Active Current Leakage' in merged_df else 0
                    st.metric(label="Max Active Leakage", value=f"{max_leak:.2f} mA")
                
                st.markdown("---")

                # 5. TABS (Memisahkan Grafik dan Tabel agar tidak menumpuk)
                tab1, tab2 = st.tabs(["📈 Analisis Grafik Interaktif", "🗃️ Data Tabel & Download"])
                
                with tab1:
                    parameter_pilihan = st.multiselect(
                        "Pilih parameter untuk di-plot:",
                        options=[col for col in merged_df.columns if col != 'time'],
                        default=['VsdFreqOut', 'VsdAmps']
                    )
                    
                    if parameter_pilihan:
                        fig = px.line(merged_df, x='time', y=parameter_pilihan, 
                                      template="plotly_dark", # Tema grafik yang modern
                                      labels={"value": "Nilai Parameter", "time": "Waktu"})
                        fig.update_layout(legend_title_text='Parameter', hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.dataframe(merged_df.head(500), use_container_width=True) # Tampilan tabel melebar
                    csv = merged_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV Bersih",
                        data=csv,
                        file_name='Clean_Pump_Data.csv',
                        mime='text/csv',
                    )

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
        finally:
            os.remove(tmp_path)
else:
    # Tampilan kosong saat belum ada file yang diunggah
    st.info("👈 Silakan unggah file HDF5 melalui panel di sebelah kiri untuk memulai analisis.")
