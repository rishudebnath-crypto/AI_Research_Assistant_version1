from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch

import os
from schemas import PaperSummary

def add_section(
    story: list,
    heading: str,
    content: str,
    heading_style,
    body_style
) -> None:

    if not content:
        content = "Not available."

    story.append(
        Paragraph(
            heading,
            heading_style
        )
    )

    story.append(
        Paragraph(
            content,
            body_style
        )
    )

    story.append(
        Spacer(
            1,
            0.25 * inch
        )
    )




def generate_summary_pdf(summary: PaperSummary, document_id: int, summary_length: str) -> str:

    os.makedirs(
        os.path.join('data', 'generated_reports'), 
        exist_ok=True
    )

    pdf_path = os.path.join(
        'data',
        'generated_reports',
        f'summary_{document_id}_{summary_length}.pdf'
    )

    doc = SimpleDocTemplate(
        pdf_path,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    heading_style = styles["Heading2"]

    body_style = styles["BodyText"]

    story = []

    story.append(
    Paragraph(
        "AI Research Assistant",
        title_style
    )
    )

    story.append(
    Spacer(
        1,
        0.4 * inch
    )
    )

    story.append(
    Paragraph(
        "Research Paper Summary Report",
        heading_style
    )
    )

    story.append(
        Spacer(
            1,
            0.35 * inch
        )
    )

    add_section(
        story,
        "Paper Title",
        summary.title,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Paper Overview",
        summary.paper_overview,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Research Problem",
        summary.research_problem,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Motivation",
        summary.motivation,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Methodology",
        summary.methodology,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Experimental Setup",
        summary.experimental_setup,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Key Results",
        summary.key_results,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Conclusion",
        summary.conclusion,
        heading_style,
        body_style
    )

    add_section(
        story,
        "Future Improvement",
        summary.future_improvement,
        heading_style,
        body_style
    )

    doc.build(story)

    return pdf_path


