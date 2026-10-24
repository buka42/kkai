# Protokół badania

Wersja 1.0 z 24.10.2026, zamrożona 24.10.2026 (tag `v1.0-freeze` w repozytorium `kkai`, przed generowaniem 640 obrazów). Treść jak w wersji roboczej 0.9.5 z 22.10.2026; zmiana: data zamrożenia 24.10 zamiast 29.10 (decyzja Piotra 24.10). Historia wersji roboczych 0.9–0.9.5 w 08_dziennik_decyzji.md. Każda zmiana po 24.10 to odstępstwo od zamrożonego planu: zapisujemy ją w dzienniku (kolumna „Odstępstwo”: tak) i opisujemy w artykule.

## 1. Przedmiot, pytania, hipotezy

Tytuł roboczy: *Multiculturalism in the past tense? Heritage, religion and generative images of Kraków and Kazimierz.*

Temat: temporalizacja różnorodności kulturowej i religijnej w obrazach z generatorów, na przykładzie Krakowa i Kazimierza.

Przedmiot: 2 systemy generowania obrazów dostępne przez API, razem z ich warstwą modelu językowego i moderacją. Nie badamy „czystego” modelu dyfuzyjnego, tylko systemy, z których korzystają ludzie.

Jednostka analizy: 1 obraz, czyli odpowiedź na 1 żądanie.

Pytanie główne: jak obrazy z 2 generatorów umiejscawiają różnorodność kulturową i religijną Krakowa i Kazimierza w czasie i jak zmienia to słowo „wielokulturowy”.

| Kod | Hipoteza lub pytanie | Porównanie | Wskaźnik (z kodeksu) | Status |
|---|---|---|---|---|
| H1 | „Wielokulturowy” zwiększa odsetek ramy historycznej lub inscenizowanej | W vs B | temporal_frame ∈ {historical, staged_historical} | Konfirmacyjna |
| H2 | Efekt H1 utrzymuje się mimo „dzisiaj” | WT vs T | jak w H1 | Konfirmacyjna |
| H3 | „Wielokulturowy” zwiększa odsetek trybu dziedzictwa lub widowiska | W vs B | mode_of_culture.dominant ∈ {heritage, spectacle} | Konfirmacyjna |
| H4 | Niezgodność z „dzisiaj” jest wyższa dla Kazimierza niż dla Krakowa | T-Z vs T-K | temporal_frame ≠ contemporary | Konfirmacyjna |
| P5 | W jakiej postaci pojawia się religia: budynek, symbol czy praktyka | Wszystkie warunki | religion.form | Eksploracyjne |
| P6 | Czy „wielokulturowy” zmienia medium obrazu (postarzona fotografia, ilustracja) | W vs B, osobno PL i EN | medium ∈ {photo_aged, illustration} | Eksploracyjne |

Wszystkie hipotezy są kierunkowe.

## 2. Macierz i prompty

4 ramowania × 2 skale × 2 języki × 2 generatory × 20 powtórzeń = 640 obrazów. Do tego 32 obrazy pilotażowe, które nie wchodzą do analizy.

Kod warunku: ramowanie (B, W, T, WT) + skala (K = Kraków, Z = Kazimierz) + język (PL, EN) + generator (OA = OpenAI, GG = Google), np. `W-Z-EN-GG`.

| Kod | Polski | Angielski |
|---|---|---|
| B-K | Obraz przedstawiający Kraków. | An image of Kraków. |
| W-K | Obraz przedstawiający wielokulturowy Kraków. | An image of multicultural Kraków. |
| T-K | Obraz przedstawiający Kraków dzisiaj. | An image of Kraków today. |
| WT-K | Obraz przedstawiający wielokulturowy Kraków dzisiaj. | An image of multicultural Kraków today. |
| B-Z | Obraz przedstawiający Kazimierz w Krakowie. | An image of Kazimierz in Kraków. |
| W-Z | Obraz przedstawiający wielokulturowy Kazimierz w Krakowie. | An image of multicultural Kazimierz in Kraków. |
| T-Z | Obraz przedstawiający Kazimierz w Krakowie dzisiaj. | An image of Kazimierz in Kraków today. |
| WT-Z | Obraz przedstawiający wielokulturowy Kazimierz w Krakowie dzisiaj. | An image of multicultural Kazimierz in Kraków today. |

