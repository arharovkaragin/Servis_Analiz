import streamlit as st
import pandas as pd
import PyPDF2
from openai import OpenAI
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import io
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# .env dosyasını yükle
load_dotenv()

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="PDF Analiz Uygulaması",
    page_icon="📄",
    layout="wide"
)

# Başlık
st.title("📄 PDF Analiz ve Excel Çıktı Uygulaması")
st.markdown("Bu uygulama PDF dosyalarınızı analiz ederek istediğiniz bilgileri çıkarır ve Excel formatında kaydeder.")

# Sayfa seçimi
page = st.sidebar.selectbox("📊 Sayfa Seçin", ["PDF Analiz", "Veri Analizi"])

# Sidebar - API Key girişi
st.sidebar.header("⚙️ Ayarlar")

# .env dosyasından API key'i oku
api_key = os.getenv("OPENAI_API_KEY", "")

# API anahtarı durumunu göster
if api_key:
    st.sidebar.info("✅ API Anahtarı: Otomatik yüklendi")
else:
    st.sidebar.error("❌ API Anahtarı bulunamadı!")

# OpenAI client'ını başlat
client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        # API anahtarını test et
        test_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        st.sidebar.success("✅ API Anahtarı başarıyla test edildi!")
    except Exception as e:
        st.sidebar.error(f"❌ API Anahtarı hatası: {str(e)}")
        client = None
else:
    st.sidebar.warning("⚠️ API Anahtarı gerekli!")

# Fonksiyonlar
def extract_text_from_pdf(pdf_file):
    """PDF dosyasından metin çıkarır - Kullanıcı dostu"""
    try:
        # PyPDF2 ile deneme
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        # Sayfa sayısını kontrol et
        if len(pdf_reader.pages) == 0:
            return None
            
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    # Türkçe karakterleri düzelt
                    page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                    text += page_text
            except Exception:
                continue
        
        # Eğer hiç metin bulunamadıysa
        if not text or len(text.strip()) < 10:
            return None
        
        # Türkçe karakterleri normalize et
        text = text.replace('Ä±', 'ı').replace('Å\x9f', 'ş').replace('Ä\x9f', 'ğ')
        text = text.replace('Ã¼', 'ü').replace('Ã¶', 'ö').replace('Ã§', 'ç')
        text = text.replace('Ä°', 'İ').replace('Åž', 'Ş').replace('ÄŸ', 'Ğ')
        text = text.replace('Ãœ', 'Ü').replace('Ã–', 'Ö').replace('Ã‡', 'Ç')
        
        return text
        
    except Exception:
        return None

