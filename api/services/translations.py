"""
Backend translations for SSE progress messages.
"""
from typing import Any

TRANSLATIONS = {
    "en": {
        "organizing_attractions": "Organizing attractions by day...",
        "agent1_organizing": "Agent 1: Organizing attractions by geographic distance...",
        "attractions_organized": "Attractions organized by day",
        "agent2_researching": "Agent 2: Researching attraction details (parallel)...",
        "all_researched": "All attractions researched",
        "generating_document": "Generating document with images and maps...",
        "finding_images": "Finding attraction images...",
        "sending_email": "Sending itinerary to {email}...",
        "approval_prompt": "Please review the proposed itinerary organization. Type 'yes' to approve or describe the changes you'd like.",
        "resuming_after_approval": "Resuming generation with your approval...",
        "itinerary_approved": "Itinerary approved! Researching attractions...",
        "error_no_state": "No final state received from the graph",
    },
    "pt-br": {
        "organizing_attractions": "Organizando atrações por dia...",
        "agent1_organizing": "Agente 1: Organizando atrações por distância geográfica...",
        "attractions_organized": "Atrações organizadas por dia",
        "agent2_researching": "Agente 2: Pesquisando detalhes das atrações (em paralelo)...",
        "all_researched": "Todas as atrações pesquisadas",
        "generating_document": "Gerando documento com imagens e mapas...",
        "finding_images": "Buscando imagens das atrações...",
        "sending_email": "Enviando roteiro para {email}...",
        "approval_prompt": "Por favor, revise a organização do roteiro proposto. Digite 'sim' para aprovar ou descreva as alterações desejadas.",
        "resuming_after_approval": "Retomando geração com sua aprovação...",
        "itinerary_approved": "Roteiro aprovado! Pesquisando atrações...",
        "error_no_state": "Nenhum estado final recebido do grafo",
    },
    "es": {
        "organizing_attractions": "Organizando atracciones por día...",
        "agent1_organizing": "Agente 1: Organizando atracciones por distancia geográfica...",
        "attractions_organized": "Atracciones organizadas por día",
        "agent2_researching": "Agente 2: Investigando detalles de atracciones (en paralelo)...",
        "all_researched": "Todas las atracciones investigadas",
        "generating_document": "Generando documento con imágenes y mapas...",
        "finding_images": "Buscando imágenes de atracciones...",
        "sending_email": "Enviando itinerario a {email}...",
        "approval_prompt": "Por favor, revise la organización del itinerario propuesto. Escriba 'sí' para aprobar o describa los cambios que desea.",
        "resuming_after_approval": "Reanudando generación con su aprobación...",
        "itinerary_approved": "¡Itinerario aprobado! Investigando atracciones...",
        "error_no_state": "No se recibió estado final del grafo",
    },
    "fr": {
        "organizing_attractions": "Organisation des attractions par jour...",
        "agent1_organizing": "Agent 1: Organisation des attractions par distance géographique...",
        "attractions_organized": "Attractions organisées par jour",
        "agent2_researching": "Agent 2: Recherche des détails des attractions (en parallèle)...",
        "all_researched": "Toutes les attractions recherchées",
        "generating_document": "Génération du document avec images et cartes...",
        "finding_images": "Recherche des images d'attractions...",
        "sending_email": "Envoi de l'itinéraire à {email}...",
        "approval_prompt": "Veuillez vérifier l'organisation de l'itinéraire proposé. Tapez 'oui' pour approuver ou décrivez les modifications souhaitées.",
        "resuming_after_approval": "Reprise de la génération avec votre approbation...",
        "itinerary_approved": "Itinéraire approuvé ! Recherche d'attractions...",
        "error_no_state": "Aucun état final reçu du graphe",
    },
}


def get_translation(language: str, key: str, **kwargs: Any) -> str:
    """
    Get a translated string for the given language and key.

    Args:
        language: Language code (en, pt-br, es, fr)
        key: Translation key
        **kwargs: Format parameters for the string

    Returns:
        Translated string, falling back to English if not found
    """
    lang = language if language in TRANSLATIONS else "en"
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text
