# API Sejmu RP - Przewodnik dla SejmBot

## Podstawowe informacje

**Base URL:** `https://api.sejm.gov.pl/`

**Format odpowiedzi:** JSON

**Ograniczenia:** Brak oficjalnych limitów, ale zalecane opóźnienie 1s między zapytaniami

## Kluczowe endpointy dla scrapera

### 1. Lista kadencji

```
GET /sejm/term
```

**Odpowiedź:**

```json
[
  {
    "num": 10,
    "from": "2023-11-13",
    "to": null,
    "current": true
  },
  {
    "num": 9,
    "from": "2019-11-12",
    "to": "2023-11-12",
    "current": false
  }
]
```

### 2. Lista posiedzeń dla kadencji

```
GET /sejm/term{term}/proceedings
```

**Parametry:**

- `term` (int) - numer kadencji (np. 10)

**Przykład:** `/sejm/term10/proceedings`

**Odpowiedź:**

```json
[
  {
    "number": 1,
    "title": "1. Posiedzenie Sejmu RP w dniach 13, 14, 15 listopada 2023 r.",
    "dates": [
      "2023-11-13",
      "2023-11-14",
      "2023-11-15"
    ],
    "current": false
  }
]
```

### 3. Szczegóły posiedzenia

```
GET /sejm/term{term}/proceedings/{id}
```

**Parametry:**

- `term` (int) - numer kadencji
- `id` (int) - numer posiedzenia

**Przykład:** `/sejm/term10/proceedings/1`

### 4. 🎯 **TRANSKRYPTY PDF** - Najważniejsze dla SejmBot

```
GET /sejm/term{term}/proceedings/{id}/{date}/transcripts/pdf
```

**Parametry:**

- `term` (int) - numer kadencji
- `id` (int) - numer posiedzenia
- `date` (YYYY-MM-DD) - data posiedzenia

**Przykład:** `/sejm/term10/proceedings/1/2023-11-13/transcripts/pdf`

**Zwraca:** Plik PDF ze stenogramem całego dnia posiedzenia

### 5. Lista wypowiedzi (metadane)

```
GET /sejm/term{term}/proceedings/{id}/{date}/transcripts
```

**Odpowiedź:**

```json
{
  "proceedingNum": 1,
  "date": "2023-11-13",
  "statements": [
    {
      "num": 1,
      "function": "Marszałek Sejmu",
      "name": "Szymon Hołownia",
      "memberID": 123,
      "startDateTime": "2023-11-13T10:00:00",
      "endDateTime": "2023-11-13T10:05:00",
      "unspoken": false
    }
  ]
}
```

### 6. Pojedyncza wypowiedź HTML

```
GET /sejm/term{term}/proceedings/{id}/{date}/transcripts/{statementNum}
```

**Parametry:**

- `statementNum` (int) - numer wypowiedzi

**Przykład:** `/sejm/term10/proceedings/1/2023-11-13/transcripts/15`

**Zwraca:** HTML z treścią wypowiedzi

### 7. Aktualne posiedzenie

```
GET /sejm/term{term}/proceedings/current
```

**Użycie:** Sprawdzenie czy trwa posiedzenie, pobieranie najnowszych danych

## Strategia scrapowania dla SejmBot

### Algorytm pobierania transkryptów:

1. **Sprawdź dostępne kadencje** - `/sejm/term`
2. **Pobierz listę posiedzeń** - `/sejm/term{term}/proceedings`
3. **Dla każdego posiedzenia:**
    - Pobierz szczegóły posiedzenia
    - **Dla każdej daty posiedzenia:**
        - **Pobierz PDF transkryptu** 📄
        - Opcjonalnie: pobierz metadane wypowiedzi

### Przykład implementacji:

