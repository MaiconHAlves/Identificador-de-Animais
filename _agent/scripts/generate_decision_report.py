from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_decision_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor("#0D47A1"),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#1976D2"),
        alignment=TA_LEFT,
        spaceBefore=15,
        spaceAfter=10
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_RIGHT
    )

    elements = []

    # Header
    elements.append(Paragraph("Documento de Apoio à Decisão Técnica v1.0", header_style))
    elements.append(Spacer(1, 10))

    # Title
    elements.append(Paragraph("Análise de Abordagens: Interface e Hardware", title_style))
    elements.append(Paragraph("Comparativo de Viabilidade para o Projeto Identificador de Animais", styles['Italic']))
    elements.append(Spacer(1, 20))

    # 1. O Desafio Técnico
    elements.append(Paragraph("1. O Desafio Técnico", subtitle_style))
    elements.append(Paragraph(
        "Para atingir o objetivo de prevenir colisões com animais em rodovias, o sistema deve equilibrar "
        "três pilares: Precisão de Detecção (IA), Latência de Resposta e Estabilidade Térmica do Hardware.",
        styles['BodyText']
    ))

    # 2. Comparativo de Abordagens
    elements.append(Paragraph("2. Comparativo de Abordagens de Design", subtitle_style))
    
    comp_data = [
        ["Critério", "Abordagem A: Sobreposição Tática", "Abordagem B: Assistente Minimalista"],
        ["Foco", "Experiência Visual Imersiva", "Segurança Silenciosa / Estabilidade"],
        ["Display", "Câmera Ativa + Overlay Térmico", "Tela em Blackout (Radar)"],
        ["Uso de GPU", "Contínuo (Alta Carga)", "Intermitente (Sob Demanda)"],
        ["Alerta", "Visual + Sonoro Progressivo", "Ícones Grandes + Voz Contextual"],
        ["Impacto Hardware", "Exige Hardware High-End", "Compatível com Hardware Entry-Level"]
    ]
    
    t = Table(comp_data, colWidths=[100, 180, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1976D2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)

    # 3. Requisitos de Hardware
    elements.append(Paragraph("3. Requisitos Mínimos de Hardware", subtitle_style))
    
    hw_data = [
        ["Plataforma", "Requisito Abordagem A", "Requisito Abordagem B"],
        ["Smartphone (V1)", "6GB RAM / Snapdragon 7+", "4GB RAM / Snapdragon 6+"],
        ["Embedded (V2)", "NVIDIA Jetson Orin Nano", "NVIDIA Jetson Nano / Pi 4"],
        ["Sensores", "Térmica + RGB (Alta Res)", "Térmica + RGB (Res. Padrão)"]
    ]
    
    hw_t = Table(hw_data, colWidths=[100, 180, 180])
    hw_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#BBDEFB")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(hw_t)

    # 4. Análise de Viabilidade (Business)
    elements.append(Paragraph("4. Considerações para Tomada de Decisão", subtitle_style))
    elements.append(Paragraph(
        "<b>Opção A (Premium):</b> Ideal para gerar 'Uau' em investidores e vender como acessório de luxo. "
        "Apresenta maior risco de superaquecimento em dispositivos móveis se não houver dissipação ativa.",
        styles['BodyText']
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>Opção B (Segurança):</b> Focada em utilidade pura. Reduz o custo de hardware final e aumenta a vida útil "
        "do dispositivo. É a escolha lógica para frotas comerciais e integração de fábrica.",
        styles['BodyText']
    ))

    # Recomendação
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Recomendação Técnica:</b>", styles['Heading4']))
    elements.append(Paragraph(
        "Iniciar com a <b>Abordagem A</b> no Protótipo Mobile (V1) para validação de marketing e algoritmos, "
        "mas projetar o núcleo do software para suportar o modo <b>Abordagem B</b> como padrão no Produto Industrial (V2).",
        styles['BodyText']
    ))

    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<i>Relatório Estratégico - Antigravity AI Designer</i>", styles['Normal']))

    doc.build(elements)

if __name__ == "__main__":
    generate_decision_pdf("Tomada_de_Decisao_Design_Hardware.pdf")
    print("PDF de Tomada de Decisão gerado com sucesso.")
