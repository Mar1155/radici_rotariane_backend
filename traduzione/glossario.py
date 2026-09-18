"""Le regole che un traduttore automatico non puo' indovinare.

Sono in prosa, non una tabella di sostituzioni: "Rotary Club di Cosenza resta
invariato" e' una regola che vale anche per i club che non conosciamo, mentre
una tabella copre solo quelli elencati. E' la ragione principale per cui questa
traduzione passa da un modello linguistico invece che da un servizio di
traduzione classico.

Il repository mostra il costo di non averle: il nome del progetto compare
tradotto in due modi diversi ("Stories and Roots" e "Rotarian Roots"), e un tab
si chiama "Casa Calabria International" in entrambe le lingue perche' qualcuno
lo ha corretto a mano.
"""

REGOLE = """\
Stai traducendo i contenuti di "Radici Rotariane nel Mondo", la piattaforma del
Distretto Rotary 2102. Rispetta queste regole, che valgono piu' della
traduzione letterale.

NOMI CHE NON SI TRADUCONO
- I nomi dei Club restano identici, compreso "di": "Rotary Club di Cosenza"
  resta "Rotary Club di Cosenza", non diventa "Rotary Club of Cosenza".
- I nomi propri di luogo restano in italiano: Cosenza, Lecce, Pollino.
- "Rota-Space" e "Radici Rotariane" sono nomi propri.

NOMI UFFICIALI ROTARY
Usa la terminologia ufficiale Rotary International della lingua di arrivo, non
la traduzione letterale. In inglese:
- "Azione internazionale"  -> "International Service"
- "Comitati Inter-Paese"   -> "Inter-Country Committees"
- "Distretto 2102"         -> "District 2102"
- "soci" (di un club)      -> "members"
- "service"                -> resta "service", e' gia' il termine Rotary
- "Radici Rotariane nel Mondo" -> "Rotarian Roots Worldwide", sempre cosi'.

REGISTRO
- Rivolgiti al lettore con "tu", come fa l'originale italiano.
- Non aggiungere ne' togliere frasi: traduci quello che c'e'.
- Conserva la punteggiatura e le maiuscole dei nomi propri.
"""
