<div align="center">

<img src="assets/mercatcher.png" alt="Mercatcher Logo" width="130" style="border-radius: 26px; box-shadow: 0 8px 32px rgba(2, 132, 199, 0.45); margin-bottom: 12px;" />

# ⚡ Mercatcher
### Yeni Nesil Toplu Medya & Dosya İndirici (Bulk Media Downloader Pro)

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)
[![UI](https://img.shields.io/badge/UI-Cyberpunk%20Dark%20Glass-0284c7?style=for-the-badge)](ui/)

**Mercatcher**, popüler dosya ve medya barındırma servislerindeki tekil bağlantıları veya devasa albümleri tek tıkla analiz eden, kuyruğa alan ve yüksek hızda toplu olarak indiren modern bir masaüstü uygulamasıdır.

</div>

---

## 🌟 Öne Çıkan Özellikler

- 🌐 **Otomatik Servis Tespiti:** 11+ popüler medya ve bulut depolama servisini URL'den otomatik algılar, ilgili motora yönlendirir.
- ⚡ **Çok İş Parçacıklı (Multi-threaded) İndirme:** Ayarlanabilir eşzamanlı indirme sayısı (1-5 thread) ile internet bant genişliğini maksimum verimle kullanır.
- 🔄 **Yarıda Kalanı Sürdürme (Resume / .part):** Bağlantı kopsa veya program kapatılsa bile indirilen baytlar korunur, baştan başlamak yerine kaldığı yerden devam eder.
- 🌍 **Çoklu Dil Desteği (7 Dil):** Türkçe, İngilizce, Basitleştirilmiş Çince, İspanyolca, Felemenkçe, Almanca ve Portekizce. Sistem dilini otomatik algılar, desteklenmeyen dillerde otomatik İngilizce açılır.
- 🎨 **Modern Cyberpunk Glassmorphic Arayüz:** Koyu neon temalı, çift başlıktan arındırılmış, anlık hız ve disk alanı göstergeli şık masaüstü deneyimi.
- 🔒 **İstemci Taraflı Şifre Çözücü (MEGA):** MEGA dosyalarını sunucudan çekerken anlık olarak akış halinde (streaming AES-128-CTR) çözer ve diske yazar.
- 📦 **Bağımsız `.exe` Desteği:** PyInstaller ile tek tıkla taşınabilir (portable), Python gerektirmeyen masaüstü programı haline getirilebilir.

---

## 🚀 Desteklenen Platformlar

| Platform | Format & Yetenekler | Çözümleme Yöntemi |
| :--- | :--- | :--- |
| **GoFile** (`gofile.io`) | Tekil dosyalar, klasörler ve alt klasörler | Dinamik SHA-256 `X-Website-Token` ve oturum token motoru |
| **Bunkr** (`.si`, `.is`, `.cr`, `.to`, `.black`, `.ws`, `.ac` vb.) | Albümler (`/a/`), videolar (`/v/`), görseller (`/i/`), indirmeler (`/d/`) | Çoklu sayfa ayrıştırıcı ve CDN yönlendirici |
| **Balbums** (`balbums.st`, `balbums.org`) | Bunkr albüm indeksleri ve doğrudan medya listeleri | Albüm ve doğrudan medya tespit motoru |
| **Pixeldrain** (`pixeldrain.com`) | Tekil dosyalar (`/u/`) ve albümler/listeler (`/l/`) | Resmi JSON REST API entegrasyonu |
| **KrakenFiles** (`krakenfiles.com`) | Tekil büyük dosyalar ve arşivler | Dinamik token ve hash el sıkışmasıyla doğrudan CDN çekimi |
| **CyberFile** (`cyberfile.me`, `cyberfile.is`) | Tekil dosyalar ve paylaşılan klasörler (`/folder/`) | Tokenli ve şifreli indirme bağlantısı ayrıştırma |
| **Filester** (`filester.me`, `filester.net`) | Sayfalandırmalı genel klasörler (`/f/`) ve dosyalar (`/d/`) | Sayfa tarayıcı (crawler) ve otomatik sayfalama |
| **MEGA** (`mega.nz`, `mega.io`) | Tekil dosyalar ve klasörler (`/file/`, `/folder/`) | İstemci tarafında AES-128-CTR akış deşifreleme |
| **MixDrop** (`mixdrop.co`, `mixdrop.sx`, `mixdrop.to` vb.) | Stream videoları ve dosyalar | Dahili Dean Edwards Packer (p,a,c,k,e,d) JS açıcı |
| **DoodStream** (`dood.to`, `doodstream.com`, `ds2play.com` vb.) | Video akışları ve indirmeleri | `pass_md5` anahtar üretimi ve zaman damgalı tokenlama |
| **FileMoon** (`filemoon.sx`, `filemoon.to`, `filemoon.in` vb.) | Gömülü video sayfaları | Packed JS çözümlemesi ile doğrudan akış çekimi |
| **Doğrudan Linkler** | `.mp4`, `.zip`, `.mkv`, `.jpg` vb. her türlü doğrudan URL | Akıllı dosya adı tespiti ile doğrudan indirme |

---

## 🛠️ Kurulum & Çalıştırma

### Yöntem 1: Tek Tıkla Masaüstü Uygulaması Olarak Çalıştırma (Önerilen)
Python kurulu sisteminizde herhangi bir komut girmeden:
1. `start_mercatcher.bat` dosyasına **çift tıklayın**.
2. Uygulama bağımsız pencere modunda açılacaktır.

---

### Yöntem 2: Kaynak Koddan Çalıştırma

1. **Depoyu klonlayın:**
   ```bash
   git clone https://github.com/KULLANICI_ADINIZ/Mercatcher.git
   cd Mercatcher
   ```

2. **Gereksinimleri yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Uygulamayı başlatın:**
   - **Grafik Arayüz (GUI):**
     ```bash
     python mercatcher_gui.py
     ```
   - **Komut Satırı Modu (CLI):**
     ```bash
     python mercatcher_cli.py https://gofile.io/d/XXXXXX https://bunkr.si/a/YYYYYY
     ```

---

### Yöntem 3: Tek Parça `.exe` (Taşınabilir Sürüm) Oluşturma

Python kurulu olmayan bilgisayarlarda da çalıştırmak için:
1. `build_exe.bat` dosyasını çalıştırın.
2. PyInstaller otomatik olarak Rust/C kütüphanelerini, WebView bileşenlerini ve arayüzü paketler.
3. Çıktı: `dist/Mercatcher.exe` konumunda tek parça olarak hazır olur!

---

## 📂 Proje Dizin Yapısı

```
Mercatcher/
│
├── core/                       # Çekirdek İndirme ve Çıkarıcı Modülleri
│   ├── __init__.py             # Modül dışa aktarımları
│   ├── config.py               # Servisler, domain listeleri ve sabitler
│   ├── utils.py                # Güvenli dosya adı, token yönetimi
│   ├── js_unpacker.py          # Dean Edwards JS açıcı (MixDrop, FileMoon)
│   ├── engine.py               # Multi-threaded download & resume motoru
│   ├── gofile.py               # GoFile X-Website-Token & API motoru
│   ├── bunkr.py                # Bunkr & Balbums çoklu sayfa çıkarıcısı
│   ├── pixeldrain.py           # Pixeldrain API motoru
│   ├── krakenfiles.py          # KrakenFiles token çözücü
│   ├── cyberfile.py            # CyberFile klasör & dosya ayrıştırıcı
│   ├── filester.py             # Filester sayfalandırma tarayıcısı
│   ├── mega.py                 # MEGA istemci taraflı AES-CTR şifre çözücü
│   ├── mixdrop.py              # MixDrop video akış çıkarıcı
│   ├── doodstream.py           # DoodStream pass_md5 çözücü
│   └── filemoon.py             # FileMoon video yakalayıcı
│
├── ui/                         # Arayüz Dosyaları
│   └── index.html              # Modern Cyberpunk Dark Glass Arayüz (HTML5/CSS3/JS)
│
├── server.py                   # Sıfır harici bağımlılıklı yerel HTTP API sunucusu
├── mercatcher_gui.py           # Native masaüstü başlatıcı (pywebview & Edge app)
├── mercatcher_cli.py           # Hızlı terminal arayüzü
├── start_mercatcher.bat        # Windows tek tık başlatıcı
├── build_exe.bat               # Windows tek tık PyInstaller EXE derleyici
├── requirements.txt            # Python bağımlılıkları
├── .gitignore                  # Git hariç tutma kuralları
└── README.md                   # Dokümantasyon
```

---

## ⚙️ Yapılandırma ve İpuçları

- **İndirme Klasörü:** Arayüz üzerinden tek tıkla istediğiniz klasörü seçebilir veya sağ üstten doğrudan klasörü açabilirsiniz.
- **Eşzamanlı Bağlantı (Threads):** Ağ hızınıza göre 1 ile 5 arasında anlık dosya indirme limiti belirleyebilirsiniz.
- **Bağlantılar Arası Bekleme (Delay):** Sunucu taraflı rate limit (istek sınırı) engellerine takılmamak için linkler arası bekleme süresini (1-15 sn) ayarlayabilirsiniz.
- **GoFile Tokeni:** GoFile misafir kullanıcıları IP bazlı sınırlayabilir. Arayüzün Ayarlar sekmesinden ücretsiz GoFile hesabınızın API tokenini girerek sınırsız indirme yapabilirsiniz.

---

## ⚖️ Yasal Uyarı & Lisans

Bu yazılım yalnızca eğitim ve kişisel arşivleme amacıyla geliştirilmiştir. Kullanıcıların telif hakkı ile korunan veya üçüncü taraf hizmet şartlarını ihlal eden içerikleri indirmesi geliştiricinin sorumluluğunda değildir.

Bu proje **MIT Lisansı** ile lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakabilirsiniz.
