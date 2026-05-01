# KeyPatternVerify

Keystroke Dynamics ile Kimlik Dogrulama

Bu proje CMU Keystroke Dynamics Benchmark Dataset uzerinde davranissal biyometri ile kimlik dogrulama yapar. Varsayilan model, her kullanici icin ayri egitilen one-class k-NN anomalilik skorlayicisidir.

CMU veri setinde 51 kullanici, `.tie5Roanl` parolasini 8 oturumda toplam 400 kez yazmistir. Resmi protokole uygun olarak her hedef kullanici icin ilk 200 ornek egitimde, son 200 gercek kullanici testi icin, diger kullanicilarin ilk 5 ornegi ise sahte giris testi icin kullanilir.

## Kurulum

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
```

Kisa yol:

```powershell
python scripts/install_requirements.py
```

## Veri Setini Indirme

```powershell
python -m keystroke_auth.cli download --output data/DSL-StrongPasswordData.csv
```

Kisa yol:

```powershell
python scripts/download_dataset.py
```

Bu komut dosyayi CMU kaynagindan indirir ve resmi MD5 ozetiyle dogrular.

## Yerel Web Arayuzu

Tarayici tabanli arayuz FastAPI ile yerelde calisir. Ana ekran ozel parola
profili olusturma ve dogrulama akisini gosterir. CMU veri seti, k-NN ayarlari,
FAR/FRR/EER grafikleri ve akademik degerlendirme tablolari `Evaluation /
Research Mode` bolumunun altindadir.

```powershell
python scripts/run_ui.py
```

Sonra tarayicida acin:

```text
http://127.0.0.1:8000
```

Canli test bolumu `.tie5Roanl` ve Enter dizisini bekler. Tarayici tus basma ve
birakma zamanlarini olcer, FastAPI arka ucu mevcut k-NN modelini egitir, skoru
hesaplar ve esige gore kabul/ret karari dondurur.

### Ozel Parola ile Kayit ve Dogrulama

Web arayuzundeki `Custom Password Profiles` bolumu, CMU veri setinden bagimsiz
yerel profil olusturur.

Akis:

1. Profil adini ve istediginiz parolayi girin.
2. `Samples` alaninda kac kayit denemesi alinacagini secin.
3. `Start Enroll` ile parolayi ayni kullaniciya birden cok kez yazdirin.
4. Yeterli ornekten sonra `Save Profile` ile profili kaydedin.
5. `Saved Profile` listesinden profili secip `Start Verify` ile baska
   kisilerin ayni parolayi denemesini saglayin.

Ozel profiller `models/custom_profiles.json` dosyasinda yerel olarak saklanir.
Bu dosya parola ve klavye zamanlama verisi icerdigi icin `.gitignore` icindedir.

## k-NN Degerlendirme

```powershell
python -m keystroke_auth.cli evaluate `
  --data data/DSL-StrongPasswordData.csv `
  --features all `
  --k 5 `
  --output reports/knn_results.csv
```

Kisa yol:

```powershell
python scripts/evaluate_knn.py
```

Oznitelik secenekleri:

- `hold`: yalnizca tus basili kalma sureleri (`H.*`)
- `dwell`: `hold` ile ayni anlamda tutulur
- `latency`: digraph sureleri (`DD.*` ve `UD.*`)
- `all`: tum zamanlama oznitelikleri

Cikti metrikleri:

- `FAR`: sahte kullanicinin kabul edilme orani
- `FRR`: gercek kullanicinin reddedilme orani
- `EER`: FAR ve FRR'nin esitlendigi yaklasik hata orani

## Gercek Zamanli Senaryo

Veri setinden satirlari sirayla akitip canli karar verme davranisini gormek icin:

```powershell
python -m keystroke_auth.cli realtime-sim `
  --data data/DSL-StrongPasswordData.csv `
  --subject s002 `
  --attempts 12 `
  --delay 0.25
```

Kisa yol:

```powershell
python scripts/realtime_sim.py --subject s002
```

Testleri calistirmak icin:

```powershell
python scripts/run_tests.py
```

k-NN sonuclarindan grafik uretmek icin:

```powershell
python scripts/plot_knn_results.py
```

Web arayuzundeki canli yakalama bolumu `.tie5Roanl` ve Enter dizisini bekler,
hold/UD/DD oznitelik vektorunu olusturur, egitilmis k-NN modeliyle skoru
hesaplar ve esige gore kabul veya ret karari verir.

## Kaynak

- CMU Keystroke Dynamics Benchmark Dataset: https://www.cs.cmu.edu/~keystroke/
