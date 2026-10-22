import os
from PIL import Image, ImageDraw

def draw_national_id(output_path, title="کارت هوشمند ملی", nat_id="0012345678", name="علیرضا رضایی پور"):
    img = Image.new('RGB', (856, 540), color='#f0f9ff')
    d = ImageDraw.Draw(img)

    # Outer border
    d.rounded_rectangle([15, 15, 841, 525], radius=24, outline='#0284c7', width=3)
    
    # Iran Flag Top Stripe
    d.rectangle([18, 18, 838, 38], fill='#16a34a')
    d.rectangle([18, 38, 838, 58], fill='#ffffff')
    d.rectangle([18, 58, 838, 78], fill='#dc2626')

    # Card Header
    d.rectangle([18, 78, 838, 128], fill='#e0f2fe')
    d.text((428, 95), "ISLAMIC REPUBLIC OF IRAN - NATIONAL SMART CARD", fill='#0f2744', anchor="mm")
    
    # Gold Smart Chip
    d.rounded_rectangle([60, 160, 160, 240], radius=8, fill='#facc15', outline='#ca8a04', width=2)
    d.rectangle([65, 195, 155, 205], fill='#ca8a04')
    d.rectangle([105, 165, 115, 235], fill='#ca8a04')

    # Photo Box
    d.rounded_rectangle([680, 150, 810, 310], radius=8, fill='#e2e8f0', outline='#94a3b8', width=2)
    # Silhouette Head
    d.ellipse([725, 175, 765, 225], fill='#64748b')
    d.ellipse([705, 235, 785, 305], fill='#64748b')

    # Information Lines
    d.text((640, 170), f"Name: {name}", fill='#0f172a', anchor="ra")
    d.text((640, 220), f"National ID: {nat_id}", fill='#1e3a8a', anchor="ra")
    d.text((640, 270), "Birth Date: 1365/04/18", fill='#334155', anchor="ra")
    d.text((640, 320), "Card Serial: 9845012389", fill='#475569', anchor="ra")

    # Barcode representation
    for i in range(40):
        x = 60 + i * 18
        w = 3 if i % 2 == 0 else 6
        d.rectangle([x, 370, x + w, 440], fill='#0f172a')
    
    d.text((428, 460), f"<{nat_id}<<<<9845012389<<<<<<IRN<<<<<<", fill='#475569', anchor="mm")

    # Official Seal watermark
    d.ellipse([340, 210, 480, 350], outline='#38bdf8', width=2)
    d.text((410, 280), "OFFICIAL SEAL", fill='#38bdf8', anchor="mm")

    img.save(output_path, 'JPEG', quality=95)
    print(f"Generated National ID: {output_path}")


def draw_bank_booklet(output_path, nat_id="0012345678"):
    img = Image.new('RGB', (856, 540), color='#ffffff')
    d = ImageDraw.Draw(img)

    # Border
    d.rounded_rectangle([15, 15, 841, 525], radius=16, outline='#ea580c', width=3)
    
    # Header Banner
    d.rectangle([18, 18, 838, 110], fill='#ffedd5')
    d.rectangle([18, 18, 838, 30], fill='#ea580c')
    d.text((428, 70), "BANK MASKAN - NATIONAL HOUSING INSTALLMENT BOOKLET", fill='#9a3412', anchor="mm")

    # Details Box
    d.rounded_rectangle([50, 130, 806, 230], radius=8, fill='#fff7ed', outline='#fed7aa', width=1)
    d.text((70, 155), f"Applicant National ID: {nat_id}", fill='#0f172a')
    d.text((70, 185), "Loan Contract Number: 4501-8890-1200", fill='#0f172a')
    d.text((500, 155), "Facility Amount: 6,500,000,000 Rials", fill='#c2410c')
    d.text((500, 185), "Installment Term: 240 Months", fill='#0f172a')

    # Schedule Table Mockup
    y = 250
    d.rectangle([50, y, 806, y + 35], fill='#ea580c')
    d.text((90, y + 18), "No.", fill='#ffffff', anchor="mm")
    d.text((250, y + 18), "Due Date", fill='#ffffff', anchor="mm")
    d.text((450, y + 18), "Amount (Rials)", fill='#ffffff', anchor="mm")
    d.text((680, y + 18), "Status", fill='#ffffff', anchor="mm")

    for idx, (due, amt, st) in enumerate([("1403/08/25", "32,500,000", "PAID"), ("1403/09/25", "32,500,000", "PAID"), ("1403/10/25", "32,500,000", "CURRENT")]):
        row_y = y + 40 + idx * 36
        d.rectangle([50, row_y, 806, row_y + 32], fill='#f8fafc' if idx % 2 == 0 else '#ffffff', outline='#e2e8f0')
        d.text((90, row_y + 16), str(idx + 1), fill='#0f172a', anchor="mm")
        d.text((250, row_y + 16), due, fill='#0f172a', anchor="mm")
        d.text((450, row_y + 16), amt, fill='#0f172a', anchor="mm")
        d.text((680, row_y + 16), st, fill='#16a34a' if st == 'PAID' else '#2563eb', anchor="mm")

    # Round Bank Stamp
    d.ellipse([640, 380, 770, 500], outline='#dc2626', width=3)
    d.text((705, 430), "BANK MASKAN", fill='#dc2626', anchor="mm")
    d.text((705, 455), "CENTRAL BRANCH", fill='#dc2626', anchor="mm")

    img.save(output_path, 'JPEG', quality=95)
    print(f"Generated Bank Booklet: {output_path}")


