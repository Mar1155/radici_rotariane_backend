import os
import django

# Configura l'ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from users.models import Skill, SoftSkill

def populate_skills():
    # Hard Skills (Skill model)
    # Format: (Canonical Name, {lang: translation})
    hard_skills = [
        ("Project Management", {"it": "Gestione Progetti"}),
        ("Software Development", {"it": "Sviluppo Software"}),
        ("Data Analysis", {"it": "Analisi Dati"}),
        ("Digital Marketing", {"it": "Marketing Digitale"}),
        ("Financial Planning", {"it": "Pianificazione Finanziaria"}),
        ("Legal Consulting", {"it": "Consulenza Legale"}),
        ("Medical Research", {"it": "Ricerca Medica"}),
        ("Graphic Design", {"it": "Design Grafico"}),
        ("Public Relations", {"it": "Pubbliche Relazioni"}),
        ("Business Strategy", {"it": "Strategia Aziendale"}),
        ("Engineering", {"it": "Ingegneria"}),
        ("Architecture", {"it": "Architettura"}),
        ("Event Planning", {"it": "Pianificazione Eventi"}),
        ("Social Media Management", {"it": "Gestione Social Media"}),
        ("Cybersecurity", {"it": "Sicurezza Informatica"})
    ]

    # Soft Skills (SoftSkill model)
    soft_skills = [
        ("Leadership", {"it": "Leadership"}),
        ("Teamwork", {"it": "Lavoro di Squadra"}),
        ("Communication", {"it": "Comunicazione"}),
        ("Problem Solving", {"it": "Risoluzione Problemi"}),
        ("Time Management", {"it": "Gestione del Tempo"}),
        ("Adaptability", {"it": "Adattabilità"}),
        ("Critical Thinking", {"it": "Pensiero Critico"}),
        ("Conflict Resolution", {"it": "Risoluzione Conflitti"}),
        ("Emotional Intelligence", {"it": "Intelligenza Emotiva"}),
        ("Public Speaking", {"it": "Parlare in Pubblico"}),
        ("Negotiation", {"it": "Negoziazione"}),
        ("Creativity", {"it": "Creatività"}),
        ("Mentoring", {"it": "Mentoring"}),
        ("Decision Making", {"it": "Presa di Decisioni"}),
        ("Empathy", {"it": "Empatia"})
    ]

    print("Popolamento Hard Skills...")
    for name, translations in hard_skills:
        skill, created = Skill.objects.get_or_create(name=name)
        skill.translations = translations
        skill.save()
        if created:
            print(f"Aggiunta: {name}")
        else:
            print(f"Aggiornata: {name}")

    print("\nPopolamento Soft Skills...")
    for name, translations in soft_skills:
        skill, created = SoftSkill.objects.get_or_create(name=name)
        skill.translations = translations
        skill.save()
        if created:
            print(f"Aggiunta: {name}")
        else:
            print(f"Aggiornata: {name}")

    print("\nCompletato!")

if __name__ == "__main__":
    populate_skills()