Stałe we wszystkich warunkach: szablon zdania, słowo „obraz/image”, zapis „Kraków” ze znakiem diakrytycznym w obu językach, rozmiar 1024 × 1024 (1:1), 1 obraz na żądanie, brak instrukcji systemowej, brak kontekstu rozmowy.

Uzasadnienia, które trzeba powtórzyć w metodzie:
- „Obraz/image” zamiast „fotografia/photograph” (decyzja 22.10, po pilotażu 1). Medium nie jest narzucone i staje się zmienną wynikową: czas może się pojawić także przez styl (malarstwo, grafika, postarzenie), a nie tylko przez treść kadru. Powód: w pilotażu 1 z „fotografią” wszystkie 32 obrazy były kolorową fotografią, a 31 z 32 miało ramę współczesną; stała „fotografia” wiązała obraz z konwencją współczesnej fotografii turystycznej. Koszt: większy rozrzut stylu, więcej obrazów `illustration` i mniejsza moc dla H1–H4. Polskie „obraz” może silniej niż angielskie *image* sugerować malarstwo, co obciąża porównanie językowe; rozkład medium raportujemy osobno dla PL i EN.
- Zmianę wprowadzono po obejrzeniu pilotażu 1. W artykule piszemy to wprost, a wyniki pilotażu 1 (prompty, kody, rozkład ramy czasowej) idą do materiałów uzupełniających. Pilotaż 2 jest ostatnią zmianą promptów: po nim zmieniamy tylko kodeks i instrukcję (decyzja 22.10, 19:51: prompty v2 ostateczne, bez pilotażu 3).
- Ograniczenie tłumaczenia (pilotaż 2): `illustration` pojawiło się tylko przy promptach polskich (u Ciebie 3 obrazy GG, u modelu 3 GG i 3 OA), przy angielskich ani razu. Polskie „obraz” znaczy także „malowidło”, a *image* jest neutralne. Różnicę PL/EN w medium może więc tłumaczyć samo słowo szablonu, a nie język promptu jako taki. W artykule: ograniczenie tłumaczenia; porównania językowe dla medium tylko eksploracyjnie, a dla H1–H4 kontrola przez analizę wrażliwości bez `illustration`.
- „Dzisiaj”, a nie „współczesny”: angielskie *contemporary* odsyła też do sztuki i architektury.
- „Kazimierz w Krakowie” odróżnia dzielnicę od Kazimierza Wielkiego i Kazimierza Dolnego.
- „Obraz przedstawiający” wymaga biernika. W bierniku „Kazimierz” jako miejsce (rzeczownik nieżywotny) ma formę mianownika, a osoba to „Kazimierza”. Szablon sam ujednoznacznia więc nazwę jako miejsce; „Obraz Kazimierza” czytałoby się jak portret osoby.
- „Kraków” ze znakiem diakrytycznym także w angielskim: forma oficjalna. Dawny egzonim *Cracow* występuje dziś głównie w tekstach historycznych i sam wprowadzałby ramę przeszłości; zapis *Krakow* jest potoczny.
- „Dzisiaj” stoi na końcu zdania w obu językach (okolicznik), więc struktura PL i EN jest równoległa. Przymiotnik „dzisiejszy” dałby w WT „dzisiejszy wielokulturowy Kraków” i rozszedłby się z *Kraków today*.
- W parach minimalnych jedynym słowem kulturowym jest manipulowane „wielokulturowy”. Nazwy grup, religii, symboli i zabytków nie trafiają do promptów. Religia jest wyłącznie zmienną wynikową.
- Nazwa „Kazimierz” niesie silne skojarzenia sama w sobie. To część przedmiotu badania; porównanie z całym Krakowem pozwala ocenić jej wagę.
- Skal nie porównujemy surowo („Kazimierz jest bardziej stereotypowy”). Porównujemy efekt ramowania w obrębie skali. Wyjątek: H4, gdzie pytanie dotyczy właśnie skali przy tym samym ramowaniu.
- „Wielokulturowy” i *multicultural* mają różne konotacje (angielski termin wiąże się z debatą o polityce wielokulturowości). To ograniczenie porównania językowego, opisane w tekście. Druga strona: w polskim dyskursie publicznym „wielokulturowość” często oznacza wielokulturową przeszłość; to wymaga źródła (luka w literaturze, 22.10).
- Brak przymiotnika kontrolnego: nie wiemy, czy podobny efekt dałby każdy przymiotnik wartościujący. Wniosek dotyczy słowa „wielokulturowy” w tych promptach; porównanie z przymiotnikiem kontrolnym i ramowaniem D (dziennik, wpis 5) to kierunek dalszych badań. Częściowym zabezpieczeniem jest H3 (przesunięcie ku dziedzictwu i widowisku, a nie tylko ku „ładniejszemu” zdjęciu).

