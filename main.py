import time
import json
import re
import sqlite3
from playwright.sync_api import sync_playwright, TimeoutError

DB_FILE = "ihaleler.db"

def setup_database():
    # ... (değişiklik yok)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ihaleler (
        ikn TEXT PRIMARY KEY, ihale_adi TEXT, idare TEXT, yer TEXT,
        tarih TEXT, etiketler TEXT, kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
    print(f"'{DB_FILE}' veritabanı hazır.")

def get_existing_ikns():
    # ... (değişiklik yok)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ikn FROM ihaleler")
    ikns = {row[0] for row in cursor.fetchall()}
    conn.close()
    print(f"Veritabanında {len(ikns)} mevcut kayıt bulundu.")
    return ikns

def insert_new_tenders(tenders_list):
    # ... (değişiklik yok)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for tender in tenders_list:
        cursor.execute("""
        INSERT OR IGNORE INTO ihaleler (ikn, ihale_adi, idare, yer, tarih, etiketler)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tender['ikn'], tender['ihale_adi'], tender['idare'],
            tender['yer'], tender['tarih'], json.dumps(tender['etiketler'])
        ))
    conn.commit()
    conn.close()

def scrape_and_update_db(yil, alim_turleri, ihale_durumu_listesi):
    existing_ikns = get_existing_ikns()
    
    with sync_playwright() as p:
        # GITHUB ACTIONS İÇİN DEĞİŞİKLİK: headless=True olmalı
        browser = p.chromium.launch(headless=True, slow_mo=50) 
        page = browser.new_page()

        try:
            print("Sayfa açılıyor...")
            page.goto("https://ekapv2.kik.gov.tr/ekap/search", timeout=60000)
            page.wait_for_load_state('networkidle')
            print("Sayfa başarıyla açıldı.")

            # ... (Filtreleme kodunun geri kalanı tamamen aynı) ...
            print("\n--- Filtreler Uygulanıyor ---")
            page.locator("#ikn-yil").click()
            page.locator(f".dx-list-item-content:text-is('{yil}')").click()
            
            aktif_butonlar = page.locator("button.filter-button.active")
            for _ in range(aktif_butonlar.count()):
                aktif_butonlar.nth(0).click()
            
            for tur in alim_turleri:
                page.locator(f"button.filter-button:has-text('{tur}')").click()
            print(f"Alım Türleri seçildi: {', '.join(alim_turleri)}")

            print("\n--- İhale Durumu Seçiliyor ---")
            page.locator("ihale-multiselect-filtre:has-text('İhale Durumu')").click()
            dialog = page.get_by_role("dialog").filter(has=page.get_by_text("Tümünü Seç"))
            dialog.wait_for(state="visible")
            popup_search_box = dialog.get_by_placeholder("Ara")
            for durum in ihale_durumu_listesi:
                popup_search_box.fill(durum)
                dialog.locator(f".dx-list-item-content:text-is('{durum}')").click()
            page.keyboard.press('Escape')

            print("\nAna 'Filtrele' butonuna basılıyor...")
            page.locator("#search-ihale").click()
            
            page.wait_for_selector("div#ihale-list", timeout=60000)
            print("Sonuçlar yüklendi.")

            page.locator('dx-select-box[title="Gösterilecek Kayıt Sayısı"]').click()
            page.locator(".dx-list-item-content:text-is('50')").click()
            page.wait_for_selector("div.pc-card", timeout=30000)
            print("Sayfa başına 50 kayıt ile liste güncellendi.")

            page_info_element = page.locator("p:has-text('Sayfa')")
            page_text = page_info_element.inner_text()
            total_pages_match = re.search(r'\d+', page_text)
            total_pages = int(total_pages_match.group(0)) if total_pages_match else 1
            print(f"Toplam {total_pages} sayfa bulundu.")
            
            new_tenders = []
            stop_scraping = False

            for current_page in range(1, total_pages + 1):
                if stop_scraping:
                    break
                
                print(f"\n--- Sayfa {current_page}/{total_pages} taranıyor... ---")
                page.wait_for_selector("div.pc-card")
                ilanlar = page.locator("div.pc-card").all()
                
                for ilan in ilanlar:
                    try:
                        ikn = ilan.locator(".ikn").inner_text()
                        if ikn in existing_ikns:
                            print(f"Mevcut ihale bulundu (IKN: {ikn}). Verimli tarama durduruluyor.")
                            stop_scraping = True
                            break
                        
                        ihale_adi = ilan.locator(".ihale").inner_text()
                        idare = ilan.locator(".idare").inner_text()
                        yer_ve_tarih_str = ilan.locator(".first-row .il-saat").inner_text()
                        yer, tarih = ("Belirtilmemiş", "Belirtilmemiş")
                        if "," in yer_ve_tarih_str:
                            parcalar = yer_ve_tarih_str.split(",", 1)
                            yer, tarih = parcalar[0].strip(), parcalar[1].strip()
                        else:
                            yer = yer_ve_tarih_str.strip()
                        etiketler = [etiket.inner_text() for etiket in ilan.locator(".badges .badge").all()]
                        
                        new_tenders.append({
                            "ikn": ikn, "ihale_adi": ihale_adi, "idare": idare,
                            "yer": yer, "tarih": tarih, "etiketler": etiketler
                        })

                    except Exception as e:
                        print(f"Bir ilan okunurken hata oluştu: {e}")
                
                if not stop_scraping and current_page < total_pages:
                    next_page_button = page.locator('dx-button[title="İleri"]')
                    if next_page_button.is_enabled():
                        print("Sonraki sayfaya geçiliyor...")
                        next_page_button.click()
                        page.locator(f'dx-number-box input[aria-valuenow="{current_page + 1}"]').wait_for()
                    else:
                        break
            
            print("\nTarama tamamlandı!")
            if new_tenders:
                insert_new_tenders(new_tenders)
                print(f"Başarılı! {len(new_tenders)} YENİ ihale veritabanına eklendi.")
            else:
                print("Yeni ihale bulunamadı.")
            
            # GITHUB ACTIONS İÇİN DEĞİŞİKLİK: input satırını kaldırıyoruz.

        except TimeoutError as e:
            print(f"Zaman aşımı hatası: {e}")
        except Exception as e:
            print(f"Beklenmedik bir hata oluştu: {e}")
        finally:
            if 'browser' in locals() and browser.is_connected():
                browser.close()
                print("\nTarayıcı kapatıldı.")

if __name__ == "__main__":
    setup_database()
    
    aranacak_yil = "2025"
    aranacak_alim_turleri = ["Hizmet","Mal","Danışmanlık","Yapım"]
    aranacak_ihale_durumlari = ["Teklif Vermeye Açık"]

    scrape_and_update_db(aranacak_yil, aranacak_alim_turleri, aranacak_ihale_durumlari)