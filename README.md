# KAMU İHALE KURUMU(KİK) EKAP İhale Takip ve Kayıt Aracı

Bu proje, **Kamu İhale Kurumu (KİK)** üzerinden günlük olarak ihale ilanlarını tarayıp, yeni bulunan ihaleleri bir **SQLite veritabanına (`ihaleler.db`)** kaydeden basit ama otomatik çalışan bir araçtır.  
Linux sunucuda zamanlanmış şekilde çalışıp veritabanı değiştiğinde GitHub reposuna commit/push eder.

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
- Linux sunucuda `cron` ile otomatik çalıştırmaya uygundur.
- Değişen `ihaleler.db` dosyasını commit/push etmek için hazır script içerir.

---

## Proje Yapısı

- `main.py`  
  İhale tarama, filtreleme ve veritabanı güncelleme işlerinin tamamını yapan ana betik.

- `requirements.txt`  
  Python bağımlılıkları (şu anda sadece `playwright`).

- `ihaleler.db`  
  Çalışma sırasında otomatik oluşturulan **SQLite veritabanı** dosyası.  
  İlk çalıştırmada yoksa otomatik oluşturulur.

- `run_scrape_and_push.sh`  
  Betiği çalıştırır, `ihaleler.db` değiştiyse commit atar ve GitHub'a push eder.

---

## Kullanılan Teknolojiler

- **Python 3.11+**
- **Playwright for Python**
  - Chromium tarayıcısını headless (görünmez) modda kullanır.
- **SQLite** (`sqlite3` standart kütüphanesi)
- **Cron** (Linux sunucuda zamanlanmış çalıştırma için)
- **Git** (değişen `ihaleler.db` dosyasını commit/push etmek için)

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
    
    aranacak_yil = time.strftime("%Y")
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

## Linux Sunucuda Otomatik Çalıştırma (22:00)

Bu projede GitHub Actions yerine Linux sunucuda `cron` kullanabilirsiniz.

### 1. Sunucu hazırlığı

```bash
git clone <repo-url>
cd kik-ihale-takip

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install --with-deps
```

### 2. GitHub push yetkisi

Sunucuda repoya push atabilmek için SSH anahtarını veya PAT erişimini ayarlayın.  
SSH ile kontrol için:

```bash
ssh -T git@github.com
```

### 3. Scripti test et

```bash
./run_scrape_and_push.sh
```

Bu script:

1. `python main.py` çalıştırır.
2. `ihaleler.db` değiştiyse commit atar.
3. Aktif branche `origin` üzerinden push eder.

### 4. Her gün 22:00'de çalıştırma (cron)

`crontab -e` ile aşağıdaki satırları ekleyin:

```cron
CRON_TZ=Europe/Istanbul
0 22 * * * cd /path/to/kik-ihale-takip && ./run_scrape_and_push.sh >> /var/log/kik-ihale.log 2>&1
```

- `CRON_TZ=Europe/Istanbul` satırı, cron saatini Türkiye saatine sabitler.
- Log dosyasını (`/var/log/kik-ihale.log`) ihtiyacınıza göre değiştirebilirsiniz.

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