## 3. Generatory

| Generator | Wersja i dostęp | Ustawienia | Uwagi |
|---|---|---|---|
| OpenAI GPT Image 2.5 Flare | `gpt-image-2.5-flare-2026-09-08`, Images API, `/v1/images/generations` | 1024 × 1024, jakość medium, n = 1, moderacja domyślna (auto) | Pole revised_prompt nie jest zwracane dla modeli GPT Image; może być wymagana weryfikacja organizacji |
| Google Gemini Nano Banana 2.1 | `gemini-nano-banana-2.1`, Gemini API | 1K, proporcje 1:1 | Tryb „myślenia” włączony na stałe; znak wodny SynthID; parametru seed dokumentacja nie wymienia |

Plan B dla drugiego generatora: FLUX.2 [dev] przez hostowany endpoint z parametrem seed.

Test API wykonany 22.10.2026 (16 obrazów, 10 zakodowanych modelem); pilotaże 1 i 2 też 22.10. Program zapisuje zwracaną nazwę modelu przy każdym żądaniu. Lista kontrolna testu (zachowana dla przejrzystości):
1. Dostęp do GPT Image w koncie OpenAI (weryfikacja organizacji). Zgłoś ją od razu, bo może potrwać 1–3 dni.
2. Gemini API: dostęp z Polski, włączone rozliczenia, generowanie scen z ludźmi.
3. Dokładne nazwy parametrów rozmiaru, jakości i proporcji w obu API.
4. Co wraca w odpowiedzi: nazwa modelu, identyfikator żądania, zużycie tokenów, tekst obok obrazu (Gemini). Wszystko zapisujemy.
5. Jak wygląda odmowa: kod błędu, komunikat, powód zakończenia.
6. Rzeczywisty koszt 16 obrazów testowych wobec szacunku.

## 4. Liczebności

| Etap | Wyliczenie | Obrazy |
|---|---|---|
| Test API | 4 prompty × 2 języki × 2 generatory | 16 |
| Pilotaż 1 (prompty „fotografia/photograph”, wykonany 22.10) | 4 ramowania × 2 skale × 2 języki × 2 generatory × 1 | 32 (poza analizą, raport w materiałach uzupełniających) |
| Pilotaż 2 (prompty „obraz/image”, wykonany 22.10; prompty ostateczne) | 4 ramowania × 2 skale × 2 języki × 2 generatory × 1 | 32 (poza analizą, raport w materiałach uzupełniających) |
| Badanie właściwe | 4 × 2 × 2 × 2 × 20 | 640 |
| Zbiór walidacyjny | 5 losowych obrazów z każdego z 32 warunków | 160 (z 640) |
| Kodowanie powtórne (test–retest) | losowe z 160, po ≥ 7 dniach | 50 |
| Drugi koder (doktorant, nauki o kulturze i religii) | losowe z 160; `temporal_frame`, `mode_of_culture.dominant`, `religion.form` | 50 |

Moc: porównanie W z B w 1 generatorze, po złączeniu języków i skal, to 80 obrazów na grupę. To wystarcza do wykrycia różnicy ok. 20 punktów procentowych przy mocy ok. 80%. W 1 skali i 1 generatorze (40 na grupę) wykrywalna różnica to ok. 30 punktów. Liczebność nie czyni wyników reprezentatywnymi dla „AI”: opisuje rozkład dla tych promptów, tych wersji i tego okresu.

## 5. Procedura generowania

- Każdy obraz to osobne żądanie z n = 1, bez kontekstu rozmowy.
- Pełna lista 640 żądań jest losowo przemieszana; ziarno losowania zapisane. Oba generatory pracują naprzemiennie, całość w ciągu 1 dnia.
- Wersje modeli przypięte. Jeśli wersja zniknie w trakcie, zbieranie zaczyna się od nowa; wersji nie mieszamy.
- Błędy techniczne (przekroczenie czasu, 5xx, 429): do 3 ponowień z rosnącą przerwą, każda próba w logu.
- Odmowy i blokady treści: zapis jako wynik, z komunikatem. Bez przeredagowania promptu i bez zastępowania obrazu. Raportujemy odsetek odmów w każdym warunku.
- Uszkodzony plik: 1 ponowienie.
- Zakaz selekcji: obraz niepodobny do Krakowa jest danymi i dostaje kod niezgodności z miejscem.

