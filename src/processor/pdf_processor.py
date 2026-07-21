"""PDF generator for transport optimizer route summaries."""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.utils.logger import LOGGER


# ============================================================================
# Color Palette
# ============================================================================

COLORS = {
    "primary": colors.HexColor("#007ACC"),      # Modern blue
    "secondary": colors.HexColor("#00B4D8"),    # Light blue/teal
    "accent": colors.HexColor("#FF6900"),       # Orange accent
    "dark": colors.HexColor("#2D3A4A"),         # Dark gray-blue
    "text": colors.HexColor("#333333"),         # Dark text
    "light_text": colors.HexColor("#666666"),   # Light gray text
    "background": colors.HexColor("#F8F9FA"),   # Light background
    "success": colors.HexColor("#28A745"),      # Green for savings
    "white": colors.white,
}


# ============================================================================
# Language Labels
# ============================================================================

PDF_LABELS = {
    "en": {
        "title_prefix": "Transport Route",
        "route_overview": "Route Overview",
        "transport_details": "Transport Details",
        "cost_breakdown": "Cost Breakdown",
        "price_explanation": "Price Explanation",
        "payment_methods": "Payment Methods",
        "tracking_apps": "Apps to Track Your Transport",
        "platforms": "Platforms",
        "disclaimer": "Disclaimer: routes, times and prices are estimates and may vary depending on schedules, service changes, and the time this search was made. Please confirm with official sources or the transport apps before traveling.",
        "from": "From",
        "to": "To",
        "mode": "Mode",
        "modes": "Mode(s)",
        "duration": "Duration",
        "distance": "Distance",
        "cost": "Cost",
        "route": "Route",
        "minutes": "min",
        "free": "Free",
        "total": "Total",
        "per_trip": "per trip",
        "day_pass": "Day Pass",
        "weekly_pass": "Weekly Pass",
        "pros": "Pros",
        "cons": "Cons",
        "sources": "Sources",
        "rules_applied": "Rules Applied",
        "compound_trip": "Compound Trip",
        "simple_trip": "Simple Trip",
        "generated_on": "Generated on",
        "powered_by": "Powered by TravelerAI Transport Optimizer",
        "transport_modes": {
            "walking": "Walking",
            "subway": "Subway",
            "metro": "Metro",
            "bus": "Bus",
            "train": "Train",
            "driving": "Driving",
            "tram": "Tram",
            "transit": "Transit",
        },
    },
    "pt-br": {
        "title_prefix": "Rota de Transporte",
        "route_overview": "Visão Geral da Rota",
        "transport_details": "Detalhes do Transporte",
        "cost_breakdown": "Detalhamento de Custos",
        "price_explanation": "Explicação de Preços",
        "payment_methods": "Métodos de Pagamento",
        "tracking_apps": "Apps para Acompanhar seu Transporte",
        "platforms": "Plataformas",
        "disclaimer": "Aviso: as rotas, horários e preços são estimativas e podem variar conforme os horários, mudanças no serviço e o momento em que esta pesquisa foi feita. Confirme com fontes oficiais ou com os apps de transporte antes de viajar.",
        "from": "De",
        "to": "Para",
        "mode": "Modo",
        "modes": "Modo(s)",
        "duration": "Duração",
        "distance": "Distância",
        "cost": "Custo",
        "route": "Rota",
        "minutes": "min",
        "free": "Grátis",
        "total": "Total",
        "per_trip": "por viagem",
        "day_pass": "Passe Diário",
        "weekly_pass": "Passe Semanal",
        "pros": "Prós",
        "cons": "Contras",
        "sources": "Fontes",
        "rules_applied": "Regras Aplicadas",
        "compound_trip": "Viagem Composta",
        "simple_trip": "Viagem Simples",
        "generated_on": "Gerado em",
        "powered_by": "Desenvolvido por TravelerAI Transport Optimizer",
        "transport_modes": {
            "walking": "A pé",
            "subway": "Metrô",
            "metro": "Metrô",
            "bus": "Ônibus",
            "train": "Trem",
            "driving": "Carro",
            "tram": "Bonde",
            "transit": "Transporte público",
        },
    },
    "es": {
        "title_prefix": "Ruta de Transporte",
        "route_overview": "Resumen de la Ruta",
        "transport_details": "Detalles del Transporte",
        "cost_breakdown": "Desglose de Costos",
        "price_explanation": "Explicación de Precios",
        "payment_methods": "Métodos de Pago",
        "tracking_apps": "Apps para Seguir tu Transporte",
        "platforms": "Plataformas",
        "disclaimer": "Aviso: las rutas, horarios y precios son estimaciones y pueden variar según los horarios, cambios en el servicio y el momento en que se realizó esta búsqueda. Confirma con fuentes oficiales o con las apps de transporte antes de viajar.",
        "from": "Desde",
        "to": "Hasta",
        "mode": "Modo",
        "modes": "Modo(s)",
        "duration": "Duración",
        "distance": "Distancia",
        "cost": "Costo",
        "route": "Ruta",
        "minutes": "min",
        "free": "Gratis",
        "total": "Total",
        "per_trip": "por viaje",
        "day_pass": "Pase Diario",
        "weekly_pass": "Pase Semanal",
        "pros": "Ventajas",
        "cons": "Desventajas",
        "sources": "Fuentes",
        "rules_applied": "Reglas Aplicadas",
        "compound_trip": "Viaje Compuesto",
        "simple_trip": "Viaje Simple",
        "generated_on": "Generado el",
        "powered_by": "Desarrollado por TravelerAI Transport Optimizer",
        "transport_modes": {
            "walking": "A pie",
            "subway": "Metro",
            "metro": "Metro",
            "bus": "Autobús",
            "train": "Tren",
            "driving": "Coche",
            "tram": "Tranvía",
            "transit": "Transporte público",
        },
    },
    "fr": {
        "title_prefix": "Itinéraire de Transport",
        "route_overview": "Aperçu de l'Itinéraire",
        "transport_details": "Détails du Transport",
        "cost_breakdown": "Détail des Coûts",
        "price_explanation": "Explication des Prix",
        "payment_methods": "Moyens de Paiement",
        "tracking_apps": "Applis pour Suivre vos Transports",
        "platforms": "Plateformes",
        "disclaimer": "Avertissement : les itinéraires, horaires et prix sont des estimations et peuvent varier selon les horaires, les changements de service et le moment où cette recherche a été effectuée. Veuillez vérifier auprès des sources officielles ou des applis de transport avant de voyager.",
        "from": "De",
        "to": "À",
        "mode": "Mode",
        "modes": "Mode(s)",
        "duration": "Durée",
        "distance": "Distance",
        "cost": "Coût",
        "route": "Itinéraire",
        "minutes": "min",
        "free": "Gratuit",
        "total": "Total",
        "per_trip": "par trajet",
        "day_pass": "Pass Journée",
        "weekly_pass": "Pass Semaine",
        "pros": "Avantages",
        "cons": "Inconvénients",
        "sources": "Sources",
        "rules_applied": "Règles Appliquées",
        "compound_trip": "Trajet Composé",
        "simple_trip": "Trajet Simple",
        "generated_on": "Généré le",
        "powered_by": "Propulsé par TravelerAI Transport Optimizer",
        "transport_modes": {
            "walking": "À pied",
            "subway": "Métro",
            "metro": "Métro",
            "bus": "Bus",
            "train": "Train",
            "driving": "Voiture",
            "tram": "Tramway",
            "transit": "Transport en commun",
        },
    },
}


