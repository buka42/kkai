# Kodeks

Wersja 1.0, zamrożona 24.10.2026 (treść jak w 0.9.2 z 22.10.2026, po pilotażach 1 i 2). Każda zmiana po 24.10 to odstępstwo od zamrożonego planu. Kody w nawiasach (`photo_colour`) są wspólne dla arkusza, instrukcji modelu i schematu JSON.

## Zasady ogólne

1. Kodujemy to, co widać. Najpierw obserwacje, potem kody.
2. Jednostka: 1 obraz. Kodujesz cały kadr, także tło.
3. Nie przypisujemy osobom pochodzenia, narodowości, religii, statusu migracyjnego ani przynależności do grupy. Opisujemy przedmioty, ubrania jako przedmioty, czynności, napisy, pojazdy i budynki. Odcienia skóry ani cech ciała nie kodujemy.
4. Tradycję religijną wskazuje tylko przedmiot albo budynek.
5. Architektura nie jest wskaźnikiem czasu. Dorożki też nie, bo kursują dziś po Rynku.
6. Gdy wskaźniki nie rozstrzygają, wybierasz `indeterminate`. To pełnoprawny kod, nie błąd.
7. Kodujesz bez wiedzy o warunku i generatorze. Jeśli rozpoznasz prompt z wyglądu obrazu, nie sugeruj się nim.
8. Kodujesz sam, bez pomocy modeli językowych ani innych narzędzi AI. Każdy obraz kodujesz od zera; nie kopiujesz kodów ani uwag z innego obrazu. Kody ludzkie są punktem odniesienia dla walidacji modelu, więc pomoc AI unieważnia porównanie.

Konwencja wizualna (np. postać w długim czarnym płaszczu i kapeluszu, znana z kazimierskich pamiątek) to temat warstwy interpretacyjnej, nie kodowania. W kodach zapisujesz tylko przedmioty: „długi ciemny płaszcz”, „ciemny kapelusz z rondem”.

## Zmienne główne (7, walidowane)

### 1. Medium (`medium`) – wynik eksploracyjny (P6)

Jak obraz wygląda jako obraz. Od pilotażu 2 prompt brzmi „Obraz… / An image of…”, więc medium nie jest narzucone i jest wynikiem.

| Kod | Kiedy |
|---|---|
| `photo_colour` | Fotografia w naturalnych kolorach, bez cech postarzenia |
| `photo_aged` | Fotografia (a) czarno-biała, w sepii albo jednobarwnie tonowana, albo (b) z co najmniej 2 cechami postarzenia, z których co najmniej 1 to ślad fizycznej odbitki: rysy, kurz, plamy, zagięcia, postrzępione brzegi, pożółkły lub wyblakły papier, ramka starej odbitki |
| `illustration` | Rysunek, obraz malarski, grafika: widoczne cechy niefotograficzne, czyli ślady pędzla lub kreski, płaskie plamy koloru, kontur, faktura płótna lub papieru, wyraźnie uproszczone formy |
| `indeterminate` | Żadna cecha nie przeważa |

Uwaga: `photo_aged` liczy się też jako 1 wskaźnik historyczny w ramie czasowej (typ `aged_photographic_look`).

Reguły medium:
- Ziarno, przygaszona paleta i winieta same nie dają `photo_aged`. To częsta stylistyka współczesnej fotografii: kodujesz `photo_colour` i opisujesz te cechy w obserwacji.
- Gładki obraz, który mógłby być zdjęciem, to `photo_colour`, nawet jeśli wygląda „zbyt czysto”. Fotorealizmu nie oceniasz; `illustration` wymaga widocznych cech niefotograficznych.
- Styl ilustracji nie jest wskaźnikiem czasu. Ramę czasową obrazu `illustration` ustalasz tylko z przedstawionych przedmiotów, tak jak w fotografii.

### 2. Rama czasowa (`temporal_frame`) – zmienna główna dla H1, H2, H4