def draw_sayad_check(output_path):
    img = Image.new('RGB', (856, 420), color='#faf5ff')
    d = ImageDraw.Draw(img)

    # Border
    d.rounded_rectangle([12, 12, 844, 408], radius=14, outline='#9333ea', width=3)
    
    # Purple Security Header
    d.rectangle([15, 15, 841, 75], fill='#9333ea')
    d.text((428, 45), "SAYAD OFFICIAL CHEQUE - CENTRAL BANK OF IRAN", fill='#ffffff', anchor="mm")

    # Sayad 16-Digit ID Box
    d.rounded_rectangle([40, 95, 400, 140], radius=6, fill='#f3e8ff', outline='#c084fc', width=2)
    d.text((220, 118), "SAYAD ID: 4501 8892 1029 3481", fill='#6b21a8', anchor="mm")

    # Date Box
    d.rounded_rectangle([520, 95, 810, 140], radius=6, fill='#ffffff', outline='#c084fc', width=1)
    d.text((665, 118), "DATE: 1404 / 06 / 15", fill='#0f172a', anchor="mm")

    # Payee & Amount Lines
    d.text((60, 175), "PAY TO THE ORDER OF: Ministry of Roads & Urban Development", fill='#1e293b')
    d.line([60, 200, 800, 200], fill='#c084fc', width=1)

    d.text((60, 225), "THE SUM OF: Four Hundred Million Rials Only", fill='#1e293b')
    d.line([60, 250, 800, 250], fill='#c084fc', width=1)

    d.rounded_rectangle([500, 270, 800, 325], radius=6, fill='#ffffff', outline='#9333ea', width=2)
    d.text((650, 298), "# 400,000,000 Rials #", fill='#9333ea', anchor="mm")

    # Signature Area
    d.rectangle([540, 340, 780, 395], outline='#c084fc', width=1)
    d.text((660, 365), "[DIGITALLY REGISTERED SIGNATURE]", fill='#6b21a8', anchor="mm")

    img.save(output_path, 'JPEG', quality=95)
    print(f"Generated Sayad Check: {output_path}")


def draw_title_deed(output_path, nat_id="0012345678"):
    img = Image.new('RGB', (800, 1050), color='#fefce8')
    d = ImageDraw.Draw(img)

    # Intricate Green Border
    d.rectangle([20, 20, 780, 1030], outline='#166534', width=4)
    d.rectangle([30, 30, 770, 1020], outline='#15803d', width=1)

    # Header
    d.text((400, 70), "STATE ORGANIZATION FOR REGISTRATION OF DEEDS & PROPERTIES", fill='#14532d', anchor="mm")
    d.text((400, 100), "CADASTRAL SINGLE-SHEET TITLE DEED (سند مالکیت تک‌برگ)", fill='#166534', anchor="mm")

    # Cadastral Code Box
    d.rounded_rectangle([60, 140, 740, 210], radius=8, fill='#f0fdf4', outline='#86efac', width=2)
    d.text((400, 175), "ELECTRONIC CADASTRAL IDENTIFIER: 1403-9821-4401-8890", fill='#166534', anchor="mm")

    # Property Particulars
    y = 240
    d.text((70, y), "Registry Section: 04 Central Province", fill='#0f172a')
    d.text((450, y), "Main Plaque: 2405 / Sub: 12", fill='#0f172a')
    
    y += 40
    d.text((70, y), "Apartment Unit: 14 (Floor 3)", fill='#0f172a')
    d.text((450, y), "Net Floor Area: 85.50 m²", fill='#0f172a')

    y += 40
    d.text((70, y), f"Owner National ID: {nat_id}", fill='#0f172a')
    d.text((450, y), "Ownership Share: Six Dangs (Full)", fill='#15803d')

    # Cadastral Map Grid
    y = 380
    d.rectangle([70, y, 730, y + 360], fill='#ffffff', outline='#166534', width=2)
    for gx in range(90, 720, 45):
        d.line([gx, y, gx, y + 360], fill='#e2e8f0', width=1)
    for gy in range(y + 20, y + 350, 45):
        d.line([70, gy, 730, gy], fill='#e2e8f0', width=1)

    # Plot outline in red
    d.polygon([(220, y + 80), (560, y + 80), (560, y + 270), (220, y + 270)], outline='#dc2626', width=3)
    d.text((390, y + 170), "UNIT 14 (85.5 m²)", fill='#dc2626', anchor="mm")

    # Notary Red Seal
    d.ellipse([540, 800, 700, 960], outline='#dc2626', width=4)
    d.text((620, 870), "REGISTRY NOTARY", fill='#dc2626', anchor="mm")
    d.text((620, 895), "SEAL APPROVED", fill='#dc2626', anchor="mm")

    img.save(output_path, 'JPEG', quality=95)
    print(f"Generated Title Deed: {output_path}")