### Metadane każdej próby

| Pole | Przykład |
|---|---|
| image_id | `img_7f3a9c` (losowy, bez związku z warunkiem) |
| run_order | 0412 |
| condition_code | `W-Z-EN-GG` (trzymany w osobnym pliku klucza) |
| prompt_exact | pełny tekst w UTF-8 |
| prompt_language | pl / en |
| generator, model_requested, model_returned | `gpt-image-2.5-flare-2026-09-08` |
| endpoint, params | rozmiar, jakość, n, format, moderacja, proporcje |
| request_id, response_id | z API |
| ts_start, ts_end (UTC) | `2026-10-29T10:41:03Z` |
| status, attempts, error_code, error_message | `refused`, 1, treść komunikatu |
| text_parts | tekst zwrócony obok obrazu (jeśli jest) |
| usage, cost_usd | tokeny i koszt |
| sha256 | skrót pliku |
| script_version, shuffle_seed | wersja programu, ziarno |

## 6. Kodowanie i walidacja

Kodeks: 02_kodeks.md (1.0). Instrukcja dla modelu: 03_instrukcja_kodera.md (1.0). Instrukcja drugiego kodera: 03c_instrukcja_drugiego_kodera.md (1.0). Schemat wyniku: 03b_schemat_kodowania.json (1.0).

Model kodujący: `gpt-6.1-sol` przez Batch API, 1 obraz na żądanie, ustrukturyzowany wynik według schematu. Model nie zna promptu, warunku, generatora ani hipotez. Alternatywa: `gpt-6-astra`, jeśli w pilotażu `gpt-6.1-sol` wyraźnie zawiedzie. Dostawca nie udostępnia wersji datowanej tego modelu: program zapisuje nazwę modelu zwróconą w każdej odpowiedzi, a brak przypiętej wersji opisujemy w tekście jako ograniczenie odtwarzalności. Model działa ze stałą temperaturą 1,0 (bez możliwości jej obniżenia, test API 22.10), więc jego kody są losowe w pewnym zakresie; dlatego kodowanie zbioru walidacyjnego 2 razy i próg stabilności ≥ .90 są obowiązkowe.

Kolejność:
1. Pilotaż (32 obrazy). Kodujesz je ręcznie i doprecyzowujesz definicje. Program puszcza na nich model, porównujesz odpowiedzi. Kodeks i instrukcję zamrażamy (wersja 1.0 i skrót SHA-256).
2. Zbiór walidacyjny (160). Program losuje 5 obrazów z każdego z 32 warunków i pokazuje je bez warunku i bez kodów modelu. Kodujesz w arkuszu, ok. 2 minuty na obraz, sam i bez pomocy narzędzi AI; każdy obraz od zera (kodeks, zasada 8). To samo dotyczy drugiego kodera i kodowania powtórnego.
3. Kodowanie przez model: wszystkie 640 obrazów; zbiór walidacyjny dwukrotnie, by zmierzyć stabilność.
4. Decyzja dla każdej zmiennej (tabela niżej).
5. Przegląd 480 pozostałych obrazów: poprawki w osobnych kolumnach, kody modelu zostają nietknięte.
6. Kodowanie powtórne 50 obrazów walidacyjnych po co najmniej 7 dniach, bez wglądu we wcześniejsze kody.

| Wynik zmiennej na 160 obrazach | Co robisz z pozostałymi 480 |
|---|---|
| α model–Ty ≥ .80, stabilność modelu ≥ .90, brak błędu różnicowego | Przeglądasz tę zmienną tylko w obrazach z flagą, która jej dotyczy (tabela niżej) |
| α .67–.80 | Przeglądasz tę zmienną we wszystkich 480 obrazach |
| α < .67 albo model myli się częściej w warunkach W i WT niż w B i T | Kodujesz tę zmienną ręcznie we wszystkich 480 obrazach |

Gdy 1 kategoria zmiennej obejmuje ponad 90% obrazów w zbiorze walidacyjnym, α bywa niska mimo wysokiej zgodności (pilotaż 1: 94% zgodności, α .48). Wtedy obok α podajemy zgodność procentową i AC1 Gweta, a zmienna przechodzi próg .80, jeśli zgodność ≥ 95% i AC1 ≥ .80 (decyzja 22.10). Próg .67 stosujemy analogicznie (zgodność ≥ 90% i AC1 ≥ .67). Pismo hebrajskie oceniamy jako połączoną kategorię `hebrew` + `hebrew_like`.

