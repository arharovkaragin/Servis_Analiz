# PDF Analiz ve Excel Çıktı Uygulaması

Bu uygulama PDF dosyalarınızı analiz ederek istediğiniz bilgileri çıkarır ve Excel formatında kaydeder.

## 🌟 Özellikler

- **PDF Analiz**: Çoklu PDF yükleme ve otomatik veri çıkarma
- **Veri Analizi**: İnteraktif dashboard ile detaylı analizler
- **Excel Export**: Sonuçları Excel formatında indirme
- **Türkçe/İngilizce Destek**: Çok dilli başlık tanıma

## 📊 Analiz Verileri

- Geri Yükleme Zamanı
- Yapılan İşlemler
- Ürün Numarası
- Müşteri Firma
- Müşteri Konumu
- Servis Uzmanı
- Sonuç
- Ekipman No

## 🔧 Kurulum

1. Repository'yi klonlayın
2. Gerekli paketleri yükleyin: `pip install -r requirements.txt`
3. OpenAI API anahtarınızı `.env` dosyasına ekleyin
4. Uygulamayı çalıştırın: `streamlit run app.py`

## 🌐 Live Demo

[Streamlit Cloud'da Canlı Demo](https://your-app-url.streamlit.app)

## 📋 Gereksinimler

- Python 3.8+
- OpenAI API Key
- Streamlit
- PyPDF2
- Pandas
- Plotly

## 🔐 API Key Kurulumu

1. `.env` dosyası oluşturun
2. `OPENAI_API_KEY=your_api_key_here` ekleyin
3. Streamlit Cloud'da Secrets bölümünden API key'i ekleyin

## 📈 Dashboard Özellikleri

- Top 10 Müşteri Dağılımı
- Servis Uzmanları Performansı
- Zaman Bazında Trend Analizi
- İş Tipi Kategorileri
- Lokasyon Dağılımı
