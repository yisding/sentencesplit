# -*- coding: utf-8 -*-
import pytest

GOLDEN_FR_RULES_TEST_CASES = [
    (
        "Après avoir été l'un des acteurs du projet génome humain, le Genoscope met aujourd'hui le cap vers la génomique environnementale. L'exploitation des données de séquences, prolongée par l'identification expérimentale des fonctions biologiques, notamment dans le domaine de la biocatalyse, ouvrent des perspectives de développements en biotechnologie industrielle.",
        [
            "Après avoir été l'un des acteurs du projet génome humain, le Genoscope met aujourd'hui le cap vers la génomique environnementale.",
            "L'exploitation des données de séquences, prolongée par l'identification expérimentale des fonctions biologiques, notamment dans le domaine de la biocatalyse, ouvrent des perspectives de développements en biotechnologie industrielle.",
        ],
    ),
    (
        "\"Airbus livrera comme prévu 30 appareils 380 cette année avec en ligne de mire l'objectif d'équilibre financier du programme en 2015\", a-t-il ajouté.",
        [
            "\"Airbus livrera comme prévu 30 appareils 380 cette année avec en ligne de mire l'objectif d'équilibre financier du programme en 2015\", a-t-il ajouté."
        ],
    ),
    (
        "À 11 heures ce matin, la direction ne décomptait que douze grévistes en tout sur la France : ce sont ceux du site de Saran (Loiret), dont l’effectif est de 809 salariés, dont la moitié d’intérimaires. Elle assure que ce mouvement « n’aura aucun impact sur les livraisons ».",
        [
            "À 11 heures ce matin, la direction ne décomptait que douze grévistes en tout sur la France : ce sont ceux du site de Saran (Loiret), dont l’effectif est de 809 salariés, dont la moitié d’intérimaires.",
            "Elle assure que ce mouvement « n’aura aucun impact sur les livraisons ».",
        ],
    ),
    (
        "Ce modèle permet d’afficher le texte « LL.AA.II.RR. » pour l’abréviation de « Leurs Altesses impériales et royales » avec son infobulle.",
        [
            "Ce modèle permet d’afficher le texte « LL.AA.II.RR. » pour l’abréviation de « Leurs Altesses impériales et royales » avec son infobulle."
        ],
    ),
    ("Les derniers ouvrages de Intercept Ltd. sont ici.", ["Les derniers ouvrages de Intercept Ltd. sont ici."]),
    ("J'ai parlé à Mme. Dupont hier.", ["J'ai parlé à Mme. Dupont hier."]),
    ("Le Dr. Martin est arrivé. Il est reparti.", ["Le Dr. Martin est arrivé.", "Il est reparti."]),
    (
        "Rendez-vous avec Pr. Durand demain. Merci de confirmer.",
        ["Rendez-vous avec Pr. Durand demain.", "Merci de confirmer."],
    ),
    ("Nous avons vu Ste. Anne hier.", ["Nous avons vu Ste. Anne hier."]),
    ("No. 12 est disponible. Merci.", ["No. 12 est disponible.", "Merci."]),
    ("Mmes. Dupont et Durand sont là.", ["Mmes. Dupont et Durand sont là."]),
    ("MM. Dupont et Durand sont là.", ["MM. Dupont et Durand sont là."]),
    (
        "Il habite av. Victor-Hugo. Il travaille ici.",
        ["Il habite av. Victor-Hugo.", "Il travaille ici."],
    ),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_FR_RULES_TEST_CASES)
def test_fr_sbd(fr_default_fixture, text, expected_sents):
    """French language SBD tests"""
    segments = fr_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
