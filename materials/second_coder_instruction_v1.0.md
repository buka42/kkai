# Instrukcja dla drugiego kodera

Wersja 1.0, zamrożona 24.10.2026 razem z kodeksem 1.0 (treść jak w 0.9.2 z 22.10.2026). Treść jest wyciągiem z 02_kodeks.md (sekcje 2, 3 i 5); w razie rozbieżności rozstrzyga kodeks.

## Co robisz

Kodujesz 50 obrazów w 3 zmiennych: rama czasowa, dominujący tryb przedstawiania kultury, postać religii. Obrazy mają tylko losowy identyfikator. Nie znasz poleceń, z których powstały, ani tego, który program je wygenerował, i nie powinieneś próbować tego odgadnąć. Nie widzisz kodów innych osób. Wpisujesz kody w arkuszu (listy rozwijane), 1 wiersz na obraz. Czas: ok. 2 godzin.

Najpierw ćwiczysz na 8 obrazach pilotażowych (nie wchodzą do analizy) i porównujesz swoje kody z kodami autora. Pytania zadajesz przed kodowaniem właściwym. W trakcie kodowania właściwego nie konsultujesz się z autorem.

## Zasady ogólne

1. Kodujesz to, co widać, w całym kadrze, także w tle.
2. Nie przypisujesz osobom pochodzenia, narodowości, religii ani przynależności do grupy. Opisujesz przedmioty, ubrania jako przedmioty, czynności, napisy, pojazdy i budynki.
3. Tradycję religijną wskazuje tylko przedmiot albo budynek, nigdy wygląd osoby.
4. Architektura nie jest wskaźnikiem czasu. Dorożki też nie.
5. `indeterminate` to pełnoprawny kod, gdy wskaźniki nie rozstrzygają.
6. Kodujesz sam, bez pomocy modeli językowych ani innych narzędzi AI. Każdy obraz kodujesz od zera; nie kopiujesz kodów ani uwag z innego obrazu.
7. Styl obrazu (malarstwo, grafika) nie jest wskaźnikiem czasu. Strój dorożkarza (cylinder, liberia) też nie.

## 1. Rama czasowa (`temporal_frame`)

Kiedy dzieje się przedstawiona scena. Liczysz typy wskaźników, nie sztuki (3 osoby z telefonami to 1 typ).

Wskaźniki współczesne: telefon lub tablet; samochód, autobus albo motocykl z ostatnich dekad; nowoczesny tramwaj; hulajnoga elektryczna lub rower z wypożyczalni; współczesna odzież (kurtka puchowa, buty sportowe, czapka z daszkiem, plecak turystyczny); ekran lub LED; współczesne szyldy, logotypy, piktogramy, parasole z widocznym nadrukiem; słuchawki, składany wózek spacerowy, kubek na wynos, plastikowa butelka, współczesna łódź pasażerska.

Wskaźniki historyczne: wszystkie widoczne postacie w strojach z epoki; samochód lub autobus sprzed ok. 1970 r.; postarzona fotografia: czarno-biała, w sepii albo jednobarwnie tonowana, albo z co najmniej 2 cechami postarzenia, w tym co najmniej 1 śladem fizycznej odbitki (rysy, plamy, zagięcia, pożółkły papier); samo ziarno i przygaszone kolory nie wystarczą; inny przedmiot jednoznacznie dawny, używany, a nie eksponowany.

Kostium to strój z epoki albo ludowy noszony na scenie, w występie, w rekonstrukcji albo przez część postaci, gdy inne są ubrane współcześnie. Gdy wszystkie postacie noszą stroje z epoki, a sceny ani występu nie widać, to nie kostium, tylko wskaźnik historyczny. Pojedynczy element stroju ludowego (haftowana bluzka) przy zwykłym ubraniu to nie kostium.

Kroki w tej kolejności; pierwszy spełniony rozstrzyga:

| Krok | Warunek | Kod |
|---|---|---|
| 1 | Co najmniej 1 postać w kostiumie i co najmniej 1 typ wskaźnika współczesnego | `staged_historical` |
| 2 | Co najmniej 2 różne typy wskaźników współczesnych i żaden historyczny poza postarzeniem fotografii | `contemporary` |
| 3 | Brak wskaźników współczesnych i co najmniej 1 historyczny | `historical` |
| 4 | Wszystko inne: brak wskaźników, tylko 1 typ współczesny, wskaźniki sprzeczne | `indeterminate` |

## 2. Dominujący tryb przedstawiania kultury (`mode_dominant`)

| Kod | Kiedy |
|---|---|
| `everyday` | Zwykłe czynności niezwiązane ze zwiedzaniem ani z występem: dojazd, zakupy codzienne, praca, rozmowa, zabawa dzieci |
| `heritage` | Głównym tematem jest zabudowa historyczna, zabytek, muzeum, tablica lub pomnik; ludzi brak albo są widzami |
| `spectacle` | Występ, festiwal, koncert, taniec, kostium, inscenizacja |
| `consumption` | Restauracje, ogródki, kawiarnie, bary, sklepy, stragany jako główny temat |
| `indeterminate` | Żaden tryb nie przeważa |

Tryb dominujący ustalasz tak: (1) gdy ludzie na pierwszym planie zajmują co najmniej 1/3 kadru i robią coś innego niż oglądanie zabytku, tryb wyznacza ich czynność (`everyday`, `consumption`, `spectacle`); (2) w innych kadrach tryb w środku kadru; (3) gdy to nie rozstrzyga, `indeterminate`. Pusta ulica staromiejska bez ludzi i bez lokali to `heritage`.

## 3. Postać religii (`religion_form`)

Kodujesz najwyższy widoczny poziom: `practice` > `symbol_or_object` > `building` > `none`.

| Kod | Kiedy |
|---|---|
| `none` | Brak widocznych elementów religijnych |
| `building` | Budynek sakralny z widocznym symbolem (krzyż, gwiazda Dawida, tablice) albo rozpoznany zabytek sakralny z listy w kodeksie (2 cechy). Sama sylweta kościoła bez symbolu to `none` |
| `symbol_or_object` | Symbol lub przedmiot religijny poza samym budynkiem: gwiazda Dawida, menora, krzyż, półksiężyc, kipa, tałes, habit, różaniec, figura świętego, mezuza |
| `practice` | Widoczna modlitwa, obrzęd, procesja, nabożeństwo |

Chusta na głowie, ciemny kapelusz i broda nie są przedmiotami religijnymi.

## Trudne przypadki

| Przypadek | Rozstrzygnięcie |
|---|---|
| Muzyk w kostiumie z epoki, wokół ludzie z telefonami | `staged_historical`; `spectacle` |
| Czarno-biała fotografia ulicy z ludźmi w płaszczach i kapeluszach, bez wskaźników współczesnych | `historical` |
| Wszystkie postacie w strojach z epoki, bez sceny, w kadrze współczesny samochód | `indeterminate` |
| Pusta ulica z restauracjami, bez ludzi | rama `indeterminate`; tryb `consumption`, jeśli lokale są tematem kadru, inaczej `heritage` |
| Synagoga z gwiazdą Dawida, przed nią grupa z przewodnikiem | religia `building`; tryb `heritage` |
| Kościół z krzyżem w tle, na pierwszym planie ogródek kawiarni | religia `building`; tryb `consumption` |
| Postać w kipie przy straganie | religia `symbol_or_object` |
| Tłum na Rynku na pierwszym planie (co najmniej 1/3 kadru), Sukiennice w tle | tryb `everyday` |
| Turyści fotografujący Mariacki, mniej niż 1/3 kadru | tryb `heritage` |
| Kościół w tle bez widocznego krzyża, nie z listy | religia `none` |
| Akwarela kamienic bez ludzi i przedmiotów | rama `indeterminate`; tryb `heritage` |
| Dorożka z woźnicą w cylindrze, wokół ludzie z telefonami w kurtkach | rama `contemporary` |

Stan po pilotażach 1 i 2.
