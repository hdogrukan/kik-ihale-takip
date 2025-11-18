# KAMU İHALE KURUMU(KİK) EKAP İhale Takip ve Kayıt Aracı

Bu proje, **Kamu İhale Kurumu (KİK)** üzerinden günlük olarak ihale ilanlarını tarayıp, yeni bulunan ihaleleri bir **SQLite veritabanına (`ihaleler.db`)** kaydeden basit ama otomatik çalışan bir araçtır.  
GitHub Actions üzerinden zamanlanmış şekilde çalışarak veritabanını düzenli olarak günceller.

---

## Özellikler

- EKAP arama sayfasına Playwright ile otomatik bağlanır.
- Belirli bir **yıl**, **alım türleri** ve **ihale durumları** için filtre uygular.
- Sonuçları sayfa sayfa gezerek ihale kartlarını okur.
- Her ilan için aşağıdaki alanları toplar:
  - `ikn` (ihale kayıt numarası – benzersiz anahtar)
  - `ihale_adi`
  - `idare`
  - `yer`
  - `tarih`
  - `etiketler` (liste olarak, veritabanında JSON string)
- Daha önce kaydedilmiş `ikn` değerlerine sahip ihaleleri **atlar**, sadece yeni kayıtları ekler.
- Veriler yerel bir **SQLite veritabanında** tutulur (`ihaleler.db`).
- GitHub Actions üzerinden otomatik olarak:
  - Betiği çalıştırır,
  - Değişen `ihaleler.db` dosyasını repoya commit/push eder.

---

## Proje Yapısı

- `main.py`  
  İhale tarama, filtreleme ve veritabanı güncelleme işlerinin tamamını yapan ana betik.

- `requirements.txt`  
  Python bağımlılıkları (şu anda sadece `playwright`).

- `ihaleler.db`  
  Çalışma sırasında otomatik oluşturulan **SQLite veritabanı** dosyası.  
  İlk çalıştırmada yoksa otomatik oluşturulur.

- `.github/workflows/scrape.yml`  
  GitHub Actions üzerinde betiğin her gün otomatik çalışmasını sağlayan workflow dosyası.

---

## Kullanılan Teknolojiler

- **Python 3.11+**
- **Playwright for Python**
  - Chromium tarayıcısını headless (görünmez) modda kullanır.
- **SQLite** (`sqlite3` standart kütüphanesi)
- **GitHub Actions** (otomatik zamanlanmış çalıştırma için)

---

## Veritabanı Yapısı

`main.py` içindeki `setup_database()` fonksiyonu şu tabloyu oluşturur:

- Tablo adı: `ihaleler`
- Sütunlar:
  - `ikn` – `TEXT`, **PRIMARY KEY**
  - `ihale_adi` – `TEXT`
  - `idare` – `TEXT`
  - `yer` – `TEXT`
  - `tarih` – `TEXT`
  - `etiketler` – `TEXT` (JSON string; Python tarafında listeden `json.dumps()` ile kaydediliyor)
  - `kayit_tarihi` – `TIMESTAMP`, varsayılan `CURRENT_TIMESTAMP`

Aynı `ikn`'ye sahip ilanlar için **`INSERT OR IGNORE`** kullanıldığı için, veritabanında tekrar eden kayıt oluşmaz.

---

## Kurulum (Yerel Geliştirme Ortamı)

### 1. Python ve sanal ortam

1. Python 3.11 veya üzeri bir sürüm kurulu olduğundan emin olun.
2. Depoyu yerel makinenize klonlayın veya proje klasörüne girin.
3. (İsteğe bağlı ama tavsiye edilir) Sanal ortam oluşturun:

```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
# veya
venv\Scripts\activate          # Windows
```

### 2. Bağımlılıkların kurulumu

Proje kök dizininde:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Playwright tarayıcılarının kurulumu

Playwright Python kütüphanesini kurduktan sonra, Chromium tarayıcısını da indirmek gerekir:

```bash
python -m playwright install
```

Linux sunucularda eksik sistem bağımlılıkları varsa:

```bash
python -m playwright install --with-deps
```

komutu tercih edilebilir.

---

## Çalıştırma

Yerel ortamda betiği çalıştırmak için:

```bash
python main.py
```

İlk çalıştırmada:

- `ihaleler.db` dosyası oluşturulur,
- `ihaleler` tablosu yoksa oluşturulur,
- EKAP üzerinden filtrelenmiş ihaleler taranır,
- Veritabanında bulunmayan `ikn` değerleri için yeni satırlar eklenir.

`main.py` dosyasının sonunda yer alan:

```python
if __name__ == "__main__":
    setup_database()
    
    aranacak_yil = "2025"
    aranacak_alim_turleri = ["Hizmet","Mal","Danışmanlık","Yapım"]
    aranacak_ihale_durumlari = ["Teklif Vermeye Açık"]

    scrape_and_update_db(aranacak_yil, aranacak_alim_turleri, aranacak_ihale_durumlari)
```

bloğu, betiğin çalıştırıldığında hangi filtrelerle tarama yapacağını belirler.

---

## Filtreleme Mantığı (`main.py`)

`scrape_and_update_db(yil, alim_turleri, ihale_durumu_listesi)` fonksiyonu kısaca şu adımları izler:

1. **Mevcut kayıtların çekilmesi**
   - `get_existing_ikns()` fonksiyonu ile veritabanından tüm `ikn` değerleri set olarak alınır.

2. **Playwright ile tarayıcı açılması**
   - `sync_playwright()` kullanılarak Chromium headless modda açılır.
   - `locale="tr-TR"`, `timezone_id="Europe/Istanbul"`, uygun `user_agent` ve `Accept-Language` başlıkları ayarlanır.