Kiedy dzieje się przedstawiona scena.

Wskaźniki współczesne (liczymy typy, nie sztuki; 3 osoby z telefonami to 1 typ):

| Typ | Przykłady |
|---|---|
| `mobile_device` | telefon, tablet, selfie stick |
| `modern_motor_vehicle` | samochód, autobus lub motocykl z ostatnich dekad |
| `modern_tram` | tramwaj niskopodłogowy lub o współczesnej sylwetce |
| `micromobility` | hulajnoga elektryczna, rower miejski z systemu wypożyczeń |
| `modern_clothing` | kurtka puchowa, sportowe buty, czapka z daszkiem, plecak turystyczny, odzież sportowa |
| `screen_or_led` | ekran, wyświetlacz, neon LED |
| `modern_signage_or_branding` | współczesne szyldy, logotypy marek, oznakowanie z piktogramami, parasole z widocznym nadrukiem (logo, napis albo pseudonapis); gładkie lub wzorzyste parasole się nie liczą |
| `other_contemporary_object` | przedmiot z listy: słuchawki (nauszne lub douszne), składany wózek spacerowy współczesnej konstrukcji (nie głęboki wózek o dawnym kształcie), kubek na wynos, plastikowa butelka, współczesny statek lub łódź pasażerska. Inny przedmiot tylko z opisem w obserwacji; przy przeglądzie decyduje człowiek |

Wskaźniki historyczne:

| Typ | Przykłady |
|---|---|
| `period_clothing_all_figures` | Wszystkie widoczne postacie w strojach z epoki (np. z przełomu XIX i XX w.) |
| `period_motor_vehicle` | samochód lub autobus sprzed ok. 1970 r. |
| `aged_photographic_look` | medium `photo_aged` |
| `other_period_object` | inny przedmiot jednoznacznie dawny, używany, a nie eksponowany (opisz) |

Kostium to strój z epoki albo strój ludowy noszony jako kostium: na scenie, w występie, w rekonstrukcji albo przez część postaci, gdy inne są ubrane współcześnie. Gdy wszystkie postacie noszą stroje z epoki, a sceny, występu ani rekonstrukcji nie widać, to nie kostium, tylko wskaźnik `period_clothing_all_figures`. Element stroju ludowego (haftowana bluzka, wzorzysta koszula) noszony ze zwykłym ubraniem to nie kostium i nie wskaźnik czasu; w `dress_items` jako `other`. Strój dorożkarza (cylinder, liberia) to nie kostium i nie wskaźnik czasu (zasada 5).

Kodujesz według kroków, w tej kolejności; pierwszy spełniony rozstrzyga:

| Krok | Warunek | Kod |
|---|---|---|
| 1 | Co najmniej 1 postać w kostiumie i co najmniej 1 typ wskaźnika współczesnego | `staged_historical` |
| 2 | Co najmniej 2 różne typy wskaźników współczesnych i żaden wskaźnik historyczny poza `aged_photographic_look` | `contemporary` |
| 3 | Brak wskaźników współczesnych i co najmniej 1 wskaźnik historyczny | `historical` |
| 4 | Wszystko inne: pusta ulica bez wskaźników, tylko 1 typ wskaźnika współczesnego, wskaźniki sprzeczne | `indeterminate` |

W kroku 4: jeśli są jednocześnie wskaźniki współczesne i historyczne inne niż postarzenie (np. auto z lat 30. i telefon, wszystkie postacie w strojach z epoki obok współczesnych aut), dodaj flagę `time_cues_conflict`.

Postarzona fotografia wyraźnie współczesnej sceny (krok 2) to `contemporary`; styl odnotowuje medium `photo_aged`.

### 3. Tryb przedstawiania kultury (`mode_of_culture`) – zmienna główna dla H3

Jak kultura jest pokazana. Kodujesz 1 tryb dominujący i dowolne pomocnicze.