def analyze_pdf_with_gpt(text, client):
    """GPT API kullanarak PDF içeriğini analiz eder"""
    try:
        if not client:
            return None
            
        prompt = f"""
        Aşağıda Siemens formatında bir servis raporunun metni bulunmaktadır. Bu metni analiz ederek belirtilen alanları çıkartmanı istiyorum. PDF'ler hem Türkçe hem İngilizce başlıklar içerebilir. Her alanın başlık varyasyonları aşağıda listelenmiştir. Bu başlıklardan herhangi biri geçiyorsa, ona karşılık gelen değeri çıkar. Eğer hiçbiri yoksa o alanı boş ("") bırak.

        ❗️ ÖNEMLİ: Türkçe karakterleri (ı, ş, ğ, ü, ö, ç, İ, Ş, Ğ, Ü, Ö, Ç) doğru tanı ve kullan!
        ❗️ ÖNEMLİ: Özellikle "Sonuç" alanını dikkatli ara! "Conclusion", "Sonuç", "Result", "Summary" başlıklarının altındaki metinleri mutlaka çıkar.

        ❗️Çıktıyı aşağıdaki JSON şemasına uygun şekilde hazırla:

        {{
          "Restoration_Time": "",        // "Restoration Time", "Rapor hazırlanma zamanı", "Ticket reporting time", "Date", "Tarih", "Time", "Zaman"
          "Work_Carried_Out": "",        // "Yapılan işlemler", "Work carried out", "İş tanımı", "Job Description", "Programa online", "İşlem"
          "Product_Number": "",          // "Product No:", "Product Number", "Ürün No", "Model", "Part Number", "Article Number" (ÜRÜN MODEL NUMARASI)
          "Customer_Company": "",        // "Firma", "Company", "Name", "Customer", "Müşteri", "End Customer", "TÜPRAŞ", "Petrol", "Rafineri"
          "Customer_Location": "",       // "Konum", "Location", "ZIP Code", "Address", "Adres", "BAHŞILI", "KIRIKKALE", "Şehir"
          "Service_Engineer": "",        // "Servis Uzmanı", "Service Engineer", "Teknisyen", "Technician", "Engineer", "Adigüzel", "Kadir"
          "Conclusion": "",              // "Conclusion", "Sonuç", "Result", "Netice", "Summary", "PLC'lerde devam eden", "bulunmadığı gözlemlenmiştir"
          "EQ_No_End_Customer": ""       // "EQ No", "Equipment No", "Ekipman No", "EQ No. End Customer" - Varsa ekipman numarasını yaz, yoksa boş bırak
        }}

        Rapor metni aşağıdadır:
        ------------------------------------------------------
        {text[:6000]}
        ------------------------------------------------------
        
        ÖZELLİKLE DİKKAT ET:
        1. "Sonuç / Conclusion" başlığı altındaki tüm metni çıkar
        2. PDF'de "Yapılan çalışmalar sonucunda PLC'lerde devam eden hatalar bulunmadığı gözlemlenmiştir" gibi metinler varsa bunları "Conclusion" alanına yaz
        3. Tarih formatını dd/mm/yyyy şeklinde düzenle
        4. Uzun metinleri özetle ama önemli bilgileri kaybetme
        5. Sadece JSON formatında yanıt ver, başka açıklama ekleme
        6. Türkçe ve İngilizce başlıkları aynı şekilde işle
        7. Tüm alanları dikkatli kontrol et, hiçbirini atlama
        8. **ÖNEMLİ: Product No (ürün model numarası) ile EQ No (ekipman numarası) FARKLI bilgilerdir! Karıştırma!**
        9. **Türkçe karakterleri (ç, ğ, ı, ö, ş, ü) doğru kullan ve tanı!**
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen Siemens servis raporlarını analiz eden uzman bir AI asistanısın. Türkçe ve İngilizce başlıkları tanıyorsun ve sadece JSON formatında yanıt veriyorsun. Özellikle 'Sonuç/Conclusion' alanlarını dikkatli analiz ediyorsun."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        # JSON yanıtını parse et
        result_text = response.choices[0].message.content
        
        # JSON formatını temizle
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1]
            
        result = json.loads(result_text.strip())
        
        # Alan isimlerini Türkçe'ye çevir (Excel için)
        translated_result = {
            "Geri Yükleme Zamanı": result.get("Restoration_Time", ""),
            "Yapılan İşlemler": result.get("Work_Carried_Out", ""),
            "Ürün Numarası": result.get("Product_Number", ""),
            "Müşteri Firma": result.get("Customer_Company", ""),
            "Müşteri Konumu": result.get("Customer_Location", ""),
            "Servis Uzmanı": result.get("Service_Engineer", ""),
            "Sonuç": result.get("Conclusion", ""),
            "Ekipman No": result.get("EQ_No_End_Customer", "")
        }
        
        return translated_result
        
    except Exception:
        return None

def pdf_analysis_page():
    """PDF Analiz sayfası"""
    # Ana içerik
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📤 PDF Dosyalarını Yükleyin")
        uploaded_files = st.file_uploader(
            "PDF dosyalarınızı seçin",
            type=['pdf'],
            accept_multiple_files=True,
            help="Birden fazla PDF dosyası yükleyebilirsiniz"
        )

    with col2:
        st.header("🔍 Çıkarılacak Bilgiler")
        st.markdown("""
        **Otomatik çıkarılan bilgiler:**
        - **Geri Yükleme Zamanı** (Restoration Time, Date, Tarih)
        - **Yapılan İşlemler** (Work carried out, İş tanımı)
        - **Ürün Numarası** (Product No, Model - Ürün model numarası)
        - **Müşteri Firma** (Company, End Customer, Müşteri)
        - **Müşteri Konumu** (Location, Address, Adres)
        - **Servis Uzmanı** (Service Engineer, Teknisyen)
        - **Sonuç** (Conclusion, Result, Netice)
        - **Ekipman No** (EQ No, Equipment No - Ekipman numarası varsa)
        
        💡 *Sistem birden fazla başlık formatını tanır*
        ⚠️ **Not:** Ürün No ve Ekipman No farklı bilgilerdir!
        """)

    # Özel bilgi alanlarını kaldır - artık sabit bilgiler kullanılacak
    st.header("📋 Analiz Bilgileri")
    st.info("Sistem otomatik olarak Türkçe ve İngilizce başlıkları tanıyarak yukarıdaki bilgileri PDF'lerden çıkaracaktır. Bilgi bulunamazsa ilgili alan boş bırakılacaktır.")

    # Ana işlem
    if st.button("🚀 Analizi Başlat", type="primary"):
        if not api_key:
            st.error("⚠️ Lütfen OpenAI API Key'inizi girin!")
        elif not client:
            st.error("⚠️ OpenAI client başlatılamadı. API key'inizi kontrol edin!")
        elif not uploaded_files:
            st.error("⚠️ Lütfen en az bir PDF dosyası yükleyin!")
        else:
            # Sonuçları saklamak için liste
            results = []
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"İşleniyor: {uploaded_file.name}")
                
                # PDF'den metin çıkar
                text = extract_text_from_pdf(uploaded_file)
                
                if text:
                    # GPT ile analiz et
                    analysis_result = analyze_pdf_with_gpt(text, client)
                    
                    if analysis_result:
                        analysis_result["Dosya Adı"] = uploaded_file.name
                        analysis_result["İşlem Tarihi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        results.append(analysis_result)
                        st.success(f"✅ {uploaded_file.name} - Başarıyla analiz edildi")
                    else:
                        st.warning(f"⚠️ {uploaded_file.name} - Analiz edilemedi (GPT hatası)")
                else:
                    st.warning(f"⚠️ {uploaded_file.name} - PDF okunamadı (şifreli veya taranmış görsel olabilir)")
                
                # Progress bar güncelle
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text("✅ Analiz tamamlandı!")
            
            if results:
                # DataFrame oluştur
                df = pd.DataFrame(results)
                
                # Sonuçları session state'e kaydet
                st.session_state['analysis_data'] = df
                
                # Sonuçları göster
                st.header("📊 Analiz Sonuçları")
                st.dataframe(df, use_container_width=True)
                
                # Excel dosyası oluştur
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='PDF Analiz Sonuçları', index=False)
                
                # Excel dosyasını indirme butonu
                st.download_button(
                    label="📥 Excel Dosyasını İndir",
                    data=output.getvalue(),
                    file_name=f"pdf_analiz_sonuclari_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # İstatistikler
                st.header("📈 İstatistikler")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Toplam PDF", len(uploaded_files))
                with col2:
                    st.metric("Başarılı Analiz", len(results))
                with col3:
                    st.metric("Başarı Oranı", f"{(len(results)/len(uploaded_files)*100):.1f}%")
                
                st.success("✅ Veriler analiz için hazır! 'Veri Analizi' sayfasından detaylı analizleri görüntüleyebilirsiniz.")
            
            else:
                st.error("❌ Hiçbir PDF dosyası analiz edilemedi!")

def data_analysis_page():
    """Veri Analizi sayfası"""
    st.header("📊 Veri Analizi Dashboard")
    
    # Session state'den veri kontrolü
    if 'analysis_data' not in st.session_state or st.session_state['analysis_data'].empty:
        st.warning("⚠️ Henüz analiz edilmiş veri bulunmuyor. Önce 'PDF Analiz' sayfasından PDF'lerinizi analiz edin.")
        return
    
    df = st.session_state['analysis_data']
    
    # Veri özeti
    st.subheader("📋 Veri Özeti")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Toplam Kayıt", len(df))
    with col2:
        st.metric("Benzersiz Müşteri", df['Müşteri Firma'].nunique())
    with col3:
        st.metric("Servis Uzmanı", df['Servis Uzmanı'].nunique())
    with col4:
        st.metric("Farklı Lokasyon", df['Müşteri Konumu'].nunique())
    
    # Top 10 Müşteri Dağılımı
    st.subheader("🏢 Top 10 Müşteri Dağılımı")
    if not df['Müşteri Firma'].isna().all():
        customer_counts = df['Müşteri Firma'].value_counts().head(10)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_bar = px.bar(
                x=customer_counts.index,
                y=customer_counts.values,
                title="Top 10 Müşteri - İş Sayısı",
                labels={'x': 'Müşteri Firma', 'y': 'İş Sayısı'},
                color=customer_counts.values,
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            fig_pie = px.pie(
                values=customer_counts.values,
                names=customer_counts.index,
                title="Müşteri Dağılım Oranı"
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Servis Uzmanları Analizi
    st.subheader("👨‍🔧 Servis Uzmanları Performansı")
    if not df['Servis Uzmanı'].isna().all():
        engineer_counts = df['Servis Uzmanı'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_eng = px.bar(
                x=engineer_counts.values,
                y=engineer_counts.index,
                orientation='h',
                title="Servis Uzmanlarının İş Sayıları",
                labels={'x': 'İş Sayısı', 'y': 'Servis Uzmanı'},
                color=engineer_counts.values,
                color_continuous_scale='Greens'
            )
            fig_eng.update_layout(height=400)
            st.plotly_chart(fig_eng, use_container_width=True)
        
        with col2:
            st.write("**📊 Detaylı İstatistik:**")
            for engineer, count in engineer_counts.items():
                st.write(f"• **{engineer}**: {count} iş")
    
    # Zaman Bazında Analiz
    st.subheader("📅 Zaman Bazında Trend Analizi")
    if not df['Geri Yükleme Zamanı'].isna().all():
        # Tarih sütununu datetime'a çevir
        df_time = df.copy()
        df_time['Tarih'] = pd.to_datetime(df_time['Geri Yükleme Zamanı'], errors='coerce')
        df_time = df_time.dropna(subset=['Tarih'])
        
        if not df_time.empty:
            # Aylık trend
            df_time['Yil_Ay'] = df_time['Tarih'].dt.to_period('M')
            monthly_counts = df_time.groupby('Yil_Ay').size()
            
            fig_trend = px.line(
                x=monthly_counts.index.astype(str),
                y=monthly_counts.values,
                title="Zaman Bazında İş Sayısı Trendi",
                labels={'x': 'Ay', 'y': 'İş Sayısı'},
                markers=True
            )
            fig_trend.update_layout(height=400)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("⚠️ Geçerli tarih bilgisi bulunamadı.")
    
    # Yapılan İşler Analizi
    st.subheader("🔧 Yapılan İşlemler Kategorileri")
    if not df['Yapılan İşlemler'].isna().all():
        # İş tiplerini analiz et (basit kelime analizi)
        work_types = []
        for work in df['Yapılan İşlemler'].dropna():
            if 'test' in work.lower():
                work_types.append('Test İşlemleri')
            elif 'bakım' in work.lower() or 'maintenance' in work.lower():
                work_types.append('Bakım İşlemleri')
            elif 'onarım' in work.lower() or 'repair' in work.lower():
                work_types.append('Onarım İşlemleri')
            elif 'kurulum' in work.lower() or 'installation' in work.lower():
                work_types.append('Kurulum İşlemleri')
            elif 'kontrol' in work.lower() or 'check' in work.lower():
                work_types.append('Kontrol İşlemleri')
            else:
                work_types.append('Diğer İşlemler')
        
        if work_types:
            work_counts = Counter(work_types)
            
            fig_work = px.pie(
                values=list(work_counts.values()),
                names=list(work_counts.keys()),
                title="İş Tipi Dağılımı"
            )
            fig_work.update_layout(height=400)
            st.plotly_chart(fig_work, use_container_width=True)
    
    # Lokasyon Analizi
    st.subheader("🌍 Müşteri Lokasyon Dağılımı")
    if not df['Müşteri Konumu'].isna().all():
        location_counts = df['Müşteri Konumu'].value_counts().head(15)
        
        fig_loc = px.bar(
            x=location_counts.values,
            y=location_counts.index,
            orientation='h',
            title="Top 15 Servis Lokasyonu",
            labels={'x': 'İş Sayısı', 'y': 'Lokasyon'},
            color=location_counts.values,
            color_continuous_scale='Reds'
        )
        fig_loc.update_layout(height=600)
        st.plotly_chart(fig_loc, use_container_width=True)
    
    # Ham veri görüntüleme
    st.subheader("📋 Ham Veri")
    st.dataframe(df, use_container_width=True)

# Ana sayfa içeriği
if page == "PDF Analiz":
    pdf_analysis_page()
elif page == "Veri Analizi":
    data_analysis_page()

# Footer (sadece PDF Analiz sayfasında)
if page == "PDF Analiz":
    st.markdown("---")
    st.markdown("🔧 **Kullanım Talimatları:**")
    st.markdown("""
    1. PDF dosyalarınızı yükleyin (Türkçe/İngilizce desteklenir)
    2. 'Analizi Başlat' butonuna tıklayın
    3. Sistem otomatik olarak belirtilen bilgileri çıkaracaktır
    4. Sonuçları Excel formatında indirin
    5. 'Veri Analizi' sayfasından detaylı analizleri görüntüleyin

    **📋 Çıkarılan Bilgiler:**
    - **Geri Yükleme Zamanı** - Rapor tarihi ve zaman bilgisi
    - **Yapılan İşlemler** - Gerçekleştirilen servis işlemleri
    - **Ürün Numarası** - Ürün model ve part numarası
    - **Müşteri Firma** - Müşteri firma adı
    - **Müşteri Konumu** - Lokasyon ve adres bilgisi
    - **Servis Uzmanı** - Servisi yapan teknisyen
    - **Sonuç** - İşlem sonucu ve değerlendirme
    - **Ekipman No** - Ekipman numarası (varsa)

    🌐 **Desteklenen Diller:** Türkçe & İngilizce başlıklar otomatik tanınır
    """)