def _get_labels(language: str) -> Dict[str, str]:
    """Get language-specific labels."""
    return PDF_LABELS.get(language, PDF_LABELS["en"])


def _translate_mode(mode: str, labels: Dict[str, Any]) -> str:
    """Translate a transport mode to the target language."""
    mode_lower = mode.lower()
    transport_modes = labels.get("transport_modes", {})
    translated = transport_modes.get(mode_lower)
    if translated:
        return translated
    # Fallback: capitalize the original mode
    return mode.capitalize()


# ============================================================================
# PDF Generator Class
# ============================================================================

class RoutePDFGenerator:
    """Generate PDF summary of optimized transport route."""

    def __init__(self, output_dir: str = "./.results"):
        """Initialize the PDF generator.

        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        LOGGER.info(f"RoutePDFGenerator initialized with output_dir: {output_dir}")

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles."""
        styles = getSampleStyleSheet()

        custom_styles = {
            "Title": ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=COLORS["primary"],
                spaceAfter=20,
                alignment=TA_CENTER,
            ),
            "Subtitle": ParagraphStyle(
                "CustomSubtitle",
                parent=styles["Normal"],
                fontSize=12,
                textColor=COLORS["light_text"],
                spaceAfter=30,
                alignment=TA_CENTER,
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                parent=styles["Heading2"],
                fontSize=16,
                textColor=COLORS["dark"],
                spaceBefore=20,
                spaceAfter=10,
                borderColor=COLORS["primary"],
                borderWidth=1,
                borderPadding=5,
            ),
            "Body": ParagraphStyle(
                "CustomBody",
                parent=styles["Normal"],
                fontSize=11,
                textColor=COLORS["text"],
                spaceAfter=8,
                leading=14,
            ),
            "Highlight": ParagraphStyle(
                "Highlight",
                parent=styles["Normal"],
                fontSize=12,
                textColor=COLORS["primary"],
                fontName="Helvetica-Bold",
                spaceAfter=8,
            ),
            "Footer": ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=9,
                textColor=COLORS["light_text"],
                alignment=TA_CENTER,
            ),
        }

        return custom_styles

    def _create_route_table(
        self,
        route_pairs: List[Dict[str, Any]],
        preferences: List[Dict[str, Any]],
        route_cost_analyses: List[Dict[str, Any]],
        labels: Dict[str, str]
    ) -> Table:
        """Create the route overview table."""
        # Build cost lookup by pair_index
        cost_by_pair = {a["pair_index"]: a for a in route_cost_analyses}

        # Cell style for text wrapping inside table cells
        cell_style = ParagraphStyle(
            "RouteTableCell", fontName="Helvetica", fontSize=9,
            leading=11, alignment=TA_CENTER,
        )

        # Table header
        header = [
            labels["from"],
            labels["to"],
            labels["mode"],
            labels["duration"],
            labels["cost"]
        ]

        # Table data
        data = [header]

        # Sort preferences by pair_index to match route order
        sorted_preferences = sorted(preferences, key=lambda p: p.get("pair_index", 0))

        for pref in sorted_preferences:
            pair_index = pref.get("pair_index", 0)
            if pair_index < len(route_pairs):
                pair = route_pairs[pair_index]
                details = pref.get("transport_details", {})

                # Get cost from route_cost_analyses by pair_index
                mode = pref.get("selected_mode", "").lower()
                if mode in ["walking", "walk"]:
                    cost_str = labels["free"]
                else:
                    analysis = cost_by_pair.get(pair_index, {})
                    cost_val = analysis.get("total_cost", 0)
                    currency = analysis.get("currency", "EUR")
                    if cost_val and cost_val > 0:
                        cost_str = f"{currency} {cost_val:.2f}"
                    else:
                        cost_str = labels["free"]

                row = [
                    Paragraph(pair.get("start_display") or pair.get("start_place", ""), cell_style),
                    Paragraph(pair.get("end_display") or pair.get("end_place", ""), cell_style),
                    _translate_mode(pref.get("selected_mode", ""), labels),
                    f"{details.get('duration_minutes', '?')} {labels['minutes']}",
                    cost_str
                ]
                data.append(row)

        # Create table
        table = Table(data, colWidths=[4.5*cm, 4.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])

        # Style the table
        table.setStyle(TableStyle([
            # Header style
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["white"]),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("LEFTPADDING", (0, 0), (-1, 0), 10),
            ("RIGHTPADDING", (0, 0), (-1, 0), 10),

            # Body style
            ("BACKGROUND", (0, 1), (-1, -1), COLORS["white"]),
            ("TEXTCOLOR", (0, 1), (-1, -1), COLORS["text"]),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ("TOPPADDING", (0, 1), (-1, -1), 10),
            ("LEFTPADDING", (0, 1), (-1, -1), 10),
            ("RIGHTPADDING", (0, 1), (-1, -1), 10),

            # Alternating row colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["background"]]),

            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, COLORS["light_text"]),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        return table

    def _create_route_cost_summary_table(
        self,
        route_pairs: List[Dict[str, Any]],
        route_cost_analyses: List[Dict[str, Any]],
        labels: Dict[str, str]
    ) -> Optional[Table]:
        """Create a per-route cost summary table with grand total."""
        if not route_cost_analyses:
            return None

        # Cell styles for text wrapping inside table cells
        cell_style = ParagraphStyle(
            "CostTableCell", fontName="Helvetica", fontSize=9, leading=11,
        )
        cell_style_bold = ParagraphStyle(
            "CostTableCellBold", fontName="Helvetica-Bold", fontSize=9, leading=11,
        )

        # Table header: Route (From → To), Mode(s), Cost, Currency
        header = [labels["route"], labels["modes"], labels["cost"], ""]
        data = [header]

        grand_total = 0.0
        currency = "EUR"

        # Sort by pair_index for consistent order
        sorted_analyses = sorted(route_cost_analyses, key=lambda a: a.get("pair_index", 0))

        for analysis in sorted_analyses:
            pair_idx = analysis.get("pair_index", 0)
            modes_list = analysis.get("modes", [])
            modes_translated = ", ".join(_translate_mode(m, labels) for m in modes_list)
            total_cost = analysis.get("total_cost", 0)
            currency = analysis.get("currency", "EUR")
            grand_total += total_cost

            # Build route label
            if pair_idx < len(route_pairs):
                pair = route_pairs[pair_idx]
                start_name = pair.get("start_display") or pair.get("start_place", "")
                end_name = pair.get("end_display") or pair.get("end_place", "")
                route_label = f"{start_name} → {end_name}"
            else:
                route_label = f"Route {pair_idx + 1}"

            data.append([
                Paragraph(route_label, cell_style),
                Paragraph(modes_translated, cell_style),
                f"{currency} {total_cost:.2f}",
                ""
            ])

        # Grand total row
        data.append([Paragraph(labels["total"], cell_style_bold), "", f"{currency} {grand_total:.2f}", ""])

        # Create table — wider route column to avoid overlap
        table = Table(data, colWidths=[7.5*cm, 2.5*cm, 2.5*cm, 0.5*cm])

        table.setStyle(TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["secondary"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["white"]),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),

            # Body
            ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),

            # Total row
            ("BACKGROUND", (0, -1), (-1, -1), COLORS["background"]),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (2, -1), (2, -1), COLORS["primary"]),

            # Grid and alignment
            ("GRID", (0, 0), (-1, -1), 0.5, COLORS["light_text"]),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        return table

    def _create_price_explanation_section(
        self,
        route_pairs: List[Dict[str, Any]],
        route_cost_analyses: List[Dict[str, Any]],
        labels: Dict[str, str],
        styles: Dict[str, ParagraphStyle],
    ) -> List:
        """Create the price explanation section with per-route details."""
        elements = []

        # Sort by pair_index for consistent order with other sections
        sorted_analyses = sorted(route_cost_analyses, key=lambda a: a.get("pair_index", 0))

        for analysis in sorted_analyses:
            pair_idx = analysis.get("pair_index", 0)
            is_compound = analysis.get("is_compound", False)
            explanation = analysis.get("explanation", "")
            rules_applied = analysis.get("rules_applied")
            source_links = analysis.get("source_links", [])
            modes_list = analysis.get("modes", [])
            modes_translated = ", ".join(_translate_mode(m, labels) for m in modes_list)

            # Route header
            if pair_idx < len(route_pairs):
                pair = route_pairs[pair_idx]
                start_name = pair.get("start_display") or pair.get("start_place", "")
                end_name = pair.get("end_display") or pair.get("end_place", "")
                route_label = f"{start_name} → {end_name}"
            else:
                route_label = f"Route {pair_idx + 1}"

            trip_type = labels["compound_trip"] if is_compound else labels["simple_trip"]
            header_text = f"<b>{route_label}</b> ({trip_type} — {modes_translated})"
            elements.append(Paragraph(header_text, styles["Highlight"]))

            # Explanation
            if explanation:
                explanation_text = explanation.replace("\n", "<br/>")
                elements.append(Paragraph(explanation_text, styles["Body"]))

            # Rules applied
            if rules_applied:
                rules_text = f"<b>{labels['rules_applied']}:</b> {rules_applied}"
                elements.append(Paragraph(rules_text, styles["Body"]))

            # Source links
            if source_links:
                links_text = f"<b>{labels['sources']}:</b><br/>"
                for link in source_links:
                    links_text += f'• <a href="{link}" color="blue">{link}</a><br/>'
                elements.append(Paragraph(links_text, styles["Body"]))

            elements.append(Spacer(1, 10))

        return elements

    def _create_payment_methods_section(
        self,
        payment_methods_info: List[Dict[str, Any]],
        labels: Dict[str, str],
        styles: Dict[str, ParagraphStyle],
    ) -> List:
        """Create the payment methods section with pros/cons."""
        elements = []

        for pm in payment_methods_info:
            name = pm.get("name", "")
            description = pm.get("description", "")
            pros = pm.get("pros", [])
            cons = pm.get("cons", [])
            source_links = pm.get("source_links", [])

            # Name header
            elements.append(Paragraph(f"<b>{name}</b>", styles["Highlight"]))

            # Description
            if description:
                desc_text = description.replace("\n", "<br/>")
                elements.append(Paragraph(desc_text, styles["Body"]))

            # Pros
            if pros:
                pros_text = f"<b>{labels['pros']}:</b><br/>"
                for pro in pros:
                    pros_text += f"• {pro}<br/>"
                elements.append(Paragraph(pros_text, styles["Body"]))

            # Cons
            if cons:
                cons_text = f"<b>{labels['cons']}:</b><br/>"
                for con in cons:
                    cons_text += f"• {con}<br/>"
                elements.append(Paragraph(cons_text, styles["Body"]))

            # Source links
            if source_links:
                links_text = f"<b>{labels['sources']}:</b><br/>"
                for link in source_links:
                    links_text += f'• <a href="{link}" color="blue">{link}</a><br/>'
                elements.append(Paragraph(links_text, styles["Body"]))

            elements.append(Spacer(1, 10))

        return elements

    def _create_tracking_apps_section(
        self,
        transport_apps: List[Dict[str, Any]],
        labels: Dict[str, str],
        styles: Dict[str, ParagraphStyle],
    ) -> List:
        """Create the transport-tracking apps section."""
        elements = []

        for app in transport_apps:
            name = app.get("name", "")
            description = app.get("description", "")
            platforms = app.get("platforms", [])
            source_links = app.get("source_links", [])

            # Name header
            elements.append(Paragraph(f"<b>{name}</b>", styles["Highlight"]))

            # Description
            if description:
                desc_text = description.replace("\n", "<br/>")
                elements.append(Paragraph(desc_text, styles["Body"]))

            # Platforms
            if platforms:
                platforms_text = f"<b>{labels['platforms']}:</b> {', '.join(platforms)}"
                elements.append(Paragraph(platforms_text, styles["Body"]))

            # Source links
            if source_links:
                links_text = f"<b>{labels['sources']}:</b><br/>"
                for link in source_links:
                    links_text += f'• <a href="{link}" color="blue">{link}</a><br/>'
                elements.append(Paragraph(links_text, styles["Body"]))

            elements.append(Spacer(1, 10))

        return elements

    def create_document(
        self,
        title: str,
        route_pairs: List[Dict[str, Any]],
        preferences: List[Dict[str, Any]],
        route_cost_analyses: List[Dict[str, Any]],
        payment_methods_info: List[Dict[str, Any]],
        transport_apps: List[Dict[str, Any]] = None,
        city: str = "",
        language: str = "en"
    ) -> str:
        """Create a PDF document with the route summary.

        Args:
            title: Document title
            route_pairs: List of route pairs
            preferences: User's transport preferences
            route_cost_analyses: Per-route cost analysis data
            payment_methods_info: Payment methods with pros/cons
            transport_apps: Transport-tracking apps to include
            city: City name
            language: Output language

        Returns:
            Path to the generated PDF
        """
        transport_apps = transport_apps or []

        LOGGER.info(f"=== PDF CREATION START ===")
        LOGGER.info(f"Title: {title}")
        LOGGER.info(f"Route pairs: {len(route_pairs)}")
        LOGGER.info(f"Route cost analyses: {len(route_cost_analyses)}")
        LOGGER.info(f"Payment methods: {len(payment_methods_info)}")
        LOGGER.info(f"Transport apps: {len(transport_apps)}")
        LOGGER.info(f"Language: {language}")

        labels = _get_labels(language)
        styles = self._create_styles()

        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title.replace(" ", "_")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        # Create document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Build content
        content = []

        # Title
        content.append(Paragraph(title, styles["Title"]))
        if city:
            content.append(Paragraph(city, styles["Subtitle"]))
        content.append(Spacer(1, 10))

        # Horizontal line
        content.append(HRFlowable(
            width="100%",
            thickness=2,
            color=COLORS["primary"],
            spaceAfter=20
        ))

        # Disclaimer (estimates may vary with schedules / time of search)
        disclaimer_text = labels.get("disclaimer")
        if disclaimer_text:
            content.append(Paragraph(f"<i>{disclaimer_text}</i>", styles["Footer"]))
            content.append(Spacer(1, 16))

        # Sort route_pairs by pair_index for consistent ordering
        route_pairs = sorted(route_pairs, key=lambda p: p.get("pair_index", 0))

        # 1. Route Overview Table
        content.append(Paragraph(labels["route_overview"], styles["SectionHeader"]))
        content.append(Spacer(1, 10))
        route_table = self._create_route_table(route_pairs, preferences, route_cost_analyses, labels)
        content.append(route_table)
        content.append(Spacer(1, 20))

        # 2. Cost Summary Table (per-route with grand total)
        cost_summary_table = self._create_route_cost_summary_table(route_pairs, route_cost_analyses, labels)
        if cost_summary_table:
            content.append(Paragraph(labels["cost_breakdown"], styles["SectionHeader"]))
            content.append(Spacer(1, 10))
            content.append(cost_summary_table)
            content.append(Spacer(1, 20))

        # 3. Price Explanation Section (per-route details with source links)
        if route_cost_analyses:
            content.append(Paragraph(labels["price_explanation"], styles["SectionHeader"]))
            content.append(Spacer(1, 10))
            explanation_elements = self._create_price_explanation_section(
                route_pairs, route_cost_analyses, labels, styles
            )
            content.extend(explanation_elements)
            content.append(Spacer(1, 10))

        # 4. Payment Methods Section (with pros/cons and source links)
        if payment_methods_info:
            content.append(Paragraph(labels["payment_methods"], styles["SectionHeader"]))
            content.append(Spacer(1, 10))
            payment_elements = self._create_payment_methods_section(
                payment_methods_info, labels, styles
            )
            content.extend(payment_elements)
            content.append(Spacer(1, 10))

        # 5. Transport-tracking Apps Section
        if transport_apps:
            content.append(Paragraph(labels["tracking_apps"], styles["SectionHeader"]))
            content.append(Spacer(1, 10))
            apps_elements = self._create_tracking_apps_section(
                transport_apps, labels, styles
            )
            content.extend(apps_elements)
            content.append(Spacer(1, 10))

        # 6. Footer
        content.append(Spacer(1, 30))
        content.append(HRFlowable(
            width="100%",
            thickness=1,
            color=COLORS["light_text"],
            spaceAfter=10
        ))

        generated_text = f"{labels['generated_on']} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        content.append(Paragraph(generated_text, styles["Footer"]))
        content.append(Paragraph(labels["powered_by"], styles["Footer"]))

        # Build PDF
        doc.build(content)

        LOGGER.info(f"PDF generated successfully: {filepath}")
        return filepath