```python
import requests
import time

BASE_URL = "https://api.sejm.gov.pl"


def download_transcript_pdf(term, proceeding_id, date, save_path):
    """Pobiera PDF transkryptu z konkretnego dnia posiedzenia"""
    url = f"{BASE_URL}/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/pdf"

    response = requests.get(url, timeout=30)

    if response.status_code == 200:
        filename = f"transkrypt_T{term}_P{proceeding_id}_{date}.pdf"
        filepath = f"{save_path}/{filename}"

        with open(filepath, 'wb') as f:
            f.write(response.content)

        return filepath
    else:
        print(f"Błąd {response.status_code}: {url}")
        return None


def get_proceedings_for_term(term):
    """Pobiera listę wszystkich posiedzeń dla kadencji"""
    url = f"{BASE_URL}/sejm/term{term}/proceedings"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    return []


# Przykład użycia
term = 10
proceedings = get_proceedings_for_term(term)

for proceeding in proceedings:
    proc_id = proceeding['number']
    dates = proceeding['dates']

    for date in dates:
        print(f"Pobieram: kadencja {term}, posiedzenie {proc_id}, dzień {date}")

        pdf_path = download_transcript_pdf(term, proc_id, date, "transkrypty")

        if pdf_path:
            print(f"✅ Zapisano: {pdf_path}")

        # Rate limiting - ważne!
        time.sleep(1)
```

## Dodatkowe przydatne endpointy

### Informacje o posłach

```
GET /sejm/term{term}/MP
GET /sejm/term{term}/MP/{id}
```

**Zastosowanie:** Identyfikacja mówców w transkryptach, dodatkowe metadane

### Kluby parlamentarne

```
GET /sejm/term{term}/clubs
GET /sejm/term{term}/clubs/{id}
```

**Zastosowanie:** Klasyfikacja wypowiedzi według przynależności politycznej

### Głosowania

```
GET /sejm/term{term}/votings/{sitting}
GET /sejm/term{term}/votings/{sitting}/{num}
```

**Zastosowanie:** Kontekst dla wypowiedzi, dodatkowe źródło "dramatycznych momentów"

## Struktura folderów dla scrapera

```
transkrypty_sejm/
├── kadencja_10/
│   ├── posiedzenie_001/
│   │   ├── 2023-11-13_transkrypt.pdf
│   │   ├── 2023-11-14_transkrypt.pdf
│   │   └── metadata.json
│   └── posiedzenie_002/
│       └── ...
└── kadencja_9/
    └── ...
```

## Najlepsze praktyki

1. **Rate Limiting:** 1 sekunda między zapytaniami minimum
2. **Error Handling:** API może być niedostępne, timeout 30s
3. **Incremental Updates:** Sprawdzaj `lastModified` w metadanych
4. **Caching:** PDF-y się nie zmieniają, pobierz raz
5. **Logging:** Loguj wszystkie operacje dla debugowania

## Potencjalne rozszerzenia

- **Interpelacje** (`/interpellations`) - dodatkowe źródło "śmiesznych" treści
- **Komisje** (`/committees`) - posiedzenia komisji też mają transkrypty
- **Druki sejmowe** (`/prints`) - projekty ustaw z kontekstem

## Format danych dla SejmBot

Po pobraniu PDF-ów, przekaż je do detektora fragmentów:

```python
from SejmBotDetektor.detector import FragmentDetector

detector = FragmentDetector()
results = detector.process_folder("transkrypty_sejm/kadencja_10/")
```

## Monitorowanie nowych posiedzeń

```python
def check_for_new_proceedings():
    current_proceeding = requests.get(f"{BASE_URL}/sejm/term10/proceedings/current")

    if current_proceeding.status_code == 200:
        proc_data = current_proceeding.json()
        # Sprawdź czy to nowe posiedzenie
        # Pobierz transkrypty gdy się zakończy
```

---

**Uwaga:** API Sejmu RP jest publiczne i darmowe, ale używaj go odpowiedzialnie. Wszystkie transkrypty są w domenie
publicznej.