3. **EKAP arama sayfasına gitme**
   - `page.goto("https://ekapv2.kik.gov.tr/ekap/search", timeout=60000)` ile sayfa açılır.
   - `page.wait_for_load_state('networkidle')` ile tam yüklenmesi beklenir.

4. **Filtrelerin uygulanması**
   - Yıl seçimi: `#ikn-yil` alanına tıklanır ve ilgili yıl seçilir.
   - Aktif filtre butonları temizlenir.
   - `alim_turleri` listesindeki her bir tür için butonlara tıklanır (Örn. `"Hizmet"`, `"Mal"`, `"Danışmanlık"`, `"Yapım"`).
   - İhale durumu filtresi için:
     - `ihale-multiselect-filtre:has-text('İhale Durumu')` bileşeni açılır.
     - Açılan diyalog içindeki arama kutusuna her bir `ihale_durumu` tek tek yazılıp seçilir.
     - `Escape` ile diyalog kapatılır.

5. **Arama ve listeleme**
   - Ana `#search-ihale` butonuna tıklanır.
   - `div#ihale-list` yüklenmesi beklenir.
   - `Gösterilecek Kayıt Sayısı` seçeneği `50` olarak ayarlanır.

6. **Sayfa sayısının tespiti**
   - "Sayfa X / Y" yazan metin bulunur.
   - `re.findall` ile rakamlar çekilir; son değer toplam sayfa sayısı olarak kullanılır.

7. **Sayfa sayfa ilanların toplanması**
   - Her sayfada:
     - `div.pc-card` elemanları alınır.
     - Her kart için:
       - `.ikn`, `.ihale`, `.idare`, `.first-row .il-saat`, `.badges .badge` alanları okunur.
       - `yer` ve `tarih`, virgülle ayrılmış metinden bölünerek elde edilir.
       - `ikn` veritabanındaki mevcut set içinde ise **atlanır**.
       - Aksi durumda `new_tenders` listesine eklenir.
   - Eğer bir sonraki sayfa varsa `İleri` (`dx-button[title="İleri"]`) butonuna tıklanır ve devam edilir.

8. **Veritabanına yazma**
   - Tüm sayfalar tarandıktan sonra `insert_new_tenders(new_tenders)` çağrılır.
   - Fonksiyon, eklemeden önce/sonra satır sayısını karşılaştırarak kaç yeni kayıt eklendiğini ekrana yazar.

9. **Kapatma**
   - Her durumda (hata olsa dahi) tarayıcı ve context güvenli şekilde kapatılır.

---

## GitHub Actions ile Otomatik Çalıştırma

`.github/workflows/scrape.yml` dosyası, bu betiğin GitHub üzerinde otomatik çalışmasını sağlar.

Önemli noktalar:

- **Zamanlama**
  - `schedule` altında `cron: '0 5 * * *'` tanımlıdır.
  - Bu, her gün **05:00 UTC** (Türkiye saatiyle yaklaşık **08:00**) çalışacağı anlamına gelir.
  - Ayrıca `workflow_dispatch` ile manuel tetikleme de mümkündür.

- **Adımlar**
  1. Reponun klonlanması (`actions/checkout@v3`)
  2. Python 3.11 kurulumu (`actions/setup-python@v4`)
  3. Python bağımlılıklarının kurulması (`pip install -r requirements.txt`)
  4. Playwright tarayıcılarının kurulması (`python -m playwright install --with-deps`)
  5. `python main.py` komutuyla betiğin çalıştırılması
  6. `ihaleler.db` dosyasında değişiklik varsa:
     - `git add ihaleler.db`
     - Zaman damgalı bir commit mesajı ile commit
     - `GITHUB_TOKEN` kullanılarak ilgili dala push
     - Değişiklik yoksa commit atlanır.

Bu sayede veritabanı dosyası repoda her gün otomatik olarak güncellenmiş olur.

---

## Verileri Sorgulama Örnekleri

Veritabanını Python veya herhangi bir SQLite aracı ile okuyabilirsiniz.

### Python ile

```python
import sqlite3, json

conn = sqlite3.connect("ihaleler.db")
cursor = conn.cursor()

cursor.execute("SELECT ikn, ihale_adi, idare, yer, tarih, etiketler FROM ihaleler ORDER BY kayit_tarihi DESC LIMIT 10")
for row in cursor.fetchall():
    ikn, ihale_adi, idare, yer, tarih, etiketler_json = row
    etiketler = json.loads(etiketler_json) if etiketler_json else []
    print(ikn, ihale_adi, idare, yer, tarih, etiketler)

conn.close()
```

### Komut satırından (SQLite CLI ile)

```bash
sqlite3 ihaleler.db
sqlite> .headers on
sqlite> .mode column
sqlite> SELECT ikn, ihale_adi, tarih FROM ihaleler ORDER BY kayit_tarihi DESC LIMIT 20;
```

---

## Özelleştirme Önerileri

- Farklı yıllar veya alım türleri için:
  - `main.py` içindeki `aranacak_yil`, `aranacak_alim_turleri`, `aranacak_ihale_durumlari` listelerini düzenleyebilirsiniz.
- Veritabanına ek sütunlar eklemek istiyorsanız:
  - `setup_database()` fonksiyonundaki tablo şemasını,
  - `insert_new_tenders()` fonksiyonundaki `INSERT` sorgusunu,
  - `scrape_and_update_db()` fonksiyonundaki veri toplama kısmını birlikte güncellemeniz gerekir.

---

## Katkı ve Geliştirme

- Hatalar, öneriler veya yeni özellik fikirleri için issue açabilir veya pull request gönderebilirsiniz.
- Otomatik testler veya ek loglama ihtiyaçlarınıza göre `main.py` içine ek çıktılar veya istatistikler ekleyebilirsiniz.