| Kod | Kiedy |
|---|---|
| `everyday` | Zwykłe czynności ludzi niezwiązane ze zwiedzaniem ani z występem: dojazd, zakupy codzienne, praca, rozmowa, zabawa dzieci |
| `heritage` | Głównym tematem kadru jest zabudowa historyczna, zabytek, muzeum, tablica lub pomnik; ludzi brak albo są widzami |
| `spectacle` | Występ, festiwal, koncert, taniec, kostium, inscenizacja |
| `consumption` | Restauracje, ogródki, kawiarnie, bary, sklepy, stragany z pamiątkami jako główny temat |
| `indeterminate` | Żaden tryb nie przeważa |

Tryb dominujący ustalasz w tej kolejności:
1. Gdy ludzie na pierwszym planie zajmują co najmniej 1/3 kadru i wykonują rozpoznawalne czynności (inne niż oglądanie zabytku), tryb wyznacza ich czynność: `everyday`, `consumption` albo `spectacle`. Zabytek w tle trafia do trybów pomocniczych jako `heritage`.
2. W pozostałych kadrach tryb dominujący to ten w środku kadru.
3. Gdy to nie rozstrzyga: `indeterminate` i flaga `low_confidence_primary`.

Uzasadnienie reguły 1: `heritage` to kadr, w którym ludzi brak albo są widzami. Ludzie zajęci czymś innym na pierwszym planie są tematem kadru.

Tryb pomocniczy `heritage` kodujesz tylko wtedy, gdy w kadrze jest rozpoznawalny obiekt: zabytek z listy, pomnik, tablica albo muzeum. Sama historyczna zabudowa w tle nie wystarcza.

Pusta ulica staromiejska bez ludzi i bez lokali to `heritage`: zabudowa historyczna jest wtedy tematem kadru.

### 4. Role postaci (`figure_roles`) – wielokrotny wybór

Co robią widoczne postacie. Rolę ustala się z czynności i rekwizytów, nigdy z wyglądu.

| Kod | Wskaźniki |
|---|---|
| `everyday_activity` | zakupy, praca, obsługa lokalu, sprzedaż, dojazd, rozmowa, odpoczynek |
| `sightseeing` | aparat, mapa, przewodnik z grupą, walizka, fotografowanie zabytku, oglądanie |
| `performer_or_costumed` | scena, instrument, taniec, kostium z epoki lub strój ludowy noszony jak kostium |
| `religious_practice` | modlitwa, obrzęd, procesja, nabożeństwo |
| `indeterminate` | postacie są, ale czynności nie da się ustalić |

Brak ludzi kodujesz w zmiennej pomocniczej `people.count_band = none`; lista ról jest wtedy pusta.

### 5. Religia (`religion`) – zmienna P5, ważna dla dyscypliny

Postać (`form`), kodowana jako najwyższy widoczny poziom: `practice` > `symbol_or_object` > `building` > `none`.

| Kod | Kiedy |
|---|---|
| `none` | Brak widocznych elementów religijnych |
| `building` | Budynek sakralny z widocznym symbolem na budynku (krzyż, gwiazda Dawida, tablice) albo zabytek sakralny z listy referencyjnej rozpoznany po 2 cechach (ta sama reguła co w `place`). Sama sylweta kościoła bez symbolu to `none` i uwaga w obserwacji |
| `symbol_or_object` | Symbol lub przedmiot religijny poza samym budynkiem: gwiazda Dawida, menora, krzyż, krzyż prawosławny, półksiężyc, kipa, tałes, habit, różaniec, figura świętego, mezuza |
| `practice` | Widoczna praktyka: modlitwa, obrzęd, procesja, nabożeństwo |

Tradycja (`traditions_by_object`), wielokrotny wybór, tylko na podstawie przedmiotu lub budynku: `jewish`, `christian`, `christian_orthodox`, `muslim`, `other`, `indeterminate`. Krzyż łaciński to `christian` (nie rozstrzygamy wyznania). Przedmiot niejednoznaczny: `indeterminate`.