Flaga wskazuje zmienne do przeglądu, nie cały obraz (decyzja 22.10, po teście API: 9 z 10 obrazów miało flagę):

| Flaga | Zmienne do przeglądu |
|---|---|
| `religion_present`, `script_marker`, `dress_item_flag` | religia, pismo, `dress_items` |
| `staged_time`, `time_cues_conflict` | rama czasowa |
| `performer_or_religious_role` | role postaci, tryb kultury |
| `landmark_uncertain`, `place_not_consistent` | miejsce |
| `low_confidence_primary` | zmienna wskazana w `ambiguity_note`; gdy nie wskazano, rama czasowa, tryb kultury i role |

Flagi i ich odsetek w każdym warunku raportujemy. Flagi religii i ubioru częściej pojawią się w warunkach W i WT, więc poprawki trafią tam częściej; błąd różnicowy sprawdzamy na 160 obrazach przed bramką 3.

Kryteria po pilotażu 2 (32 obrazy to tylko sygnał, nie pomiar; klucz warunków otwierasz po zakodowaniu pilotażu). Pilotaż 2 nie zmienia już promptów: wynik niekorzystny dla hipotez nie jest powodem zmiany. Stan 22.10: pilotaż 2 wykonany, kryteria spełnione (odmowy 0 z 32, rama „nieokreślona” 3 z 32), bez pilotażu 3; zostają poprawki kodeksu (zwłaszcza definicja `photo_aged`, zgodność medium 59%).

| Kontynuuj, jeśli | Zmień projekt, jeśli | Zatrzymaj i wróć do planu, jeśli |
|---|---|---|
| Odmowy < 10% | Medium wykracza poza listę kodów (np. częste kolaże, mapy, plakaty z tekstem): dopisać regułę w kodeksie | Wszystkie warunki dają niemal te same obrazy |
| Każde medium kodowalne według kodeksu (rozkład tylko raportujemy, bez progu) | „Kazimierz” mylony z Kazimierzem Dolnym lub królem: reguła w kodeksie i opis jako wynik (promptu już nie zmieniamy) | Rama czasowa „nieokreślona” w ponad połowie obrazów mimo poprawek kodeksu |
| Rama „nieokreślona” < 30% | Jeden generator często odmawia: plan B | Odmowy przy „wielokulturowy” > 30% w obu generatorach |
| Widać różnice między warunkami w co najmniej 1 zmiennej głównej | Model i Ty często różnicie się w zmiennej głównej: poprawić definicję i instrukcję | |
| | Ponad połowa obrazów `illustration` w obu generatorach: sprawdzić, czy kodeks rozstrzyga ramę czasową dla obrazów malarskich (styl sam w sobie nie jest wskaźnikiem historycznym) | |

Błąd różnicowy sprawdzamy, porównując odsetek pomyłek modelu w warunkach z „wielokulturowy” i bez (test Fishera) oraz w obrazach z obu generatorów. Model od OpenAI koduje obrazy od OpenAI, więc ryzyko wspólnych skojarzeń sprawdzamy osobno.

Zgodność z modelem to kontrola spójności, nie walidacja przez niezależnego kodera. Test–retest mierzy stałość Twojego kodowania. Prawdziwą zgodność między koderami daje druga osoba: doktorant z nauk o kulturze i religii koduje 50 losowych obrazów z 160 w 3 zmiennych (`temporal_frame`, `mode_of_culture.dominant`, `religion.form`), ok. 2 godziny, 3–4.11. Dostaje osobną instrukcję (tylko te 3 zmienne) i ćwiczy na obrazach pilotażowych, nigdy na zbiorze walidacyjnym. Nie zna warunków, promptów, generatorów, hipotez ani Twoich kodów i kodów modelu.

Źródło kodów w analizie: dla 160 obrazów walidacyjnych Twoje kody; dla 480 pozostałych kody modelu z poprawkami według tabeli decyzji (poprawki w osobnych kolumnach, kody modelu zostają nietknięte). Kody drugiego kodera służą tylko do oceny zgodności.

## 7. Analiza