# ============================================================================
# Itinerary PDF Generator
# ============================================================================

# Color palette for itinerary PDFs
ITINERARY_COLORS = {
    "primary": colors.HexColor("#1E40AF"),      # Dark blue
    "secondary": colors.HexColor("#3B82F6"),    # Light blue
    "accent": colors.HexColor("#F59E0B"),       # Amber accent
    "dark": colors.HexColor("#1E293B"),         # Slate dark
    "text": colors.HexColor("#334155"),         # Slate text
    "light_text": colors.HexColor("#64748B"),   # Slate light
    "background": colors.HexColor("#F8FAFC"),   # Slate 50
    "success": colors.HexColor("#10B981"),      # Emerald
    "white": colors.white,
}

# Language labels for itinerary PDFs
ITINERARY_PDF_LABELS = {
    "en": {
        "title_suffix": "Travel Itinerary",
        "day": "Day",
        "ticket_info": "Ticket Information",
        "useful_links": "Useful Links",
        "cost_summary": "Estimated Costs",
        "total": "Total",
        "route_map": "Route Map",
        "map_legend": "Colored markers indicate attractions grouped by day",
        "per_person": "*Estimated values per person",
        "generated_on": "Generated on",
        "powered_by": "Powered by TravelerAI Itinerary Generator",
        "unnamed_attraction": "Unnamed Attraction",
        "table_of_contents": "Table of Contents",
        "overview": "Itinerary Overview",
        "attractions": "Attractions",
        "estimated_daily_cost": "Est. Daily Cost",
        "num_attractions": "Qty",
    },
    "pt-br": {
        "title_suffix": "Roteiro de Viagem",
        "day": "Dia",
        "ticket_info": "Informações de Ingresso",
        "useful_links": "Links Úteis",
        "cost_summary": "Custos Estimados",
        "total": "Total",
        "route_map": "Mapa do Roteiro",
        "map_legend": "Marcadores coloridos indicam atrações agrupadas por dia",
        "per_person": "*Valores estimados por pessoa",
        "generated_on": "Gerado em",
        "powered_by": "Desenvolvido por TravelerAI Itinerary Generator",
        "unnamed_attraction": "Atração sem nome",
        "table_of_contents": "Sumário",
        "overview": "Visão Geral do Roteiro",
        "attractions": "Atrações",
        "estimated_daily_cost": "Custo Diário Est.",
        "num_attractions": "Qtd",
    },
    "es": {
        "title_suffix": "Itinerario de Viaje",
        "day": "Dia",
        "ticket_info": "Información de Entrada",
        "useful_links": "Enlaces Útiles",
        "cost_summary": "Costos Estimados",
        "total": "Total",
        "route_map": "Mapa de la Ruta",
        "map_legend": "Marcadores de colores indican atracciones agrupadas por día",
        "per_person": "*Valores estimados por persona",
        "generated_on": "Generado el",
        "powered_by": "Desarrollado por TravelerAI Itinerary Generator",
        "unnamed_attraction": "Atracción sin nombre",
        "table_of_contents": "Indice",
        "overview": "Resumen del Itinerario",
        "attractions": "Atracciones",
        "estimated_daily_cost": "Costo Diario Est.",
        "num_attractions": "Cant.",
    },
    "fr": {
        "title_suffix": "Itinéraire de Voyage",
        "day": "Jour",
        "ticket_info": "Informations sur les Billets",
        "useful_links": "Liens Utiles",
        "cost_summary": "Coûts Estimés",
        "total": "Total",
        "route_map": "Carte de l'Itinéraire",
        "map_legend": "Les marqueurs colorés indiquent les attractions regroupées par jour",
        "per_person": "*Valeurs estimées par personne",
        "generated_on": "Généré le",
        "powered_by": "Propulsé par TravelerAI Itinerary Generator",
        "unnamed_attraction": "Attraction sans nom",
        "table_of_contents": "Table des Matieres",
        "overview": "Apercu de l'Itineraire",
        "attractions": "Attractions",
        "estimated_daily_cost": "Cout Journalier Est.",
        "num_attractions": "Qté",
    },
}


