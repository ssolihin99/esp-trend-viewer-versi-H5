import streamlit as st
import pandas as pd
import h5py
import tempfile
import plotly.express as px
import os

st.set_page_config(page_title="VSD & Pump Dashboard", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 1. KEMBALIKAN SEMUA PARAMETER DOWNHOLE KE SINI
DESIRED_COLUMNS = [
    'time', 'DHDischargePressure', 'DHDischargeTemperature', 'DHDifferentialPressure', 
    'DHIntakePressure', 'DHIntakePressure2', 'DHIntakeTemp', 'DHMotorTemp', 'DHMotorYpoint', 
    'DHVibration', 'DHVibrationAX1', 'DHVibrationAY1', 'DHVibrationAZ1', 'DHVibrationY', 'DHVibrationZ', 
    'DH Cf', 'DH Cz', 'VsdFreqOut', 'VsdAmps', 'VsdMotAmps', 'VSD Power In', 'VSD Power Out', 
    'VSD Volts In', 'VSD Volts Out', 'VSD Torque Percentage Live', 'VSDG7 Load', 'VSDG7 Speed Cmd WR', 
    'Motor Load', 'Starts', 'Temperature', 'SupplyVolts', 'Drive Run Status', 'COS PHI Live',
    'Active Current Leakage', 'Passive Current Leakage'
]

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2933/2933116.png", width=80) 
    st.title("⚙️ Control Panel")
    st.write("Silakan unggah log data sumur di sini.")
    uploaded_file = st.file_uploader("Upload File .h5", type=['h5', 'hdf5'])

st.title("📊 VSD & Pump Performance Dashboard")
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
                            # Ekstrak data jika ada isinya
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
                
                # 2. LOGIKA BARU: Paksa buat kolom jika tidak ada di dalam HDF5 (karena sensor rusak)
                for col in DESIRED_COLUMNS:
                    if col not in merged_df.columns:
                        merged_df[col] = pd.NA # Isi dengan nilai kosong
                
                # Urutkan ulang kolom agar rapi (opsional)
                merged_df = merged_df[DESIRED_COLUMNS]

                merged_df = merged_df.ffill().bfill()
                
                st.subheader("Ringkasan Nilai Maksimum (Berdasarkan Log)")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    max_freq = merged_df['VsdFreqOut'].max() if pd.notna(merged_df['VsdFreqOut'].max()) else 0
                    st.metric(label="Max Frequency", value=f"{max_freq:.2f} Hz")
                with col2:
                    max_amp = merged_df['VsdAmps'].max() if pd.notna(merged_df['VsdAmps'].max()) else 0
                    st.metric(label="Max VSD Amps", value=f"{max_amp:.2f} A")
                with col3:
                    max_volt = merged_df['VSD Volts Out'].max() if pd.notna(merged_df['VSD Volts Out'].max()) else 0
                    st.metric(label="Max Volts Out", value=f"{max_volt:.2f} V")
                with col4:
                    max_leak = merged_df['Active Current Leakage'].max() if pd.notna(merged_df['Active Current Leakage'].max()) else 0
                    st.metric(label="Max Active Leakage", value=f"{max_leak:.2f} mA")
                
                st.markdown("---")

                tab1, tab2 = st.tabs(["📈 Analisis Grafik Interaktif", "🗃️ Data Tabel & Download"])
                
                with tab1:
                    parameter_pilihan = st.multiselect(
                        "Pilih parameter untuk di-plot:",
                        options=[col for col in merged_df.columns if col != 'time'],
                        default=['VsdFreqOut', 'VsdAmps']
                    )
                    
                    if parameter_pilihan:
                        fig = px.line(merged_df, x='time', y=parameter_pilihan, 
                                      template="plotly_dark", 
                                      labels={"value": "Nilai Parameter", "time": "Waktu"})
                        fig.update_layout(legend_title_text='Parameter', hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.dataframe(merged_df.head(500), use_container_width=True) 
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
    st.info("👈 Silakan unggah file HDF5 melalui panel di sebelah kiri untuk memulai analisis.")