- Odsetki w każdym z 32 warunków z 95% przedziałami Wilsona.
- Testy konfirmacyjne (dziennik, wpis 8, zatwierdzony 21.10):
  - H1–H3: osobno dla każdego generatora, po złączeniu języków i skal (80 vs 80), test dokładny Fishera, jednostronny.
  - H4: osobno dla każdego generatora, po złączeniu języków (40 vs 40).
  - Korekta Holma dla 8 testów (4 hipotezy × 2 generatory). Hipoteza potwierdzona dla generatora, jeśli p po korekcie < .05 i kierunek jest zgodny.
  - Wyniki dla każdej skali osobno podajemy opisowo, z przedziałami ufności.
- Mianownik: wszystkie obrazy zakodowane, także `illustration` (zakaz selekcji). Odmowy raportujemy osobno w każdym warunku.
- Jeśli odsetek odmów w 2 porównywanych grupach różni się o więcej niż 10 punktów, podajemy też wariant zachowawczy: odmowa liczy się jako obraz bez wskaźnika hipotezy.
- Analizy wrażliwości: dla H1, H2, H4 bez obrazów z ramą „nieokreśloną”; dla H1–H4 bez obrazów `illustration`.
- H1 i H3 nie są niezależne: kostium daje jednocześnie `staged_historical` i `spectacle`. Piszemy o tym przy wynikach.
- Różnice między językami i generatorami jako tabela odporności, bez osobnych hipotez.
- P5 opisowo. Test tylko wtedy, gdy w obu porównywanych grupach jest co najmniej 30 obrazów z religią.
- Eksploracyjnie (decyzja 22.10, po pilotażu 1): rozkład medium w każdym warunku i porównanie W z B (czy „wielokulturowy” przesuwa obraz ku `illustration` lub `photo_aged`), osobno dla PL i EN. Różnicę PL/EN w medium (zwłaszcza `illustration`) opisujemy jako skutek tłumaczenia „obraz/image”, bez testu konfirmacyjnego. Przy wielu obrazach `illustration` analiza wrażliwości bez nich (sekcja 7) staje się główną kontrolą wniosków H1–H4.
- Eksploracyjnie (decyzja 22.10): tekst zwracany przez Gemini obok obrazu (`text_parts` w logu). W każdym warunku odsetek odpowiedzi z tekstem i opisowo, czy tekst nazywa religię, grupę albo okres. Model kodujący tego tekstu nie widzi. Ok. 1 godzina w tygodniu 3.

## 8. Eksponaty i warstwa interpretacyjna

- Ściany obrazów: 8 warunków (4 kazimierskie, 4 krakowskie), po 8 obrazów na warunek i generator. Reguła doboru ustalona przed obejrzeniem: pierwsze 8 według losowego identyfikatora.
- Wykres: odsetek ramy historycznej lub inscenizowanej w 8 warunkach, osobno dla generatorów, z przedziałami ufności.
- Tabela: kody religii i pisma w warunkach kazimierskich.
- Czytanie serii (Salvaggio 2023) dla każdej komórki kazimierskiej: co się powtarza, czego brakuje, jakie konfiguracje znaków tworzą obraz miejsca.
- Rama główna: autoryzowany dyskurs dziedzictwa (Smith 2006). Teza do sprawdzenia: generator automatyzuje ten dyskurs, „wielokulturowość” zamienia w zabytek i przeszłość, a ludzi w zwiedzających lub wykonawców.
- Rama pomocnicza: religia przeżywana (McGuire 2008), uzupełniona o religię materialną (Meyer i in. 2010).
- Kontekst przypadku: Lehrer (2013), Gruber (2002), Waligórska (2013), raport CASPAR UEK (Pędziwiatr i in. 2026), „Otwarty Kraków”.
- O „pominięciu” mówimy tylko z punktem odniesienia: polecenie z promptu („dzisiaj”), inny warunek albo udokumentowana teraźniejszość. O „stereotypie” tylko przy koncentracji wąskiego zestawu znaków i zgodności z tropem opisanym w literaturze. Sama częstość to ujednolicenie, nie stereotyp.

## 9. Harmonogram

Liczba godzin w tygodniach 1–4: ok. 92. Tydzień 0 to ok. 10–12 godzin.

### Tydzień 0 (21–25.10): przygotowanie