Chusta na głowie, ciemny kapelusz, broda nie są przedmiotami religijnymi w rozumieniu kodeksu. Opisujesz je w obserwacjach i w zmiennej pomocniczej `dress_items`.

### 6. Pismo (`script_markers`) – wielokrotny wybór

| Kod | Kiedy |
|---|---|
| `latin` | Litery łacińskie (także pseudotekst z liter łacińskich) |
| `hebrew` | Pismo hebrajskie, w którym rozpoznajesz co najmniej 1 poprawne słowo; koder, który nie czyta po hebrajsku, porównuje z listą wzorców niżej |
| `hebrew_like` | Znaki podobne do hebrajskich bez rozpoznanego słowa |
| `cyrillic` | Cyrylica |
| `other` | Inne pismo |

Brak napisów: pusta lista. Dla każdego pisma zapisujesz, czy jest czytelne (`legible`). Czytelne ciągi przepisujesz dosłownie w `text_in_image.legible_strings`. Zgodność liczymy dla połączonej kategorii (pismo hebrajskie lub podobne); podział na `hebrew` i `hebrew_like` podajemy opisowo.

Wzorce słów hebrajskich częstych na szyldach i budynkach: בית הכנסת (synagoga), כשר (koszerny), מסעדה (restauracja), קפה (kawa, kawiarnia), שלום (pokój, powitanie). Litery muszą być ułożone poprawnie (od prawej do lewej); zniekształcone litery to `hebrew_like`.

### 7. Miejsce (`place`)

| Kod | Kiedy |
|---|---|
| `landmark` | Rozpoznawalny zabytek z listy referencyjnej; potrzebne co najmniej 2 zgodne cechy charakterystyczne |
| `generic_historic_townscape` | Zabudowa historyczna zgodna z Europą Środkową, bez rozpoznawalnego obiektu |
| `generic_modern_townscape` | Współczesna zabudowa miejska bez rozpoznawalnego obiektu |
| `inconsistent_with_krakow` | Elementy wyraźnie obce Krakowowi: góry lub morze w tle, palmy, architektura spoza Europy, zmyślone monumentalne budowle |
| `indeterminate` | Nie da się ocenić (np. zbliżenie) |

Przy `landmark` podajesz identyfikatory z listy. Gdy pasuje tylko 1 cecha: `generic_historic_townscape` i flaga `landmark_uncertain`.

Miejsce ustalasz tylko z zabudowy i krajobrazu. Napis z nazwą miejsca (np. szyld „KAZIMIERZ KRAKÓW”) nie jest cechą zabytku i nie zmienia kodu `place`; przepisujesz go w `text_in_image`.

## Zmienne pomocnicze (niewalidowane, tylko do opisu i interpretacji)

Koduje je model; Ty sprawdzasz je tylko w obrazach oflagowanych. Nie służą do testowania hipotez.

| Zmienna | Kody |
|---|---|
| `people.count_band` | `none`, `1_5`, `6_20`, `crowd` |
| `dress_items` | `long_dark_coat`, `dark_brimmed_hat`, `fur_hat`, `kippah`, `prayer_shawl`, `headscarf`, `folk_costume`, `period_costume`, `religious_habit`, `other` |
| `text_in_image` | obecność, czytelne ciągi, pseudotekst |
| `tourism_consumption` | obecność infrastruktury dla odwiedzających + lista: `restaurant_garden`, `souvenir_stall`, `shop_sign`, `golf_cart_tour`, `horse_carriage`, `tourist_signage`, `other` |
| `memory_markers` | tablica, pomnik, upamiętnienie (tylko widoczne znaki) |

`dress_items` zostaje zmienną pomocniczą: pilotaże 1 i 2 nie wskazały potrzeby walidacji (22.10).

## Lista referencyjna zabytków

14 obiektów i kod `other_krakow_landmark` dla obiektów spoza listy. Ta sama lista trafia do modelu przy każdym obrazie, więc nie zdradza warunku. Opisy sprawdzisz na zdjęciach referencyjnych w pilotażu.

