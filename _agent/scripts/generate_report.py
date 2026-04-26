from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#1A237E"),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor("#303F9F"),
        alignment=TA_LEFT,
        spaceBefore=20,
        spaceAfter=10
    )
    
    body_style = styles['BodyText']
    body_style.fontSize = 11
    body_style.leading = 14

    elements = []

    # Title
    elements.append(Paragraph("Resumo Executivo: Identificador de Animais", title_style))
    elements.append(Paragraph("Sistema de Segurança Ativa e Prevenção de Colisões Rodoviárias", styles['Italic']))
    elements.append(Spacer(1, 20))

    # 1. Visão Geral
    elements.append(Paragraph("1. Visão Geral do Projeto", subtitle_style))
    elements.append(Paragraph(
        "O projeto consiste no desenvolvimento de um dispositivo inteligente, embarcado em veículos, "
        "capaz de detectar e identificar animais em pistas de rolagem em tempo real, alertando o condutor "
        "para evitar acidentes críticos.",
        body_style
    ))

    # 2. Diferenciais Técnicos
    elements.append(Paragraph("2. Diferenciais Técnicos e Inovação", subtitle_style))
    tech_data = [
        ["Tecnologia", "Descrição", "Benefício"],
        ["Fusão de Sensores", "Câmera Térmica + RGB", "Operação 24/7 (Noite/Neblina)"],
        ["Edge Computing", "Processamento Local", "Baixa latência (Segurança Real)"],
        ["IA YOLOv8", "Motor de Detecção", "Alta precisão e velocidade"],
        ["Portabilidade", "Stack em Python", "Fácil migração Smartphone -> Jetson"]
    ]
    t = Table(tech_data, colWidths=[100, 200, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#303F9F")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)

    # 3. Estratégia de Lançamento (Roadmap)
    elements.append(Paragraph("3. Roadmap de Desenvolvimento", subtitle_style))
    elements.append(Paragraph("<b>Fase 1 (MVP Mobile):</b> Implementação em Smartphone via USB/OTG com sensor térmico. Foco em validação de software e interface.", body_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<b>Fase 2 (Industrial):</b> Migração para hardware dedicado (NVIDIA Jetson / Raspberry Pi 5). Foco em robustez e integração veicular.", body_style))

    # 4. Interface e Experiência do Usuário (UX)
    elements.append(Paragraph("4. Interface e Alertas", subtitle_style))
    elements.append(Paragraph(
        "O sistema utilizará um modelo híbrido de interação para garantir que o motorista seja "
        "notificado sem ser distraído:",
        body_style
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("- <b>Aviso Sonoro:</b> Beeps progressivos baseados na proximidade e risco.", body_style))
    elements.append(Paragraph("- <b>Interface Visual:</b> Bounding boxes coloridas e sobreposição térmica (Overlay).", body_style))

    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<i>Relatório gerado automaticamente pelo Time NEXO - Antigravity AI</i>", styles['Normal']))

    doc.build(elements)

if __name__ == "__main__":
    generate_pdf("Resumo_Executivo_Identificador_Animais.pdf")
    print("PDF gerado com sucesso.")