| Dzień | Zadanie |
|---|---|
| Śr 21.10 | Literatura: baza RIS, zapytania do Scite. Założenie projektu w Claude. Zgłoszenie weryfikacji organizacji w OpenAI, włączenie rozliczeń w Gemini API |
| Cz 22.10 | Scite, import do Zotero, scalenie RIS. Program: config, plan żądań, generowanie (wersja próbna) |
| Pt 23.10 | Program: przygotowanie zaślepienia, losowanie zbiorów, arkusz kodowania |
| Sb 24.10 | Wybór czasopisma i sprawdzenie wytycznych (limit, obrazy, AI). Program: kodowanie modelem |
| Nd 25.10 | Test programu bez kluczy (--dry-run na obrazach zastępczych). Lektura: Smith, McGuire |

Stan faktyczny 24.10: test API i pilotaże 1–2 wykonane 22.10, bramka 1 zaliczona, zamrożenie (bramka 2) przesunięte na 24.10. Generowanie 640 obrazów po utworzeniu tagu `v1.0-freeze`. Dalsze terminy (walidacja, bramki 3 i 4, wysyłka) bez zmian.

### Tydzień 1 (26.10–1.11)

| Dzień | Zadanie |
|---|---|
| Pn 26.10 | Klucze w .env, test 16 obrazów, kodowanie 10 obrazów modelem |
| Wt 27.10 | **Bramka 1: test API.** Generowanie pilotażu (32). Kodujesz pilotaż ręcznie |
| Śr 28.10 | Kodowanie pilotażu modelem, porównanie, poprawki kodeksu i instrukcji |
| Cz 29.10 | (Bramka 2 przeniesiona na 24.10: zamrożenie kodeksu, instrukcji, schematu i planu analizy, tag `v1.0-freeze`.) Generowanie 640 obrazów po tagu, jeśli nie odbyło się wcześniej |
| Pt 30.10 | Kontrola korpusu, zaślepienie, losowanie 160. Start kodowania walidacyjnego |
| Sb–Nd 31.10–1.11 | Kodowanie walidacyjne. Pisanie: teoria |

### Tydzień 2 (2.11–8.11)

| Dzień | Zadanie |
|---|---|
| Pn 2.11 | Koniec kodowania walidacyjnego. Wysłanie zadania Batch (640 + 160) |
| Wt 3.11 | Wyniki modelu, raport walidacji. Drugi koder koduje 50 obrazów (3–4.11) |
| Śr 4.11 | **Bramka 3: decyzja dla każdej zmiennej** |
| Cz–Nd 5–8.11 | Przegląd 480 obrazów. Pisanie: teoria, stan badań |

### Tydzień 3 (9.11–15.11)

| Dzień | Zadanie |
|---|---|
| Pn 9.11 | Kodowanie powtórne 50 obrazów (7 dni po 2.11) |
| Wt–Śr 10–11.11 | Analiza, eksponaty (11.11 to święto; zaplanuj krótszy dzień) |
| Cz–Nd 12–15.11 | Czytanie serii kazimierskich. Pisanie: metoda, wyniki |

### Tydzień 4 (16.11–24.11)

| Dzień | Zadanie |
|---|---|
| Pn–Wt 16–17.11 | Wyniki |
| Śr 18.11 | **Bramka 4: szkic wyników.** Brak szkicu przesuwa wysyłkę o tydzień |
| Cz–Sb 19–21.11 | Dyskusja, wstęp, zakończenie |
| Nd 22.11 | Symulowana recenzja, poprawki |
| Pn 23.11 | Korekta, anonimizacja, deklaracja AI, materiały uzupełniające, list do redakcji |
| Wt 24.11 | Wysyłka |

## 10. Tekst: długość i struktura

Założenie robocze: „15 stron” to ok. 6 000 słów tekstu głównego (A4, Times 12, interlinia 1,5), bez bibliografii, z 3–4 ilustracjami i 2–3 tabelami. Jeśli chodzi o strony znormalizowane (1 800 znaków), tekst ma ok. 4 000 słów; wtedy obowiązuje wariant B. Ostateczny limit wyznaczają wytyczne czasopisma.