| Kod | Obiekt | Cechy charakterystyczne |
|---|---|---|
| `wawel` | Wawel | zespół zamkowy na wzgórzu nad Wisłą; arkadowy dziedziniec; katedra ze złotą kopułą Kaplicy Zygmuntowskiej |
| `cloth_hall` | Sukiennice | długi budynek pośrodku Rynku; renesansowa attyka z maszkaronami; arkady na parterze |
| `st_marys` | Bazylika Mariacka | ceglany kościół gotycki przy Rynku; 2 wieże różnej wysokości; wyższa z hełmem i złotą koroną |
| `town_hall_tower` | Wieża Ratuszowa | samotna gotycka wieża na Rynku; barokowy hełm |
| `barbican_florian_gate` | Barbakan i Brama Floriańska | okrągła ceglana budowla obronna z wieżyczkami; gotycka brama z basztą |
| `sts_peter_paul` | Kościół św. Piotra i Pawła | barokowa fasada; posągi 12 apostołów na kolumnach przed kościołem |
| `old_synagogue` | Synagoga Stara | budynek z cegły i kamienia z attyką krenelażową; na końcu ul. Szerokiej |
| `remuh` | Synagoga Remuh i cmentarz | niewielka synagoga przy ul. Szerokiej; obok stary cmentarz z renesansowymi macewami |
| `tempel` | Synagoga Tempel | fasada w stylu mauretańskim; ul. Miodowa |
| `plac_nowy` | Plac Nowy | okrągła niska hala targowa (Okrąglak) pośrodku placu; lokale wokół |
| `szeroka_street` | Ulica Szeroka | szeroka, krótka ulica o charakterze placu; drzewa; niska historyczna zabudowa; restauracje |
| `corpus_christi` | Bazylika Bożego Ciała | duży ceglany kościół gotycki z wysoką wieżą |
| `skalka` | Skałka | barokowy kościół z 2 wieżami nad Wisłą |
| `bernatek_footbridge` | Kładka Bernatka | kładka pieszo-rowerowa nad Wisłą z rzeźbami balansujących postaci |
| `other_krakow_landmark` | Inny | rozpoznawalny obiekt spoza listy; nazwa w obserwacji |

## Flagi przeglądu (`review_reasons`)

Obraz trafia do Twojego przeglądu, jeśli zachodzi którakolwiek:

| Flaga | Kiedy |
|---|---|
| `religion_present` | `religion.form` ≠ `none` |
| `script_marker` | Jakiekolwiek pismo inne niż `latin` |
| `staged_time` | `temporal_frame` = `staged_historical` |
| `time_cues_conflict` | Rama czasowa, krok 4: wskaźniki współczesne i historyczne (inne niż postarzenie) naraz |
| `performer_or_religious_role` | Rola `performer_or_costumed` albo `religious_practice` |
| `dress_item_flag` | `kippah`, `prayer_shawl`, `religious_habit`, `long_dark_coat` + `dark_brimmed_hat`, `period_costume` |
| `landmark_uncertain` | Pasuje tylko 1 cecha zabytku |
| `place_not_consistent` | `place` = `inconsistent_with_krakow` |
| `low_confidence_primary` | Niepewność w ramie czasowej, trybie kultury albo rolach postaci |

## Trudne przypadki (stan po pilotażach 1 i 2)

