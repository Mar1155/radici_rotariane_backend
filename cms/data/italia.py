"""Regioni e province italiane.

Dato di riferimento, non configurazione: si semina una volta e cambia solo se
cambia l'ordinamento amministrativo del Paese. I nomi inglesi ci sono solo dove
differiscono davvero (Puglia -> Apulia); altrove il nome italiano vale per
tutte le lingue.
"""

# nome regione, chiave, nome inglese (se diverso), [(provincia, sigla), ...]
REGIONI = [
    ('Abruzzo', 'abruzzo', None, [
        ("L'Aquila", 'AQ'), ('Chieti', 'CH'), ('Pescara', 'PE'), ('Teramo', 'TE')]),
    ('Basilicata', 'basilicata', None, [
        ('Matera', 'MT'), ('Potenza', 'PZ')]),
    ('Calabria', 'calabria', None, [
        ('Catanzaro', 'CZ'), ('Cosenza', 'CS'), ('Crotone', 'KR'),
        ('Reggio Calabria', 'RC'), ('Vibo Valentia', 'VV')]),
    ('Campania', 'campania', None, [
        ('Avellino', 'AV'), ('Benevento', 'BN'), ('Caserta', 'CE'),
        ('Napoli', 'NA'), ('Salerno', 'SA')]),
    ('Emilia-Romagna', 'emilia-romagna', None, [
        ('Bologna', 'BO'), ('Ferrara', 'FE'), ('Forlì-Cesena', 'FC'),
        ('Modena', 'MO'), ('Parma', 'PR'), ('Piacenza', 'PC'),
        ('Ravenna', 'RA'), ('Reggio Emilia', 'RE'), ('Rimini', 'RN')]),
    ('Friuli-Venezia Giulia', 'friuli-venezia-giulia', None, [
        ('Gorizia', 'GO'), ('Pordenone', 'PN'), ('Trieste', 'TS'), ('Udine', 'UD')]),
    ('Lazio', 'lazio', None, [
        ('Frosinone', 'FR'), ('Latina', 'LT'), ('Rieti', 'RI'),
        ('Roma', 'RM'), ('Viterbo', 'VT')]),
    ('Liguria', 'liguria', None, [
        ('Genova', 'GE'), ('Imperia', 'IM'), ('La Spezia', 'SP'), ('Savona', 'SV')]),
    ('Lombardia', 'lombardia', 'Lombardy', [
        ('Bergamo', 'BG'), ('Brescia', 'BS'), ('Como', 'CO'), ('Cremona', 'CR'),
        ('Lecco', 'LC'), ('Lodi', 'LO'), ('Mantova', 'MN'), ('Milano', 'MI'),
        ('Monza e della Brianza', 'MB'), ('Pavia', 'PV'), ('Sondrio', 'SO'),
        ('Varese', 'VA')]),
    ('Marche', 'marche', None, [
        ('Ancona', 'AN'), ('Ascoli Piceno', 'AP'), ('Fermo', 'FM'),
        ('Macerata', 'MC'), ('Pesaro e Urbino', 'PU')]),
    ('Molise', 'molise', None, [
        ('Campobasso', 'CB'), ('Isernia', 'IS')]),
    ('Piemonte', 'piemonte', 'Piedmont', [
        ('Alessandria', 'AL'), ('Asti', 'AT'), ('Biella', 'BI'), ('Cuneo', 'CN'),
        ('Novara', 'NO'), ('Torino', 'TO'), ('Verbano-Cusio-Ossola', 'VB'),
        ('Vercelli', 'VC')]),
    ('Puglia', 'puglia', 'Apulia', [
        ('Bari', 'BA'), ('Barletta-Andria-Trani', 'BT'), ('Brindisi', 'BR'),
        ('Foggia', 'FG'), ('Lecce', 'LE'), ('Taranto', 'TA')]),
    ('Sardegna', 'sardegna', 'Sardinia', [
        ('Cagliari', 'CA'), ('Nuoro', 'NU'), ('Oristano', 'OR'),
        ('Sassari', 'SS'), ('Sud Sardegna', 'SU')]),
    ('Sicilia', 'sicilia', 'Sicily', [
        ('Agrigento', 'AG'), ('Caltanissetta', 'CL'), ('Catania', 'CT'),
        ('Enna', 'EN'), ('Messina', 'ME'), ('Palermo', 'PA'),
        ('Ragusa', 'RG'), ('Siracusa', 'SR'), ('Trapani', 'TP')]),
    ('Toscana', 'toscana', 'Tuscany', [
        ('Arezzo', 'AR'), ('Firenze', 'FI'), ('Grosseto', 'GR'), ('Livorno', 'LI'),
        ('Lucca', 'LU'), ('Massa-Carrara', 'MS'), ('Pisa', 'PI'),
        ('Pistoia', 'PT'), ('Prato', 'PO'), ('Siena', 'SI')]),
    ('Trentino-Alto Adige', 'trentino-alto-adige', 'Trentino-South Tyrol', [
        ('Bolzano', 'BZ'), ('Trento', 'TN')]),
    ('Umbria', 'umbria', None, [
        ('Perugia', 'PG'), ('Terni', 'TR')]),
    ("Valle d'Aosta", 'valle-d-aosta', 'Aosta Valley', [
        ('Aosta', 'AO')]),
    ('Veneto', 'veneto', None, [
        ('Belluno', 'BL'), ('Padova', 'PD'), ('Rovigo', 'RO'), ('Treviso', 'TV'),
        ('Venezia', 'VE'), ('Verona', 'VR'), ('Vicenza', 'VI')]),
]

# Comuni da creare esplicitamente perche' erano gia' usati come tag.
COMUNI_INIZIALI = [
    ('Rende', 'rende', 'cosenza'),
]
