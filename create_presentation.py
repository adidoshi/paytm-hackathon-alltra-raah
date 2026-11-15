import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck(filename="Raah_Paytm_Hackathon_Presentation.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Palette
    COLOR_BG = RGBColor(10, 17, 40)        # #0A1128 Deep Navy
    COLOR_CARD = RGBColor(19, 34, 56)      # #132238 Dark Slate Card
    COLOR_CARD_BORDER = RGBColor(30, 58, 95) # #1E3A5F Border
    COLOR_SKY = RGBColor(0, 186, 242)      # #00BAF2 Paytm Sky Blue
    COLOR_CYAN = RGBColor(0, 229, 255)     # #00E5FF Bright Cyan
    COLOR_GREEN = RGBColor(95, 224, 168)   # #5FE0A8 Emerald Green
    COLOR_CORAL = RGBColor(255, 107, 107)  # #FF6B6B Alert Coral/Red
    COLOR_AMBER = RGBColor(255, 184, 0)    # #FFB800 Amber
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_MUTED = RGBColor(148, 163, 184)  # Slate 400
    COLOR_TEXT = RGBColor(203, 213, 225)   # Slate 300

    def add_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, category, title, subtitle=None):
        # Category pill
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf = cat_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category.upper()
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_SKY

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.65))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        # Subtitle
        if subtitle:
            sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(11.7), Inches(0.45))
            tf = sub_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = subtitle
            p.font.size = Pt(13)
            p.font.color.rgb = COLOR_MUTED

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    # ==========================================
    # SLIDE 1: TITLE SLIDE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    add_bg(s1)

    # Accent decorative banner
    banner = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.9), Inches(11.733), Inches(5.7))
    banner.fill.solid()
    banner.fill.fore_color.rgb = RGBColor(14, 26, 48)
    banner.line.color.rgb = COLOR_CARD_BORDER
    banner.line.width = Pt(1.5)

    # Inner decorative badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.3), Inches(1.4), Inches(4.5), Inches(0.4))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(0, 186, 242)
    badge.line.fill.background()
    tf = badge.text_frame
    p = tf.paragraphs[0]
    p.text = "⚡ PAYTM HACKATHON 2026 | FINTECH & AI TRACK"
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = RGBColor(10, 17, 40)
    p.alignment = PP_ALIGN.CENTER

    # Main Brand Title
    t_box = s1.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(11.0), Inches(1.2))
    tf = t_box.text_frame
    p = tf.paragraphs[0]
    p.text = "RAAH (राह)"
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    sub_t_box = s1.shapes.add_textbox(Inches(1.2), Inches(3.1), Inches(11.0), Inches(0.8))
    tf = sub_t_box.text_frame
    p = tf.paragraphs[0]
    p.text = "The Proactive Credit Recovery & Debt Consolidation Agent"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN

    desc_box = s1.shapes.add_textbox(Inches(1.2), Inches(3.9), Inches(10.8), Inches(1.1))
    tf = desc_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Turn rejected retail borrowers into prime customers via 90-day corrective journeys, and proactively consolidate predatory competitor loans (24%-40% APR) into single 14% high-yield Paytm loans with 1-click execution."
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_TEXT

    # 3 Stat pills at bottom of title slide
    p1 = add_card(s1, Inches(1.3), Inches(5.2), Inches(3.3), Inches(1.0), RGBColor(19, 34, 56), COLOR_SKY)
    tf = p1.text_frame
    p = tf.paragraphs[0]
    p.text = "Engine 1: Rejection to Approval"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SKY
    p2 = tf.add_paragraph()
    p2.text = "Explainable AI + 90-day roadmap"
    p2.font.size = Pt(10)
    p2.font.color.rgb = COLOR_MUTED

    p2_card = add_card(s1, Inches(4.9), Inches(5.2), Inches(3.3), Inches(1.0), RGBColor(19, 34, 56), COLOR_GREEN)
    tf = p2_card.text_frame
    p = tf.paragraphs[0]
    p.text = "Engine 2: EMI Detox Agent"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    p2 = tf.add_paragraph()
    p2.text = "Proactive Refinance @ 14% APR"
    p2.font.size = Pt(10)
    p2.font.color.rgb = COLOR_MUTED

    p3_card = add_card(s1, Inches(8.5), Inches(5.2), Inches(3.6), Inches(1.0), RGBColor(19, 34, 56), COLOR_CYAN)
    tf = p3_card.text_frame
    p = tf.paragraphs[0]
    p.text = "Sarvam AI Indic Suite"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN
    p2 = tf.add_paragraph()
    p2.text = "Voice Agent (Hindi, Marathi, English)"
    p2.font.size = Pt(10)
    p2.font.color.rgb = COLOR_MUTED

    # ==========================================
    # SLIDE 2: THE PROBLEM
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_bg(s2)
    add_header(s2, "The Market Crisis", "The Broken Credit Funnel & The Predatory Debt Trap in India", "Why retail borrowers default and why lenders lose billions in high-intent customer acquisition.")

    cards_data = [
        ("78% Opaque Rejection Rate", "The Black Box Rejection", "78% of digital personal loan applicants in India are rejected without actionable reasons. Thin credit files or minor utility late fees trigger silent algorithmic drops.", COLOR_CORAL),
        ("28% to 42% APR Debt Trap", "Predatory BNPL Cycles", "Rejected users churn to instant lending apps and high-interest BNPLs (LazyPay, KreditBee, Ring). High revolving balances quickly spiral into unmanageable debt.", COLOR_AMBER),
        ("Disparate Due Date Chaos", "₹500+ Bounce Penalties", "Borrowers juggle 3-4 loans with random due dates (5th, 12th, 22nd). A single missed payment triggers steep NACH bounce fees and damages CIBIL scores.", COLOR_CORAL),
        ("Wasted Acquisition Cost (CAC)", "Paytm's Lost Revenue", "Paytm spends valuable CAC to bring users to the loan application step. Losing them to competitors permanently destroys ecosystem lifetime value (LTV).", COLOR_SKY),
    ]

    for i, (stat, title, desc, color) in enumerate(cards_data):
        x = Inches(0.8 + (i % 2) * 5.95)
        y = Inches(1.9 + (i // 2) * 2.55)
        add_card(s2, x, y, Inches(5.75), Inches(2.35))
        
        # Pill inside card
        tb = s2.shapes.add_textbox(x + Inches(0.25), y + Inches(0.15), Inches(5.2), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = stat.upper()
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = color

        tb_title = s2.shapes.add_textbox(x + Inches(0.25), y + Inches(0.6), Inches(5.2), Inches(0.4))
        p = tb_title.text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        tb_desc = s2.shapes.add_textbox(x + Inches(0.25), y + Inches(1.05), Inches(5.2), Inches(1.15))
        tf = tb_desc.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(12.5)
        p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 3: THE VISION & VALUE PROPOSITION
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_bg(s3)
    add_header(s3, "Product Vision", "Raah (राह): From Credit Rejection to Financial Freedom", "A complete dual-engine architecture designed specifically for the Paytm Super-App.")

    # 2 big side by side columns
    # Left Column: Engine 1
    add_card(s3, Inches(0.8), Inches(1.9), Inches(5.75), Inches(5.0))
    tb = s3.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.15), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "TAB 1: LOAN REJECTION TO APPROVAL"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SKY

    tb = s3.shapes.add_textbox(Inches(1.1), Inches(2.55), Inches(5.15), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "The 90-Day Credit Recovery Journey"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    e1_points = [
        ("Opaque Rejection Decoded", "Translates bureaucratic bureau codes (THIN_FILE, HIGH_FOIR) into plain Marathi, Hindi, and English."),
        ("Actionable Milestone Plan", "Prescribes FD-backed credit card, UPI utility auto-pay, and 3 on-time repayment cycles."),
        ("Interactive Time Simulation", "Allows users to advance time (30, 60, 90 days) to see their readiness score rise from 0% to 100%."),
        ("Guaranteed Re-Application", "When 90-day criteria are met, user re-applies with guaranteed pre-approved underwriting."),
    ]
    for i, (head, body) in enumerate(e1_points):
        tb_pt = s3.shapes.add_textbox(Inches(1.1), Inches(3.2 + i * 0.85), Inches(5.15), Inches(0.8))
        tf = tb_pt.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"✔ {head}: "
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_SKY
        run = p.add_run()
        run.text = body
        run.font.bold = False
        run.font.color.rgb = COLOR_TEXT

    # Right Column: Engine 2
    add_card(s3, Inches(6.8), Inches(1.9), Inches(5.75), Inches(5.0))
    tb = s3.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.15), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "TAB 2: EMI DETOX AGENT"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN

    tb = s3.shapes.add_textbox(Inches(7.1), Inches(2.55), Inches(5.15), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "Proactive Debt Consolidation Engine"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    e2_points = [
        ("Automated Debt Scanning", "Detects external recurring EMIs & high-APR BNPL mandates across competitor apps via UPI history."),
        ("1-Click 14% Consolidation", "Consolidates multiple fragmented loans into one single Paytm loan at 14% APR, saving ₹3,000+/month."),
        ("Disparate Due Date Fix", "Replaces chaotic billing calendars with a single auto-debit on the 5th of each month."),
        ("Unlisted Loan Support", "Manual input button allows adding unlisted/offline debt with instant mathematical recalculation."),
    ]
    for i, (head, body) in enumerate(e2_points):
        tb_pt = s3.shapes.add_textbox(Inches(7.1), Inches(3.2 + i * 0.85), Inches(5.15), Inches(0.8))
        tf = tb_pt.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"✔ {head}: "
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_GREEN
        run = p.add_run()
        run.text = body
        run.font.bold = False
        run.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 4: THE CORE ARCHITECTURAL PHILOSOPHY
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_bg(s4)
    add_header(s4, "Engineering Integrity", "Strict Division of Labor: Math vs. Generative LLM", "Why fintech compliance demands deterministic math while reserving LLMs for empathy and conversion.")

    # Left: The Math & Rules
    add_card(s4, Inches(0.8), Inches(1.9), Inches(5.75), Inches(5.0))
    tb = s4.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.15), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "DETERMINISTIC CODE (TYPESCRIPT & PYTHON)"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN

    tb = s4.shapes.add_textbox(Inches(1.1), Inches(2.55), Inches(5.15), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "100% Deterministic Math & Policy Rules"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    math_items = [
        ("Reducing Balance EMI Formula", "Exact standard banking formula: EMI = [P x r x (1+r)^n] / [(1+r)^n - 1]. Never estimated."),
        ("Weighted Average APR", "Computed strictly as sum(Principal x APR) / Total Principal. Zero rounding drift."),
        ("Net Cash Savings Calculation", "Exact monthly savings, annual savings, and debt-to-income (DTI) reduction."),
        ("Underwriting Policy Engine", "Approval/rejection rules encoded in YAML thresholds. Strict compliance, no probabilistic variance."),
    ]
    for i, (h, b) in enumerate(math_items):
        tb_pt = s4.shapes.add_textbox(Inches(1.1), Inches(3.2 + i * 0.85), Inches(5.15), Inches(0.8))
        tf = tb_pt.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"⚙ {h}\n"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_CYAN
        run = p.add_run()
        run.text = b
        run.font.bold = False
        run.font.size = Pt(11)
        run.font.color.rgb = COLOR_TEXT

    # Right: The Generative AI
    add_card(s4, Inches(6.8), Inches(1.9), Inches(5.75), Inches(5.0))
    tb = s4.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.15), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "SARVAM-105B INDIC LLM"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER

    tb = s4.shapes.add_textbox(Inches(7.1), Inches(2.55), Inches(5.15), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "The Empathy & Conversion Engine"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    llm_items = [
        ("The Counselor Pitch", "Takes user's behavioral stress (e.g. medical emergency, salary dips) and frames loan consolidation with deep empathy to maximize conversion."),
        ("Dynamic Partner Routing", "Evaluates CIBIL score and DTI to dynamically allocate risk to Tata Capital (Prime), Hero Fincorp (Near-Prime), or In-House NBFC."),
        ("Paytm ROI Justification", "Synthesizes real-time unit economics (14% yield spread, zero CAC, ecosystem lock-in) for credit committee auditing."),
        ("Multi-Lingual Explanation", "Delivers seamless, culturally grounded vernacular explanations in Hindi, Marathi, and English."),
    ]
    for i, (h, b) in enumerate(llm_items):
        tb_pt = s4.shapes.add_textbox(Inches(7.1), Inches(3.2 + i * 0.85), Inches(5.15), Inches(0.8))
        tf = tb_pt.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"🧠 {h}\n"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_AMBER
        run = p.add_run()
        run.text = b
        run.font.bold = False
        run.font.size = Pt(11)
        run.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 5: TAB 1 DEEP DIVE (LOAN RECOVERY)
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_bg(s5)
    add_header(s5, "Tab 1 Architecture", "Loan Rejection to Approval: The 90-Day Guided Plan", "How Raah bridges the thin-file credit gap with measurable everyday actions.")

    # 3 horizontal process cards
    steps = [
        ("Stage 1: Transparent Diagnosis", "Day 0: Rejection Decoded", "• User applies for ₹1,00,000 Personal Loan.\n• Lender returns reference LN-RAVI-100K.\n• Bureau code THIN_FILE intercepted.\n• Raah explains: 'Lender needs 3 on-time payment cycles before approving unsecured credit.'", COLOR_CORAL),
        ("Stage 2: Corrective Plan Activated", "Days 1-90: Guided Action Steps", "• Action 1: Open ₹10,000 Fixed Deposit backed Credit Card (₹9,000 limit).\n• Action 2: Put MSEDCL electricity bill on UPI AutoPay.\n• Action 3: Complete 3 on-time monthly billing cycles reported to CIBIL.", COLOR_AMBER),
        ("Stage 3: Guaranteed Approval", "Day 90: Re-Application Success", "• User clicks 'Advance 30 Days' to simulate time.\n• Readiness metric advances: 0% → 33% → 66% → 100%.\n• System grants explicit consent.\n• Re-apply succeeds with 100% guaranteed approval!", COLOR_GREEN),
    ]

    for i, (step_num, title, body, col) in enumerate(steps):
        x = Inches(0.8 + i * 3.95)
        add_card(s5, x, Inches(1.9), Inches(3.8), Inches(5.0))
        
        tb = s5.shapes.add_textbox(x + Inches(0.2), Inches(2.1), Inches(3.4), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = step_num.upper()
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = col

        tb = s5.shapes.add_textbox(x + Inches(0.2), Inches(2.55), Inches(3.4), Inches(0.6))
        p = tb.text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        tb = s5.shapes.add_textbox(x + Inches(0.2), Inches(3.2), Inches(3.4), Inches(3.4))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = body
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 6: TAB 2 DEEP DIVE (EMI DETOX AGENT)
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    add_bg(s6)
    add_header(s6, "Tab 2 Architecture", "EMI Detox Agent: Proactive High-APR Consolidation", "Comparative Split-Screen: Transforming fragmented chaos into a unified Paytm solution.")

    # Before Box (Red/Chaos)
    add_card(s6, Inches(0.8), Inches(1.9), Inches(5.75), Inches(5.0), RGBColor(28, 16, 26), COLOR_CORAL)
    tb = s6.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.15), Inches(0.35))
    p = tb.text_frame.paragraphs[0]
    p.text = "BEFORE: THE FRAGMENTED CHAOS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_CORAL

    tb = s6.shapes.add_textbox(Inches(1.1), Inches(2.5), Inches(5.15), Inches(0.45))
    p = tb.text_frame.paragraphs[0]
    p.text = "3 High-Interest Predatory Loans"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    chaos_stats = [
        ("LazyPay BNPL", "₹25,000 balance @ 24% APR | Due 5th"),
        ("KreditBee Instant Loan", "₹35,000 balance @ 30% APR | Due 12th"),
        ("HDFC Credit Card Revolver", "₹75,000 balance @ 38% APR | Due 22nd"),
        ("Total Monthly Burden", "₹15,400 / month across 3 dates"),
        ("Average APR", "32.8% Weighted APR (Predatory)"),
        ("NACH Bounce Risk", "₹500 per bounce fee on 3 dates"),
    ]
    for i, (k, v) in enumerate(chaos_stats):
        tb_pt = s6.shapes.add_textbox(Inches(1.1), Inches(3.05 + i * 0.6), Inches(5.15), Inches(0.55))
        tf = tb_pt.text_frame
        p = tf.paragraphs[0]
        p.text = f"❌ {k}: "
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_CORAL
        run = p.add_run()
        run.text = v
        run.font.bold = False
        run.font.color.rgb = COLOR_TEXT

    # After Box (Green/Sky)
    add_card(s6, Inches(6.8), Inches(1.9), Inches(5.75), Inches(5.0), RGBColor(14, 30, 44), COLOR_GREEN)
    tb = s6.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.15), Inches(0.35))
    p = tb.text_frame.paragraphs[0]
    p.text = "AFTER: THE PAYTM SOLUTION"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN

    tb = s6.shapes.add_textbox(Inches(7.1), Inches(2.5), Inches(5.15), Inches(0.45))
    p = tb.text_frame.paragraphs[0]
    p.text = "1 Single Paytm Consolidation Loan"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    sol_stats = [
        ("Consolidated Principal", "₹1,35,000 disbursed directly to clear all 3 loans"),
        ("Paytm Partner APR", "14.0% APR Flat (Saves 18.8% in interest spread!)"),
        ("New Single Monthly EMI", "₹12,120 / month (12 months tenure)"),
        ("Net Monthly Cash Savings", "Save ₹3,280 / month! (₹39,360 / year)"),
        ("Single Due Date", "5th of month via frictionless Paytm UPI AutoPay"),
        ("Credit Score Boost", "Closing 3 unsecured lines projects +48 CIBIL boost"),
    ]
    for i, (k, v) in enumerate(sol_stats):
        tb_pt = s6.shapes.add_textbox(Inches(7.1), Inches(3.05 + i * 0.6), Inches(5.15), Inches(0.55))
        tf = tb_pt.text_frame
        p = tf.paragraphs[0]
        p.text = f"✔ {k}: "
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_GREEN
        run = p.add_run()
        run.text = v
        run.font.bold = False
        run.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 7: MANUAL UNLISTED LOAN FEATURE
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    add_bg(s7)
    add_header(s7, "Feature Innovation", "Manual Unlisted Loan Tracking & Dynamic Re-calculation", "Empowering users to consolidate informal, offline, and un-mandated loans.")

    # 3 Column Layout
    col_w = Inches(3.8)
    # Card 1: The Problem
    add_card(s7, Inches(0.8), Inches(1.9), col_w, Inches(5.0))
    tb = s7.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(3.4), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "THE PROBLEM"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_CORAL
    tb = s7.shapes.add_textbox(Inches(1.0), Inches(2.55), Inches(3.4), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "Off-Bureau Blindspots"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    tb_desc = s7.shapes.add_textbox(Inches(1.0), Inches(3.15), Inches(3.4), Inches(3.4))
    tf = tb_desc.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Account aggregators frequently miss newly issued loans, fintech instant loans without registered mandates, credit card balances, or local store credit. Without manual input, consolidation calculations remain incomplete."
    p.font.size = Pt(12.5)
    p.font.color.rgb = COLOR_TEXT

    # Card 2: The Solution
    add_card(s7, Inches(4.75), Inches(1.9), col_w, Inches(5.0))
    tb = s7.shapes.add_textbox(Inches(4.95), Inches(2.1), Inches(3.4), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "THE SOLUTION"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SKY
    tb = s7.shapes.add_textbox(Inches(4.95), Inches(2.55), Inches(3.4), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "+ Add Unlisted Loan Modal"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    tb_desc = s7.shapes.add_textbox(Inches(4.95), Inches(3.15), Inches(3.4), Inches(3.4))
    tf = tb_desc.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Provides a clean, in-theme modal to input:\n• Lender / App Name (e.g. Navi)\n• Loan Account / Card Reference\n• Category (Instant Loan, BNPL, CC)\n• Outstanding Principal & Monthly EMI\n• Interest Rate APR (5%-60%)\n• Due Day of Month & Penalty terms"
    p.font.size = Pt(12)
    p.font.color.rgb = COLOR_TEXT

    # Card 3: The Reactivity
    add_card(s7, Inches(8.7), Inches(1.9), col_w, Inches(5.0))
    tb = s7.shapes.add_textbox(Inches(8.9), Inches(2.1), Inches(3.4), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "INSTANT REACTIVITY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    tb = s7.shapes.add_textbox(Inches(8.9), Inches(2.55), Inches(3.4), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "Live Math & LLM Update"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    tb_desc = s7.shapes.add_textbox(Inches(8.9), Inches(3.15), Inches(3.4), Inches(3.4))
    tf = tb_desc.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Submitting immediately:\n• Appends with 'Unlisted' badge.\n• Recalculates total debt & weighted APR.\n• Recomputes Paytm 14% consolidated EMI.\n• Triggers Sarvam Indic LLM to regenerate Counselor Pitch and partner routing for the updated debt profile!"
    p.font.size = Pt(12)
    p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 8: VOICE AGENT & MULTILINGUAL AI
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    add_bg(s8)
    add_header(s8, "Multilingual & Voice", "Built for Bharat: Sarvam Indic Voice & Language Stack", "Natural voice conversations in Hindi, Marathi, and English to democratize credit access.")

    v_cards = [
        ("Sarvam Saaras v4 (STT)", "Speech-to-Text for Bharat", "Transcribes natural spoken speech in real-time, handling mixed Hinglish, Marathi, and vernacular regional accents with high domain accuracy.", COLOR_SKY),
        ("Sarvam Bulbul v4-flash (TTS)", "Banking-Grade Voice", "Delivers responsive, natural voice synthesis using tuned speakers ('shubh_enhi_banking', 'nilesh_mr_conversation') for reassuring conversational guidance.", COLOR_CYAN),
        ("Sarvam FastMCP Tools", "Dynamic Language Routing", "Integrates Model Context Protocol (MCP) tools for automatic language identification and on-the-fly cross-dialect translation.", COLOR_GREEN),
        ("Web Audio Resilience", "Zero Silent Failures", "Captures audio via MediaRecorder chunk assembly on recorder.onstop, verifying byte size before payload transmission with Secure Context validation.", COLOR_AMBER),
    ]
    for i, (head, sub, body, col) in enumerate(v_cards):
        x = Inches(0.8 + (i % 2) * 5.95)
        y = Inches(1.9 + (i // 2) * 2.55)
        add_card(s8, x, y, Inches(5.75), Inches(2.35))
        
        tb = s8.shapes.add_textbox(x + Inches(0.25), y + Inches(0.15), Inches(5.2), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = head.upper()
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = col

        tb_title = s8.shapes.add_textbox(x + Inches(0.25), y + Inches(0.6), Inches(5.2), Inches(0.4))
        p = tb_title.text_frame.paragraphs[0]
        p.text = sub
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        tb_desc = s8.shapes.add_textbox(x + Inches(0.25), y + Inches(1.05), Inches(5.2), Inches(1.15))
        tf = tb_desc.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = body
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 9: FULL-STACK TECHNICAL ARCHITECTURE
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    add_bg(s9)
    add_header(s9, "System Architecture", "End-to-End Modern Engineering Architecture", "High performance Next.js 15 App Router + FastAPI Python 3.12 microservices.")

    # 4 horizontal tiers
    tiers = [
        ("Frontend Tier", "Next.js 15 (App Router), React 19, Tailwind CSS v4, Framer Motion physics, Lucide icons, Web Audio API capture.", COLOR_SKY),
        ("API & Gateway Tier", "FastAPI (Python 3.12), Starlette dual-origin CORS & IPv4/IPv6 resilience, RESTful JSON contracts, Uvicorn ASGI server.", COLOR_CYAN),
        ("Rules & Math Tier", "Deterministic YAML underwriting policies (thresholds.yaml, products.yaml), Reducing balance mathematical engine.", COLOR_GREEN),
        ("AI & Intelligence Tier", "Sarvam-105B Indic LLM (Sarvam AI), LangGraph multi-agent pipeline, Gemini 3.1 Flash-Lite fallback, SQLite audit persistence.", COLOR_AMBER),
    ]

    for i, (title, desc, col) in enumerate(tiers):
        y = Inches(1.9 + i * 1.28)
        add_card(s9, Inches(0.8), y, Inches(11.733), Inches(1.15))
        
        tb = s9.shapes.add_textbox(Inches(1.1), y + Inches(0.15), Inches(3.2), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = title.upper()
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = col

        tb_desc = s9.shapes.add_textbox(Inches(4.3), y + Inches(0.15), Inches(8.0), Inches(0.85))
        tf = tb_desc.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 10: PAYTM BUSINESS VALUE & UNIT ECONOMICS
    # ==========================================
    s10 = prs.slides.add_slide(blank_layout)
    add_bg(s10)
    add_header(s10, "Business ROI", "Paytm Unit Economics: Zero CAC & High-Yield Retention", "Why proactive debt consolidation is immensely profitable for Paytm's balance sheet.")

    biz_cards = [
        ("Zero CAC Acquisition", "Monetizing Existing Traffic", "Refinances competitor loans for users already active inside Paytm's payment ecosystem, bypassing Google/Meta digital ad costs.", COLOR_GREEN),
        ("14% High-Yield Spread", "Co-Lending Balance Sheet Yield", "Earns healthy net interest margin (NIM) for Paytm's NBFC and institutional co-lenders (Tata Capital, Hero Fincorp) with secured AutoPay.", COLOR_SKY),
        ("Drastic Default Reduction", "Lowering NPL Rates", "Dropping user debt-to-income (DTI) from 55%+ down to under 25% prevents impending defaults and protects loan portfolio quality.", COLOR_CYAN),
        ("Ecosystem Lock-In", "Primary Financial Super-App", "Locks in salary deposits, bill payments, and UPI transactions into Paytm, making Paytm the user's primary lifetime financial hub.", COLOR_AMBER),
    ]

    for i, (head, sub, body, col) in enumerate(biz_cards):
        x = Inches(0.8 + (i % 2) * 5.95)
        y = Inches(1.9 + (i // 2) * 2.55)
        add_card(s10, x, y, Inches(5.75), Inches(2.35))
        
        tb = s10.shapes.add_textbox(x + Inches(0.25), y + Inches(0.15), Inches(5.2), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = head.upper()
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = col

        tb_title = s10.shapes.add_textbox(x + Inches(0.25), y + Inches(0.6), Inches(5.2), Inches(0.4))
        p = tb_title.text_frame.paragraphs[0]
        p.text = sub
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        tb_desc = s10.shapes.add_textbox(x + Inches(0.25), y + Inches(1.05), Inches(5.2), Inches(1.15))
        tf = tb_desc.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = body
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 11: COMPLIANCE & DATA GOVERNANCE
    # ==========================================
    s11 = prs.slides.add_slide(blank_layout)
    add_bg(s11)
    add_header(s11, "Regulatory Compliance", "RBI Digital Lending Guidelines (DLG) & Data Governance", "Built ground-up with auditable transparency, explicit consent, and security.")

    reg_cards = [
        ("RBI DLG Compliance", "Key Fact Statement (KFS)", "Full transparency in Annual Percentage Rate (APR), processing fees, and interest computation. No predatory hidden penal charges.", COLOR_GREEN),
        ("Explicit User Consent", "Audit-Logged Permissions", "Every loan re-application and data scan requires cryptographically verifiable opt-in consent recorded in SQLite audit logs.", COLOR_SKY),
        ("Immutable Audit Trail", "Tamper-Proof Trace Log", "Every rule execution, lender client response, LLM generation, and user event is stored in an immutable event trace for regulatory inspection.", COLOR_CYAN),
        ("1-Click Direct Settlement", "Zero Fund Diversion", "Disbursement occurs directly to competitor loan accounts (closing the loans at source), ensuring zero leakage or fund diversion.", COLOR_AMBER),
    ]

    for i, (head, sub, body, col) in enumerate(reg_cards):
        x = Inches(0.8 + (i % 2) * 5.95)
        y = Inches(1.9 + (i // 2) * 2.55)
        add_card(s11, x, y, Inches(5.75), Inches(2.35))
        
        tb = s11.shapes.add_textbox(x + Inches(0.25), y + Inches(0.15), Inches(5.2), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = head.upper()
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = col

        tb_title = s11.shapes.add_textbox(x + Inches(0.25), y + Inches(0.6), Inches(5.2), Inches(0.4))
        p = tb_title.text_frame.paragraphs[0]
        p.text = sub
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        tb_desc = s11.shapes.add_textbox(x + Inches(0.25), y + Inches(1.05), Inches(5.2), Inches(1.15))
        tf = tb_desc.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = body
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT

    # ==========================================
    # SLIDE 12: DEMO FLOW & SUMMARY
    # ==========================================
    s12 = prs.slides.add_slide(blank_layout)
    add_bg(s12)
    add_header(s12, "Summary & Live Demo", "Live Demonstration Journey for Paytm Hackathon Judges", "Three quick, high-impact demo steps proving end-to-end functionality.")

    demo_steps = [
        ("Step 1: Loan Rejection Recovery", "Tab 1: Ravi Jadhav", "1. Open Tab 1: Loan Rejection to Approval.\n2. Observe transparent diagnosis of 'THIN_FILE' in Marathi/Hindi/English.\n3. Advance simulation by 90 days.\n4. Watch readiness score reach 100% and witness guaranteed loan approval!"),
        ("Step 2: Proactive Debt Consolidation", "Tab 2: EMI Detox Agent", "1. Switch to Tab 2: EMI Detox Agent.\n2. Review Priya's 3 high-APR loans.\n3. Click '+ Add Unlisted Loan' to add Navi loan (₹35k @ 36%).\n4. Watch math instantly recompute ₹3,280/mo savings and Sarvam AI re-pitch!"),
        ("Step 3: Voice Agent in Vernacular", "Ask Raah Voice Assistant", "1. Click the microphone button on the dashboard.\n2. Speak in Hindi or English: 'How can I lower my loan EMI?'.\n3. Experience real-time Sarvam Saaras STT & Bulbul TTS answering with empathy!"),
    ]

    for i, (step_num, title, body) in enumerate(demo_steps):
        x = Inches(0.8 + i * 3.95)
        add_card(s12, x, Inches(1.9), Inches(3.8), Inches(4.3))
        
        tb = s12.shapes.add_textbox(x + Inches(0.2), Inches(2.1), Inches(3.4), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = step_num.upper()
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_SKY

        tb = s12.shapes.add_textbox(x + Inches(0.2), Inches(2.55), Inches(3.4), Inches(0.5))
        p = tb.text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

        tb = s12.shapes.add_textbox(x + Inches(0.2), Inches(3.15), Inches(3.4), Inches(2.8))
        tf = tb_desc = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = body
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT

    # Bottom summary bar
    bar = add_card(s12, Inches(0.8), Inches(6.35), Inches(11.733), Inches(0.65), RGBColor(0, 186, 242))
    tf = bar.text_frame
    p = tf.paragraphs[0]
    p.text = "🌟 RAAH: Turning Credit Rejection into Financial Freedom and Loyal Paytm Customers."
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(10, 17, 40)
    p.alignment = PP_ALIGN.CENTER

    prs.save(filename)
    print(f"Successfully generated {filename} with {len(prs.slides)} slides!")

if __name__ == "__main__":
    create_deck("Raah_Paytm_Hackathon_Presentation.pptx")