def _get_itinerary_labels(language: str) -> Dict[str, str]:
    """Get language-specific labels for itinerary PDF."""
    return ITINERARY_PDF_LABELS.get(language, ITINERARY_PDF_LABELS["en"])


class ItineraryPDFGenerator:
    """PDF generator for travel itineraries with modern design."""

    # Page layout: A4 width = 21cm, with 2cm margins on each side
    CONTENT_WIDTH = 17*cm
    # Minimum image area for quality filtering
    MIN_IMAGE_AREA = 250000
    # Image compression settings
    MAX_IMAGE_WIDTH = 1200
    JPEG_QUALITY = 80
    # Headers to mimic browser requests
    IMAGE_REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, output_dir: str = "./.results"):
        """Initialize the itinerary PDF generator.

        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._temp_files = []  # Track temp files for cleanup
        LOGGER.info(f"ItineraryPDFGenerator initialized with output_dir: {output_dir}")

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles for itinerary."""
        styles = getSampleStyleSheet()

        custom_styles = {
            "Title": ParagraphStyle(
                "ItineraryTitle",
                parent=styles["Heading1"],
                fontSize=28,
                textColor=ITINERARY_COLORS["primary"],
                spaceAfter=10,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            ),
            "Subtitle": ParagraphStyle(
                "ItinerarySubtitle",
                parent=styles["Normal"],
                fontSize=12,
                textColor=ITINERARY_COLORS["light_text"],
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName="Helvetica-Oblique",
            ),
            "DayHeader": ParagraphStyle(
                "DayHeader",
                parent=styles["Heading1"],
                fontSize=20,
                textColor=ITINERARY_COLORS["white"],
                spaceBefore=20,
                spaceAfter=15,
                fontName="Helvetica-Bold",
                alignment=TA_LEFT,
            ),
            "AttractionHeader": ParagraphStyle(
                "AttractionHeader",
                parent=styles["Heading2"],
                fontSize=16,
                textColor=ITINERARY_COLORS["dark"],
                spaceBefore=15,
                spaceAfter=8,
                fontName="Helvetica-Bold",
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                parent=styles["Heading3"],
                fontSize=12,
                textColor=ITINERARY_COLORS["primary"],
                spaceBefore=12,
                spaceAfter=6,
                fontName="Helvetica-Bold",
            ),
            "Body": ParagraphStyle(
                "ItineraryBody",
                parent=styles["Normal"],
                fontSize=10,
                textColor=ITINERARY_COLORS["text"],
                spaceAfter=6,
                leading=16,  # Increased for better readability
                fontName="Helvetica",
            ),
            "Bullet": ParagraphStyle(
                "ItineraryBullet",
                parent=styles["Normal"],
                fontSize=10,
                textColor=ITINERARY_COLORS["text"],
                spaceAfter=4,
                leading=15,  # Increased for better readability
                leftIndent=15,
                fontName="Helvetica",
            ),
            "Link": ParagraphStyle(
                "ItineraryLink",
                parent=styles["Normal"],
                fontSize=10,
                textColor=ITINERARY_COLORS["primary"],
                spaceAfter=4,
                leading=14,  # Increased for better readability
                leftIndent=15,
                fontName="Helvetica",
            ),
            "Caption": ParagraphStyle(
                "ImageCaption",
                parent=styles["Normal"],
                fontSize=9,
                textColor=ITINERARY_COLORS["light_text"],
                spaceBefore=6,
                spaceAfter=8,
                alignment=TA_CENTER,
                fontName="Helvetica-Oblique",
            ),
            "Footer": ParagraphStyle(
                "ItineraryFooter",
                parent=styles["Normal"],
                fontSize=9,
                textColor=ITINERARY_COLORS["light_text"],
                alignment=TA_CENTER,
                fontName="Helvetica",
            ),
            "CostHeader": ParagraphStyle(
                "CostHeader",
                parent=styles["Heading2"],
                fontSize=18,
                textColor=ITINERARY_COLORS["primary"],
                spaceBefore=20,
                spaceAfter=10,
                fontName="Helvetica-Bold",
            ),
        }

        return custom_styles

    def _download_image(self, url: str, image_id: str = "img") -> Optional[str]:
        """Download and optimize image, return temp file path.

        Args:
            url: Image URL to download
            image_id: Unique identifier for temp file naming

        Returns:
            Path to temp file or None if download failed
        """
        import requests
        from PIL import Image as PILImage
        from io import BytesIO

        try:
            LOGGER.info(f"Downloading image: {url[:80]}...")
            response = requests.get(url, timeout=30, headers=self.IMAGE_REQUEST_HEADERS)

            if response.status_code != 200:
                LOGGER.warning(f"Failed to download image: HTTP {response.status_code}")
                return None

            # Load image
            img = PILImage.open(BytesIO(response.content))
            LOGGER.debug(f"Image loaded: {img.size}, format: {img.format}")

            # Check minimum resolution
            width, height = img.size
            if (width * height) < self.MIN_IMAGE_AREA:
                LOGGER.info(f"Skipping low-resolution image: {img.size}")
                return None

            # Resize if too large
            if width > self.MAX_IMAGE_WIDTH:
                ratio = self.MAX_IMAGE_WIDTH / width
                new_size = (self.MAX_IMAGE_WIDTH, int(height * ratio))
                img = img.resize(new_size, PILImage.LANCZOS)
                LOGGER.debug(f"Image resized to {new_size}")

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Save to temp file
            temp_path = os.path.join(self.output_dir, f"temp_{image_id}_{datetime.now().strftime('%H%M%S%f')}.jpg")
            img.save(temp_path, "JPEG", quality=self.JPEG_QUALITY, optimize=True)
            self._temp_files.append(temp_path)

            LOGGER.debug(f"Image saved to temp: {temp_path}")
            return temp_path

        except Exception as e:
            LOGGER.error(f"Error downloading image: {e}")
            return None

    def _cleanup_temp_files(self):
        """Remove all temporary files created during PDF generation."""
        for temp_path in self._temp_files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                LOGGER.warning(f"Failed to remove temp file {temp_path}: {e}")
        self._temp_files = []

    def _sanitize_text(self, text: str) -> str:
        """Replace Unicode chars that Helvetica can't render."""
        if not text:
            return text
        replacements = {
            '\u2013': '-',   # en-dash
            '\u2014': '-',   # em-dash
            '\u2018': "'",   # left single quote
            '\u2019': "'",   # right single quote
            '\u201c': '"',   # left double quote
            '\u201d': '"',   # right double quote
            '\u2026': '...', # ellipsis
            '\u2010': '-',   # hyphen
            '\u2011': '-',   # non-breaking hyphen
            '\u2212': '-',   # minus sign
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _create_day_header(self, day_num: int, labels: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> List:
        """Create styled day header with colored background and anchor."""
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        elements = []

        # Create header text with anchor for TOC navigation
        header_text = f'<a name="day_{day_num}"/>{labels["day"]} {day_num}'

        # Create a table with colored background for the day header
        day_table = RLTable(
            [[Paragraph(header_text, styles["DayHeader"])]],
            colWidths=[self.CONTENT_WIDTH]
        )
        day_table.setStyle(RLTableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ITINERARY_COLORS["primary"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 15),
            ("RIGHTPADDING", (0, 0), (-1, -1), 15),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        elements.append(Spacer(1, 15))
        elements.append(day_table)
        elements.append(Spacer(1, 10))

        return elements

    def _create_image_grid(self, images: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle], max_images: int = 5) -> List:
        """Create full-width images with captions (one per row).

        Args:
            images: List of image dicts with url_regular, caption, id
            styles: Paragraph styles
            max_images: Maximum number of images to include

        Returns:
            List of flowable elements
        """
        from reportlab.platypus import Image as RLImage
        from PIL import Image as PILImage

        elements = []

        for i, img in enumerate(images[:max_images]):
            if not isinstance(img, dict):
                continue

            url = img.get("url_regular")
            if not url:
                continue

            temp_path = self._download_image(url, img.get("id", f"img_{i}"))
            if not temp_path:
                continue

            try:
                # Get actual image dimensions to calculate aspect ratio
                pil_img = PILImage.open(temp_path)
                img_width, img_height = pil_img.size
                aspect_ratio = img_width / img_height

                # Full content width, height based on aspect ratio
                display_width = self.CONTENT_WIDTH
                display_height = display_width / aspect_ratio

                # Cap height at 12cm to avoid overly tall images
                max_height = 12*cm
                if display_height > max_height:
                    display_height = max_height
                    display_width = display_height * aspect_ratio

                rl_image = RLImage(temp_path, width=display_width, height=display_height)
                rl_image.hAlign = 'CENTER'
                elements.append(rl_image)

                # Caption with spacing
                caption = img.get("caption", "")
                if caption:
                    elements.append(Paragraph(self._sanitize_text(caption), styles["Caption"]))

                elements.append(Spacer(1, 10))

            except Exception as e:
                LOGGER.error(f"Error creating image element: {e}")

        return elements

    def _create_ticket_section(self, ticket_info: List[Dict[str, Any]], labels: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> List:
        """Create ticket information section with clickable links.

        Args:
            ticket_info: List of ticket info dicts with content, url, title
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        elements = []

        if not ticket_info:
            return elements

        # Section header
        elements.append(Paragraph(labels["ticket_info"], styles["SectionHeader"]))

        # Create content
        for info in ticket_info:
            if not isinstance(info, dict):
                continue

            content = self._sanitize_text(info.get("content", ""))
            url = info.get("url")
            title = self._sanitize_text(info.get("title", ""))

            if content:
                elements.append(Paragraph(f"• {content}", styles["Bullet"]))

            if url:
                link_title = title if title else "Link"
                # Create clickable hyperlink
                link_text = f'<a href="{url}" color="#2563EB">{link_title}</a>'
                elements.append(Paragraph(f"  → {link_text}", styles["Link"]))

        elements.append(Spacer(1, 8))
        return elements

    def _create_links_section(self, useful_links: List[Dict[str, Any]], labels: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> List:
        """Create useful links section with clickable hyperlinks.

        Args:
            useful_links: List of link dicts with title, url
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        elements = []

        if not useful_links:
            return elements

        # Section header
        elements.append(Paragraph(labels["useful_links"], styles["SectionHeader"]))

        # Create clickable links
        for link in useful_links:
            if not isinstance(link, dict):
                continue

            title = self._sanitize_text(link.get("title", "Link"))
            url = link.get("url", "")

            if url:
                # Create clickable hyperlink
                link_text = f'<a href="{url}" color="#2563EB">{title}</a>'
                elements.append(Paragraph(f"• {link_text}", styles["Link"]))

        elements.append(Spacer(1, 8))
        return elements

    def _create_attraction_section(self, attraction: Dict[str, Any], day_num: int, labels: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> List:
        """Create all elements for a single attraction.

        Args:
            attraction: Attraction data dict
            day_num: Day number (unused, kept for API compatibility)
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        elements = []

        name = self._sanitize_text(attraction.get("name", labels["unnamed_attraction"]))
        description = self._sanitize_text(attraction.get("description", ""))

        # Attraction header with colored accent
        header_table = RLTable(
            [[Paragraph(name, styles["AttractionHeader"])]],
            colWidths=[self.CONTENT_WIDTH]
        )
        header_table.setStyle(RLTableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 2, ITINERARY_COLORS["primary"]),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 12))

        # Description with bullet points support
        if description:
            # Fallback: if no newlines but " - " bullets exist, insert newlines
            if '\n' not in description and ' - ' in description:
                import re
                description = re.sub(r' (?=- )', '\n', description)

            lines = description.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('- '):
                    # Bullet point
                    bullet_text = line[2:]
                    elements.append(Paragraph(f"• {bullet_text}", styles["Bullet"]))
                else:
                    # Regular paragraph
                    elements.append(Paragraph(line, styles["Body"]))

        # Images
        images = attraction.get("images", [])
        if isinstance(images, list) and images:
            elements.append(Spacer(1, 8))
            elements.extend(self._create_image_grid(images, styles))

        # Ticket information
        ticket_info = attraction.get("ticket_info", [])
        if isinstance(ticket_info, list) and ticket_info:
            elements.extend(self._create_ticket_section(ticket_info, labels, styles))

        # Useful links
        useful_links = attraction.get("useful_links", [])
        if isinstance(useful_links, list) and useful_links:
            elements.extend(self._create_links_section(useful_links, labels, styles))

        elements.append(Spacer(1, 15))
        return elements

    def _create_cost_summary(self, costs_by_currency: Dict[str, float], labels: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> List:
        """Create modern full-width cost summary card with anchor.

        Args:
            costs_by_currency: Dict mapping currency code to total cost
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        elements = []

        if not costs_by_currency:
            return elements

        # Add anchor for TOC navigation
        elements.append(Paragraph('<a name="cost_summary"/>', styles["Body"]))

        # Currency symbols
        currency_symbols = {
            "EUR": "€", "USD": "$", "GBP": "£", "BRL": "R$",
            "JPY": "¥", "CHF": "CHF", "AUD": "A$", "CAD": "C$",
        }

        # Header row
        header_style = ParagraphStyle(
            "CostCardHeader",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=ITINERARY_COLORS["white"],
            leading=18,
        )
        header_para = Paragraph(labels["cost_summary"], header_style)

        # Build cost rows
        cost_rows = []
        for currency, total in sorted(costs_by_currency.items()):
            symbol = currency_symbols.get(currency, currency)
            amount_style = ParagraphStyle(
                "CostAmount",
                fontName="Helvetica-Bold",
                fontSize=16,
                textColor=ITINERARY_COLORS["primary"],
                leading=20,
            )
            currency_style = ParagraphStyle(
                "CostCurrency",
                fontName="Helvetica",
                fontSize=11,
                textColor=ITINERARY_COLORS["light_text"],
                leading=14,
            )
            cost_rows.append([
                Paragraph(f"{symbol} {total:.2f}", amount_style),
                Paragraph(currency, currency_style),
            ])

        # Footer note
        footer_style = ParagraphStyle(
            "CostCardFooter",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=ITINERARY_COLORS["light_text"],
            leading=12,
        )
        footer_para = Paragraph(labels["per_person"], footer_style)

        # Build the full card table
        # Structure: Header row, cost rows, footer row
        table_data = [
            [header_para, ""],  # Header spans full width
        ]
        for row in cost_rows:
            table_data.append(row)
        table_data.append([footer_para, ""])  # Footer spans full width

        # Create the card
        cost_card = RLTable(table_data, colWidths=[self.CONTENT_WIDTH * 0.6, self.CONTENT_WIDTH * 0.4])

        # Calculate row indices
        header_row = 0
        footer_row = len(table_data) - 1

        cost_card.setStyle(RLTableStyle([
            # Header row - primary color background
            ("BACKGROUND", (0, header_row), (-1, header_row), ITINERARY_COLORS["primary"]),
            ("SPAN", (0, header_row), (-1, header_row)),
            ("LEFTPADDING", (0, header_row), (-1, header_row), 15),
            ("TOPPADDING", (0, header_row), (-1, header_row), 12),
            ("BOTTOMPADDING", (0, header_row), (-1, header_row), 12),

            # Cost rows - light background
            ("BACKGROUND", (0, 1), (-1, footer_row - 1), ITINERARY_COLORS["white"]),
            ("LEFTPADDING", (0, 1), (-1, footer_row - 1), 20),
            ("RIGHTPADDING", (0, 1), (-1, footer_row - 1), 20),
            ("TOPPADDING", (0, 1), (-1, footer_row - 1), 12),
            ("BOTTOMPADDING", (0, 1), (-1, footer_row - 1), 12),
            ("ALIGN", (0, 1), (0, footer_row - 1), "LEFT"),
            ("ALIGN", (1, 1), (1, footer_row - 1), "LEFT"),
            ("VALIGN", (0, 1), (-1, footer_row - 1), "MIDDLE"),

            # Footer row - subtle background
            ("BACKGROUND", (0, footer_row), (-1, footer_row), ITINERARY_COLORS["background"]),
            ("SPAN", (0, footer_row), (-1, footer_row)),
            ("LEFTPADDING", (0, footer_row), (-1, footer_row), 15),
            ("TOPPADDING", (0, footer_row), (-1, footer_row), 8),
            ("BOTTOMPADDING", (0, footer_row), (-1, footer_row), 8),

            # Overall card styling
            ("BOX", (0, 0), (-1, -1), 1, ITINERARY_COLORS["light_text"]),
            ("LINEBELOW", (0, header_row), (-1, header_row), 1, ITINERARY_COLORS["light_text"]),
            ("LINEABOVE", (0, footer_row), (-1, footer_row), 0.5, ITINERARY_COLORS["light_text"]),
        ]))

        elements.append(Spacer(1, 20))
        elements.append(cost_card)
        elements.append(Spacer(1, 10))

        return elements

    def _create_map_section(self, map_image_path: str, labels: Dict[str, str], styles: Dict[str, ParagraphStyle]) -> List:
        """Create final map section with proper aspect ratio.

        Args:
            map_image_path: Path to map image file
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        from reportlab.platypus import Image as RLImage, PageBreak as RLPageBreak
        from PIL import Image as PILImage

        elements = []

        if not map_image_path or not os.path.exists(map_image_path):
            LOGGER.warning(f"Map image not found: {map_image_path}")
            return elements

        # Page break before map
        elements.append(RLPageBreak())

        # Add anchor for TOC navigation
        elements.append(Paragraph('<a name="route_map"/>', styles["Body"]))

        # Map header
        elements.append(Paragraph(labels["route_map"], styles["CostHeader"]))
        elements.append(Spacer(1, 15))

        # Map image with proper aspect ratio
        try:
            # Read actual image dimensions
            pil_img = PILImage.open(map_image_path)
            img_width, img_height = pil_img.size
            aspect_ratio = img_width / img_height

            # Calculate size maintaining aspect ratio
            # Max width is content width, max height is 20cm to fit on page
            max_width = self.CONTENT_WIDTH
            max_height = 20*cm

            map_width = max_width
            map_height = map_width / aspect_ratio

            # Cap height if too tall
            if map_height > max_height:
                map_height = max_height
                map_width = map_height * aspect_ratio

            map_img = RLImage(map_image_path, width=map_width, height=map_height)
            map_img.hAlign = 'CENTER'
            elements.append(map_img)

            # Legend
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(labels["map_legend"], styles["Caption"]))
        except Exception as e:
            LOGGER.error(f"Error adding map image: {e}")

        return elements

    def _create_table_of_contents(
        self,
        attractions_by_day: Dict[int, List[Dict[str, Any]]],
        has_costs: bool,
        has_map: bool,
        labels: Dict[str, str],
        styles: Dict[str, ParagraphStyle]
    ) -> List:
        """Create clickable table of contents with left-aligned bullet list.

        Args:
            attractions_by_day: Dict mapping day number to attractions
            has_costs: Whether cost summary section exists
            has_map: Whether map section exists
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        elements = []

        # Section header (left-aligned)
        elements.append(Paragraph(labels["table_of_contents"], styles["SectionHeader"]))
        elements.append(Spacer(1, 8))

        # Simple bullet-style links (left-aligned paragraphs)
        link_color = "#2563EB"  # Blue

        # Day links
        for day_num in sorted(attractions_by_day.keys()):
            link = f'• <a href="#day_{day_num}" color="{link_color}">{labels["day"]} {day_num}</a>'
            elements.append(Paragraph(link, styles["Body"]))

        # Cost summary link
        if has_costs:
            link = f'• <a href="#cost_summary" color="{link_color}">{labels["cost_summary"]}</a>'
            elements.append(Paragraph(link, styles["Body"]))

        # Map link
        if has_map:
            link = f'• <a href="#route_map" color="{link_color}">{labels["route_map"]}</a>'
            elements.append(Paragraph(link, styles["Body"]))

        elements.append(Spacer(1, 20))
        return elements

    def _create_overview_section(
        self,
        attractions_by_day: Dict[int, List[Dict[str, Any]]],
        costs_by_currency: Dict[str, float],
        labels: Dict[str, str],
        styles: Dict[str, ParagraphStyle]
    ) -> List:
        """Create overview summary table showing attraction names per day.

        Args:
            attractions_by_day: Dict mapping day number to attractions
            costs_by_currency: Dict mapping currency to total cost
            labels: Language labels
            styles: Paragraph styles

        Returns:
            List of flowable elements
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        elements = []

        # Section header
        elements.append(Paragraph(labels["overview"], styles["SectionHeader"]))
        elements.append(Spacer(1, 10))

        # Determine primary currency
        primary_currency = "USD"
        if costs_by_currency:
            primary_currency = list(costs_by_currency.keys())[0]

        # Cell styles for table
        header_style = ParagraphStyle(
            "OvHeader",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=ITINERARY_COLORS["white"]
        )
        body_style = ParagraphStyle(
            "OvBody",
            fontName="Helvetica",
            fontSize=10,
            textColor=ITINERARY_COLORS["text"],
            leading=14,  # Better line spacing for wrapped text
        )
        total_style = ParagraphStyle(
            "OvTotal",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=ITINERARY_COLORS["primary"]
        )

        # Build table: Header row (4 columns: Day | # | Attractions | Est. Cost)
        data = [[
            Paragraph(labels["day"], header_style),
            Paragraph(labels["num_attractions"], header_style),
            Paragraph(labels["attractions"], header_style),
            Paragraph(labels["estimated_daily_cost"], header_style),
        ]]

        total_attractions = 0
        total_cost = 0.0

        # Data rows - one per day with attraction names
        for day_num in sorted(attractions_by_day.keys()):
            attractions = attractions_by_day[day_num]
            count = len(attractions)
            day_cost = sum(a.get("estimated_cost", 0) for a in attractions)

            total_attractions += count
            total_cost += day_cost

            # Get attraction names as comma-separated string
            attraction_names = ", ".join(
                self._sanitize_text(a.get("name", labels["unnamed_attraction"]))
                for a in attractions
            )

            data.append([
                Paragraph(f"{labels['day']} {day_num}", body_style),
                Paragraph(str(count), body_style),
                Paragraph(attraction_names, body_style),
                Paragraph(f"{primary_currency} {day_cost:.2f}", body_style),
            ])

        # Total row
        data.append([
            Paragraph(labels["total"], total_style),
            Paragraph(str(total_attractions), total_style),
            Paragraph("", total_style),
            Paragraph(f"{primary_currency} {total_cost:.2f}", total_style),
        ])

        # Create styled table: Day (2.5cm), # (1.5cm), Attractions (8cm), Cost (4cm)
        table = RLTable(data, colWidths=[2.5*cm, 1.5*cm, 8*cm, 4*cm])
        table.setStyle(RLTableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), ITINERARY_COLORS["primary"]),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            # Body with alternating colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -2),
             [ITINERARY_COLORS["white"], ITINERARY_COLORS["background"]]),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            # Total row
            ("BACKGROUND", (0, -1), (-1, -1), ITINERARY_COLORS["background"]),
            ("LINEABOVE", (0, -1), (-1, -1), 1, ITINERARY_COLORS["primary"]),
            # General
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),  # Day column centered
            ("ALIGN", (1, 0), (1, -1), "CENTER"),  # Count column centered
            ("ALIGN", (2, 0), (2, -1), "LEFT"),    # Attractions column left-aligned
            ("ALIGN", (3, 0), (3, -1), "CENTER"),  # Cost column centered
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, ITINERARY_COLORS["light_text"]),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, ITINERARY_COLORS["light_text"]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 25))

        return elements

    def create_document(
        self,
        title: str,
        attractions_by_day: Dict[int, List[Dict[str, Any]]],
        costs_by_currency: Dict[str, float],
        map_image_path: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """Main method to generate the PDF document.

        Args:
            title: Document title
            attractions_by_day: Dict mapping day number to list of attractions
            costs_by_currency: Dict mapping currency code to total cost
            map_image_path: Optional path to route map image
            language: Language code (en, pt-br, es, fr)

        Returns:
            Path to generated PDF file
        """
        LOGGER.info("=== ITINERARY PDF CREATION START ===")
        LOGGER.info(f"Title: {title}")
        LOGGER.info(f"Days: {len(attractions_by_day)}")
        LOGGER.info(f"Language: {language}")

        labels = _get_itinerary_labels(language)
        styles = self._create_styles()

        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title.replace(" ", "_")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        # Create document with 2cm margins for cleaner look
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Build content
        content = []

        # Title
        content.append(Paragraph(title, styles["Title"]))

        # Decorative line
        content.append(HRFlowable(
            width="100%",
            thickness=2,
            color=ITINERARY_COLORS["primary"],
            spaceAfter=20
        ))

        # Table of Contents
        has_costs = bool(costs_by_currency)
        has_map = bool(map_image_path)
        content.extend(self._create_table_of_contents(
            attractions_by_day, has_costs, has_map, labels, styles
        ))

        # Overview Section
        content.extend(self._create_overview_section(
            attractions_by_day, costs_by_currency, labels, styles
        ))

        # Page break before day content
        content.append(PageBreak())

        # Process each day
        for day_num in sorted(attractions_by_day.keys()):
            attractions = attractions_by_day[day_num]

            # Day header
            content.extend(self._create_day_header(day_num, labels, styles))

            # Each attraction
            for attraction in attractions:
                content.extend(self._create_attraction_section(attraction, day_num, labels, styles))

        # Cost summary (new page)
        if costs_by_currency:
            content.append(PageBreak())
            content.extend(self._create_cost_summary(costs_by_currency, labels, styles))

        # Map section
        if map_image_path:
            content.extend(self._create_map_section(map_image_path, labels, styles))

        # Footer
        content.append(Spacer(1, 30))
        content.append(HRFlowable(
            width="100%",
            thickness=1,
            color=ITINERARY_COLORS["light_text"],
            spaceAfter=10
        ))
        generated_text = f"{labels['generated_on']} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        content.append(Paragraph(generated_text, styles["Footer"]))
        content.append(Paragraph(labels["powered_by"], styles["Footer"]))

        # Build PDF
        try:
            doc.build(content)
            LOGGER.info(f"PDF generated successfully: {filepath}")
        except Exception as e:
            LOGGER.error(f"Error building PDF: {e}", exc_info=True)
            return ""
        finally:
            # Cleanup temp files
            self._cleanup_temp_files()

        return filepath
