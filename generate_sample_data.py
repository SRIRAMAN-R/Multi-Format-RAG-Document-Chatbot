"""
Sample Acme Retail Data Generator
---------------------------------
Generates realistic demonstration files (Excel, CSV, PowerPoint) for the Acme Retail business scenario.
Files generated:
 1. sample_data/acme_sales_q1.xlsx (Multi-sheet Excel workbook with Regional Sales & Product Performance)
 2. sample_data/acme_customers.csv (CSV dataset with enterprise customer accounts & contract statuses)
 3. sample_data/acme_q1_business_review.pptx (PowerPoint presentation with Q1 executive slides & bullet points)
"""

import os
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from config import SAMPLE_DATA_DIR
from src.utils.logger import logger

def generate_excel_data() -> str:
    """Generates sample multi-sheet Excel file 'acme_sales_q1.xlsx'."""
    excel_path = SAMPLE_DATA_DIR / "acme_sales_q1.xlsx"

    # Sheet 1: Regional Sales Targets and Achievements
    regional_sales_data = {
        "Region": ["South", "North", "East", "West", "Central"],
        "Regional_Head": ["Sarah Jenkins", "Michael Chang", "Elena Rostova", "David Miller", "Priya Patel"],
        "Q1_Target_USD": [4000000, 5000000, 3500000, 4500000, 3000000],
        "Q1_Actual_Revenue_USD": [4200000, 4800000, 3700000, 4600000, 2900000],
        "Target_Achievement_Pct": ["105.0%", "96.0%", "105.7%", "102.2%", "96.7%"],
        "Top_Growth_Category": ["Electronics", "Software Solutions", "Retail Hardware", "Enterprise SaaS", "Consumer Goods"]
    }

    # Sheet 2: Product Performance Metrics
    product_data = {
        "Product_SKU": ["ACME-101", "ACME-202", "ACME-303", "ACME-404", "ACME-505"],
        "Product_Name": ["Smart POS Terminal X1", "Retail ERP SaaS Pro", "Omnichannel Barcode Scanner", "Inventory AI Predictor", "Self-Checkout Kiosk 2.0"],
        "Category": ["Hardware", "Software", "Hardware", "Software", "Hardware"],
        "Unit_Price_USD": [1200, 5000, 350, 8500, 4200],
        "Units_Sold_Q1": [1250, 320, 2800, 140, 410],
        "Gross_Margin_Pct": ["28.5%", "82.0%", "22.0%", "88.0%", "34.0%"]
    }

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame(regional_sales_data).to_excel(writer, sheet_name="Regional Sales", index=False)
        pd.DataFrame(product_data).to_excel(writer, sheet_name="Product Performance", index=False)

    logger.info(f"Generated sample Excel file: {excel_path}")
    return str(excel_path)

def generate_csv_data() -> str:
    """Generates sample CSV file 'acme_customers.csv'."""
    csv_path = SAMPLE_DATA_DIR / "acme_customers.csv"

    customer_data = {
        "Customer_ID": ["CUST-001", "CUST-002", "CUST-003", "CUST-004", "CUST-005", "CUST-006"],
        "Account_Name": ["Apex Retail Group", "Metro Supermarket Chain", "Horizon Logistics", "Beacon Department Stores", "Starlight Mart", "Pinnacle Commerce"],
        "Region": ["South", "North", "West", "East", "Central", "South"],
        "Account_Manager": ["Sarah Jenkins", "Michael Chang", "David Miller", "Elena Rostova", "Priya Patel", "Sarah Jenkins"],
        "Annual_Contract_Value_USD": [250000, 420000, 180000, 310000, 95000, 540000],
        "Contract_Status": ["Active", "Active", "Pending Renewal", "Active", "Under Review", "Active"],
        "CSAT_Score": [4.8, 4.5, 4.2, 4.9, 3.8, 4.9]
    }

    df = pd.DataFrame(customer_data)
    df.to_csv(csv_path, index=False)
    logger.info(f"Generated sample CSV file: {csv_path}")
    return str(csv_path)

def generate_pptx_data() -> str:
    """Generates sample PowerPoint file 'acme_q1_business_review.pptx'."""
    pptx_path = SAMPLE_DATA_DIR / "acme_q1_business_review.pptx"

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    # Slide 1: Title Slide
    slide1 = prs.slides.add_slide(blank_slide_layout)
    txBox = slide1.shapes.add_textbox(Inches(1), Inches(2), Inches(11.3), Inches(3))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "Acme Retail - Q1 Business Review & Performance Report"
    p.font.size = Pt(36)
    p.font.bold = True
    p2 = tf.add_paragraph()
    p2.text = "Executive Briefing for Board of Directors | Q1 Operational Review"
    p2.font.size = Pt(20)

    # Slide 2: Regional Performance Summary Slide
    slide2 = prs.slides.add_slide(blank_slide_layout)
    txBox2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(11.3), Inches(5.5))
    tf2 = txBox2.text_frame
    p = tf2.paragraphs[0]
    p.text = "Q1 Regional Performance Highlights"
    p.font.size = Pt(28)
    p.font.bold = True

    bullets = [
        "Executive Summary: Acme Retail reached $20.2M total revenue in Q1, surpassing overall targets by 2.4%.",
        "Top Performer: The South region achieved 105% of its Q1 target, generating $4.2M in total revenue against a $4.0M target.",
        "Software SaaS Growth: Retail ERP SaaS Pro achieved an outstanding 82% gross margin, contributing significantly to profitability.",
        "Key Challenges: North region faced supply chain delays, reaching 96.0% of target ($4.8M revenue vs $5.0M target).",
        "Retention Rate: Customer renewal rate reached 92% across all enterprise tier accounts."
    ]
    for b in bullets:
        p_b = tf2.add_paragraph()
        p_b.text = f"• {b}"
        p_b.font.size = Pt(18)

    # Slide 3: Strategic Priorities Slide
    slide3 = prs.slides.add_slide(blank_slide_layout)
    txBox3 = slide3.shapes.add_textbox(Inches(1), Inches(1), Inches(11.3), Inches(5.5))
    tf3 = txBox3.text_frame
    p = tf3.paragraphs[0]
    p.text = "Q2 Strategic Growth Priorities"
    p.font.size = Pt(28)
    p.font.bold = True

    priorities = [
        "Expand Smart POS Kiosk installations in East and West regions.",
        "Accelerate Retail ERP SaaS upsell to mid-market retail partners.",
        "Target account renewal improvement in Central region with dedicated Customer Success Management.",
        "Achieve $22.5M projected Q2 total revenue target across all 5 operational regions."
    ]
    for pri in priorities:
        p_p = tf3.add_paragraph()
        p_p.text = f"1. {pri}"
        p_p.font.size = Pt(18)

    prs.save(pptx_path)
    logger.info(f"Generated sample PPTX file: {pptx_path}")
    return str(pptx_path)

def generate_all_samples():
    """Generates all Acme Retail sample files."""
    print("Generating Acme Retail sample datasets...")
    f1 = generate_excel_data()
    f2 = generate_csv_data()
    f3 = generate_pptx_data()
    print("All sample files generated successfully in 'sample_data/':")
    print(f" - {f1}")
    print(f" - {f2}")
    print(f" - {f3}")

if __name__ == "__main__":
    generate_all_samples()