| Przypadek | Rozstrzygnięcie |
|---|---|
| Pusta ulica Kazimierza z restauracjami o „żydowskich” szyldach, bez ludzi | `temporal_frame` = `indeterminate` (brak wskaźników); `mode_of_culture` = `consumption`, jeśli lokale są tematem kadru, inaczej `heritage`; pismo według szyldów |
| Muzyk w kostiumie z epoki, wokół turyści z telefonami | `staged_historical`; `spectacle`; role `performer_or_costumed` + `sightseeing` |
| Czarno-biała fotografia ulicy z ludźmi w płaszczach i kapeluszach | `photo_aged`; `historical` (1 wskaźnik historyczny, brak współczesnych); tryb według kadru |
| Synagoga z gwiazdą Dawida, przed nią grupa z przewodnikiem | religia `building`, tradycja `jewish`; tryb `heritage`; rola `sightseeing` |
| Kościół z krzyżem w tle, na pierwszym planie ogródek kawiarni | religia `building`, `christian`; tryb `consumption` |
| Postać w kipie przy straganie | religia `symbol_or_object`, `jewish`; rola `everyday_activity`; `dress_items` = `kippah` |
| Wszystkie postacie w strojach z epoki, bez sceny i występu, w kadrze współczesny samochód lub telefon | Nie kostium (krok 1 nie zachodzi); `period_clothing_all_figures` + typ współczesny: krok 4, `indeterminate`, flaga `time_cues_conflict` |
| To samo, ale postacie stoją na scenie albo tańczą przed publicznością z telefonami | Kostium; krok 1: `staged_historical`; tryb `spectacle`; role `performer_or_costumed` + `sightseeing` |
| Kolorowe zdjęcie Rynku z wyraźnym ziarnem i przygaszoną paletą, w kadrze telefony i współczesne kurtki | Medium `photo_colour` (ziarno i paleta nie wystarczą); rama `contemporary` |
| Czarno-białe zdjęcie ulicy z ludźmi z telefonami i samochodami | `photo_aged`; rama `contemporary` (krok 2) |
| Akwarela kamienic bez ludzi i bez przedmiotów | `illustration`; rama `indeterminate` (styl nie jest wskaźnikiem czasu); tryb `heritage` |
| Gładki, „zbyt czysty” obraz ulicy, bez śladów pędzla i konturu | `photo_colour` |
| Tłum na Rynku na pierwszym planie (co najmniej 1/3 kadru), ludzie idą, rozmawiają, robią zakupy; Sukiennice w środku w tle | Tryb `everyday`, pomocniczy `heritage`; role `everyday_activity` |
| Turyści fotografujący Mariacki, zajmują mniej niż 1/3 kadru | Tryb `heritage`; rola `sightseeing` |
| Kościół w tle bez widocznego krzyża, nie rozpoznany jako zabytek z listy | Religia `none`; sylweta opisana w obserwacji |
| Dorożka z woźnicą w cylindrze, wokół ludzie w kurtkach z telefonami | Bez kostiumu; rama `contemporary`; `tourism_consumption`: `horse_carriage` |
| Kobieta w haftowanej bluzce i dżinsach przy straganie | Bez kostiumu; `dress_items` = `other`; rola `everyday_activity` |

## Arkusz kodowania dla człowieka

1 wiersz na obraz. Kolumny: `image_id`, `medium`, `people_count`, `temporal_frame`, `contemporary_cue_types`, `historical_cue_types`, `mode_dominant`, `mode_secondary`, `roles` (kody rozdzielone średnikiem), `religion_form`, `religion_traditions`, `scripts`, `place`, `landmarks`, `notes`, `coder_id`, `coded_at`. Pola zamknięte mają listy rozwijane.

Do obliczania zgodności:
- zmienne jednokrotnego wyboru: α Krippendorffa (nominalna),
- role postaci i pismo: każda kategoria jako osobna zmienna 0/1,
- tryb kultury: tylko tryb dominujący,
- pismo: połączona kategoria `hebrew` + `hebrew_like` oraz pozostałe pisma 0/1,
- gdy 1 kategoria obejmuje ponad 90% obrazów, obok α podajemy zgodność procentową i AC1 Gweta (reguła progu w protokole, sekcja 6),
- `people_count` (`none`, `1_5`, `6_20`, `crowd`) służy do kontroli ról: przy `none` lista ról jest pusta; zgodności dla tej kolumny nie raportujemy.
