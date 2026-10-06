# Faceless Video Engine (Automated High-Retention Video Generator)
**Tiedosto:** PROJECT_BRIEF.md  
**Päivitetty:** 6. lokakuuta 2026  
**Tekijä:** Apex Data Solutions / Mikko Palovuori

---

## 1. Projektin Tavoite & Ydinidea
Rakentaa täysin automatisoitu, studiolaatuinen pystyvideogeneraattori (**YouTube Shorts, TikTok, Instagram Reels**), joka:
1. Erottuu 99 % netin "AI-roskasta" (ei tylsää robottiääntä, ei merkityksetöntä Minecraft-silmukkaa).
2. Generoi aidosti koukuttavia, tositapahtumiin, liike-elämän oivalluksiin, mysteereihin tai huijauksiin perustuvia tarinoita.
3. Luonnollisen kuuloinen kertojaääni (Edge Neural Voice), aihekohtaiset kuvat/videot pehmeällä kamera-ajolla (Ken Burns), dynaamiset kineettiset tekstitykset (MrBeast/Hormozi 1-3 sanaa kerrallaan + emojit) ja hienovarainen äänisuunnittelu (SFX + ambient).
4. Voidaan kytkeä suoraan viralliseen **YouTube Data API v3** -automaatiolataukseen tai ajaa Antigravityn **Scheduled Taskilla** aamuisin.

---

## 2. Miksi tämä toimii (Erotutaan AI-roskasta)

| Ominaisuus | Tavallinen AI-roska (0 katselukertaa) | Tämä Faceless Engine (Viraalipotentiaali) |
| :--- | :--- | :--- |
| **Koukku (0-2s)** | "Did you know that in 1990..." | *"He left $100M in a vault... because of a half-eaten sandwich."* |
| **Visuaalit** | 60s samaa Minecraft- tai GTA-silmukkaa | Aihekohtaiset aidot arkistokuvat + pehmeä zoom/pan + tilannevideot |
| **Tekstitykset** | Koko lause pienenä alareunassa | Keskellä ruutua 1-3 sanaa, aktiivinen sana korostuu keltaisella + pomppaa + emojit |
| **Ääni & SFX** | Monotoninen robotti ilman tehosteita | Luonnollinen ihmismäinen ääni + whoosh leikkauksissa, bass drop, kassakone |
| **Niche** | Ylikilpaillut parisuhde-redditit | Ovelat huijaukset, liike-elämän salaisuudet, "glitches in history" |

---

## 3. Tekninen Arkkitehtuuri & Komponentit

```
[1. SCRIPT ENGINE] ──> Gemini tiukoilla koukkusäännöillä (in-media-res, no clichés)
         │
[2. VOICE ENGINE]  ──> edge-tts (Microsoft Neural Voice, esim. en-US-ChristopherNeural)
         │
[3. SUBTITLES]     ──> faster-whisper luo sanatasoiset aikaleimat (JSON)
         │
[4. VISUAL ENGINE] ──> Hakee kohtauskohtaiset valokuvat / B-roll klipit + Ken Burns zoom
         │
[5. RENDERER]      ──> FFmpeg yhdistää puheen, SFX:t, taustamusiikin, visuaalit & tekstitykset (1080x1920)
         │
[6. UPLOADER]      ──> google-api-python-client lataa videon YouTube Shortsiin ajastetusti
```

---

## 4. Kehitysaskeleet (Roadmap)

- [ ] **Vaihe 1: Ympäristö & Riippuvuudet**
  - Python-virtuaaliympäristö (`venv`).
  - Asennetaan: `edge-tts`, `faster-whisper`, `moviepy` / `ffmpeg-python`, `requests`, `google-api-python-client`.
  - Varmistetaan `ffmpeg` binäärit PATH:ssa.

- [ ] **Vaihe 2: Käsikirjoitusmoottori (`script_generator.py`)**
  - Generoi 30-50 sekunnin tarinoita 5-7 visuaaliseen kohtaukseen jaettuna.
  - Mukana kuvahakusanat (image prompts) ja SFX-tunnisteet (`[whoosh]`, `[cash]`, `[boom]`).

- [ ] **Vaihe 3: Ääni ja sanakohtaiset tekstitykset (`audio_subtitles.py`)**
  - Luodaan MP3 puheraita.
  - Ajetaan Whisper sanatasoisille aikaleimoille.
  - Luodaan ASS / Drawtext -tekstitystiedosto korostusväreillä (Highlight: `#FFE500`, Text: `#FFFFFF`, Outline: `#000000`).

- [ ] **Vaihe 4: Visuaalit ja leikkaus (`video_composer.py`)**
  - Generoidaan tai haetaan B-roll/valokuvat.
  - Muunnetaan pystymuotoon (9:16, 1080x1920).
  - Lisätään hidas zoom-in / zoom-out (Ken Burns).

- [ ] **Vaihe 5: FFmpeg Master Renderöijä (`render.py`)**
  - Yhdistää kaikki elementit yhdeksi valmiiksi `.mp4`-videoksi alle minuutissa.

- [ ] **Vaihe 6: YouTube Shorts Automaattilataus (`youtube_uploader.py`)**
  - Google Cloud OAuth2 kirjautuminen.
  - Lataa valmiin videon automaattisesti otsikolla, kuvauksella ja `#Shorts` -tageilla.

---

## 5. Ohjeet uuden keskustelun käynnistämiseen
Kun aloitat uuden keskustelun Antigravityssä tälle projektille:
1. Valitse vasemmasta sivupalkista projekti **faceless-video-generator** (tai avaa kansio `C:\Users\mikko\Desktop\faceless-video-generator`).
2. Klikkaa **`+ New Conversation`**.
3. Lähetä viesti: *"Jatketaan PROJECT_BRIEF.md:n mukaan ja toteutetaan Vaihe 1 ja 2."*
Agentti lukee tämän tiedoston ja tietää välittömästi kaiken, mitä olemme suunnitelleet.