def draw_unit_selection(output_path, nat_id="0012345678"):
    img = Image.new('RGB', (800, 1050), color='#ffffff')
    d = ImageDraw.Draw(img)

    # Border
    d.rectangle([20, 20, 780, 1030], outline='#0284c7', width=3)
    
    # Header
    d.rectangle([25, 25, 775, 115], fill='#f0f9ff')
    d.text((400, 55), "NATIONAL HOUSING MOVEMENT - PRE-SELECTED UNIT CERTIFICATE", fill='#0369a1', anchor="mm")
    d.text((400, 85), "مجوز رسمی انتخاب واحد و تخصیص قطعی مسکن", fill='#0284c7', anchor="mm")

    # Applicant particulars table
    y = 150
    d.rectangle([50, y, 750, y + 180], fill='#f8fafc', outline='#cbd5e1')
    d.text((70, y + 25), f"Applicant National ID: {nat_id}", fill='#0f172a')
    d.text((450, y + 25), "Allocation Date: 1403/05/10", fill='#0f172a')

    d.text((70, y + 65), "Project: Zaytoun 26 National Housing", fill='#0f172a')
    d.text((450, y + 65), "Site: 560 Hectare Qom Site", fill='#0f172a')

    d.text((70, y + 105), "Block: B-12 | Floor: 4 | Unit: 16", fill='#0369a1')
    d.text((450, y + 105), "Unit Area: 87.20 m²", fill='#0f172a')

    d.text((70, y + 145), "Parking Number: 16 | Storage: 16", fill='#475569')
    d.text((450, y + 145), "Construction Type: Apartment", fill='#475569')

    # Watermark Brokerage Seal
    d.ellipse([530, 800, 710, 980], outline='#0284c7', width=3)
    d.text((620, 880), "HOUSING BROKERAGE", fill='#0284c7', anchor="mm")
    d.text((620, 905), "OFFICIALLY CONFIRMED", fill='#0284c7', anchor="mm")

    img.save(output_path, 'JPEG', quality=95)
    print(f"Generated Unit Selection: {output_path}")


def process_all_uploads():
    base_uploads = "uploads"
    for folder in os.listdir(base_uploads):
        folder_path = os.path.join(base_uploads, folder)
        if not os.path.isdir(folder_path) or folder == "signatures":
            continue
        
        nat_id = folder
        print(f"\nProcessing folder: {folder_path} (National ID: {nat_id})")

        # 1. National ID image
        for fn in [f"national_id_{nat_id}.jpg", f"applicant_{nat_id}.pdf", f"applicant_{nat_id}.jpg"]:
            fp = os.path.join(folder_path, fn)
            draw_national_id(fp, title="کارت ملی متقاضی", nat_id=nat_id, name="متقاضی مسکن ملی")

        # 2. Spouse ID image
        for fn in os.listdir(folder_path):
            if fn.startswith("spouse_id"):
                fp = os.path.join(folder_path, fn)
                draw_national_id(fp, title="کارت ملی همسر", nat_id="0029876543", name="همسر متقاضی")

        # 3. Sayad Check image
        for fn in os.listdir(folder_path):
            if "sayad_check" in fn:
                fp = os.path.join(folder_path, fn)
                draw_sayad_check(fp)

        # 4. Bank booklet
        for fn in os.listdir(folder_path):
            if "bank_installment_booklet" in fn:
                fp = os.path.join(folder_path, fn)
                draw_bank_booklet(fp, nat_id=nat_id)

        # 5. Title deed
        for fn in os.listdir(folder_path):
            if "title_deed" in fn:
                fp = os.path.join(folder_path, fn)
                draw_title_deed(fp, nat_id=nat_id)

        # 6. Unit selection
        for fn in os.listdir(folder_path):
            if "unit_selection" in fn:
                fp = os.path.join(folder_path, fn)
                draw_unit_selection(fp, nat_id=nat_id)

if __name__ == "__main__":
    process_all_uploads()
    print("\nALL SCAN IMAGES SUCCESSFULLY REPLACED WITH VALID BINARY JPEG FILES!")