| Część | Wariant A (ok. 6 000) | Wariant B (ok. 4 000) | Treść |
|---|---|---|---|
| Wstęp | 600 | 400 | Problem, pytanie, wkład dla badań nad dziedzictwem i religią |
| Teoria i kontekst | 1 200 | 800 | AHD, religia przeżywana i materialna, Kazimierz jako krajobraz dziedzictwa, współczesny Kraków |
| Stan badań | 500 | 300 | Generatory a miejsca, kultury i religie; wpływ języka |
| Materiał i metoda | 1 000 | 700 | Prompty, generatory, kodowanie, walidacja, udział AI, granice wniosków |
| Wyniki | 1 500 | 1 000 | Rama czasowa, tryby kultury, religia; serie kazimierskie |
| Dyskusja | 900 | 600 | Wielokulturowość w czasie przeszłym, dziedzictwo zautomatyzowane, religia jako zabytek |
| Zakończenie i ograniczenia | 300 | 200 | 1 koder, 1 punkt w czasie, 2 systemy; zmiana promptów po pilotażu 1 (ujawniona); tłumaczenie „obraz/image” (malarskie znaczenie polskiego słowa); brak przymiotnika kontrolnego; różne konotacje „wielokulturowy/multicultural”; model kodujący bez wersji datowanej |

Szczegóły procedury, pełny kodeks i instrukcja kodera idą do materiałów uzupełniających.

## 11. Zamrożenie planu analizy (zamiast preregistracji w rejestrze)

Decyzja z 21.10: bez rejestracji w OSF ani AsPredicted. 24.10 (decyzja z 24.10; pierwotnie 29.10), przed generowaniem 640 obrazów, w publicznym repozytorium `kkai` powstaje tag `v1.0-freeze` z: kodeksem 1.0, instrukcją kodera 1.0, schematem 1.0, ich skrótami SHA-256 i 1-stronicowym planem analizy po angielsku (`analysis_plan_v1.0.md`). Plan analizy zawiera: stan danych (zebrano tylko test API i pilotaż), H1–H4 z kierunkiem, P5 i P6 jako eksploracyjne, zmienne zależne (odwołanie do kodeksu 1.0), warunki i prompty, liczebności, źródło kodów, testy i korektę, reguły wykluczeń i odmów, analizy wrażliwości, regułę doboru ilustracji. W artykule piszemy „deposited in a public repository before data collection”, nie „preregistered”. W wersji do recenzji: anonimowa kopia repozytorium.

## 12. Etyka, prawa, udział AI

- Obrazy nie przedstawiają realnych osób; nie zbieramy danych osobowych.
- Prawo do publikacji obrazów: sprawdzić warunki obu dostawców i politykę czasopisma.
- W metodzie tabela udziału AI: generowanie (2 systemy), opis widocznych elementów i kody zmiennych zwalidowanych (model kodujący, wersja, daty), kody religii i pisma (model + przegląd 100% oflagowanych), interpretacja (autor), redakcja tekstu (zgodnie z polityką czasopisma).
- Materiały otwarte: prompty, kodeks, instrukcja kodera, schemat, kody, skrypty. Obrazy według warunków dostawców.

## 13. Ryzyka i plan B

| Ryzyko | Sygnał | Plan B | Koszt w czasie |
|---|---|---|---|
| Weryfikacja organizacji w OpenAI trwa | Brak dostępu 26.10 | Start od Gemini; OpenAI dołącza przed generowaniem właściwym | 1–3 dni |
| Gemini odmawia scen z ludźmi albo nie działa w regionie | Test 26.10 | FLUX.2 przez hostowany endpoint z seed | 1 dzień |
| Odmowy > 30% przy „wielokulturowy” | Pilotaż | Odmowa staje się wynikiem; warunek zostaje | 0 |
| Model źle koduje zmienne główne | Bramka 3 | Ręczne kodowanie 2 zmiennych w 480 obrazach | 8–10 h |
| Pisanie po angielsku trwa dłużej | Brak szkicu wyników 18.11 | Krótszy stan badań; korekta po wysłaniu wersji roboczej znajomemu | 3–5 dni |
| Inne obowiązki zjadają godziny | < 15 h w tygodniu | Wysyłka tydzień później; walidacji nie tniemy | 1 tydzień |
| Recenzenci chcą więcej modeli albo pomiaru w czasie | Recenzje | Odpowiedź z ograniczeń + zapowiedź wersji pełnej (1 600 obrazów) | – |

## 14. Koszty

Ok. 25–50 USD. Generowanie OpenAI ok. 4,5 USD (ok. 344 obrazy z testem i pilotażem), Google ok. 11,6 USD (ok. 344 obrazy, 0,0336 USD za obraz według cennika z 21.10.2026), kodowanie `gpt-6.1-sol` ok. 830 wywołań, 9–31 USD. Ceny sprawdzić ponownie w dniu testu.
