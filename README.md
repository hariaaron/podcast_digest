## Daily Podcast Digest

Podcasts liefern häufig nur Shownotes. Der eigentliche Mehrwert steckt im Audio. Ziel dieses Projekts ist ein automatisierter Workflow, der neue Podcast-Episoden erkennt, den Audioinhalt per ASR transkribiert, daraus prägnante Episoden-Summaries erzeugt und das Ergebnis als Digest bereitstellt. 
 
## Ansatz
Baue mit einem Vibe-Coding Ansatz ein MVP, das 2–3 Podcast-RSS-Feeds überwacht, neue Episoden robust dedupliziert, Audio (MP3) verarbeitet, per AI transkribiert und pro Episode eine strukturierte Zusammenfassung erzeugt. 
Konkretes Ergebnis am Ende:

Ein lauffähiger Workflow, der:  
- 2–3 Podcast-RSS-Feeds einliest (MP3-Enclosures) 
- neue Episoden erkennt (Dedupe über stabilen Episode-Key) 
- Audio herunterlädt (mit Max-Size-Limit), ggf. in Chunks splittet (ffmpeg) 
- ASR (automatic speech recognition) ausführt und (optional) cached 
- pro Episode per LLM ein strukturiertes Summary erzeugt 
- Ergebnis als HTML (oder Markdown) in einem preview.html ablegt 
- optional Mail versendet (DRY_RUN steuert Versand) 
- State als JSON persistiert, sodass beim nächsten Run keine Doppelverarbeitung stattfindet 
- auch bei Teilausfällen Fortschritt persistiert 
- Betriebsmodi unterstützt: BOOTSTRAP, SMOKE_TEST, DRY_RUN, FORCE_LATEST_N 
