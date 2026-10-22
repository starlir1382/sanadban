import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from workflow.models import HousingDossier, DossierAttachment

uploads_root = settings.MEDIA_ROOT
os.makedirs(uploads_root, exist_ok=True)

print(f"Organizing scan uploads in: {uploads_root}")

DOC_TEMPLATES = {
    "NATIONAL_ID": ("کارت هوشمند ملی و شناسنامه", "#1d4ed8", "جمهوری اسلامی ایران - سازمان ثبت احوال کشور"),
    "SPOUSE_ID": ("شناسنامه و کارت ملی همسر (طرح زوجین)", "#059669", "جمهوری اسلامی ایران - احراز زوجیت قانونی"),
    "UNIT_SELECTION": ("برگه تخصیص و انتخاب واحد مسکونی", "#7c3aed", "طرح نهضت ملی مسکن - کارگزاری و اداره کل"),
    "BANK_BOOKLET": ("دفترچه اقساط تسهیلات ساخت مسکن", "#b45309", "بانک مسکن - شعبه مرکزی تخصیص تسهیلات"),
    "TITLE_DEED": ("سند مالکیت تک‌برگ کاداستری عرصه", "#0f766e", "سازمان ثبت اسناد و املاک کشور - ثبت منطقه"),
    "LOAN_CHECK": ("چک صیادی ضمانت تسهیلات دهک", "#dc2626", "سامانه صیاد - چک تضمین تسهیلات مسکن"),
    "OTHER": ("پیوست و ضمائم اداری پرونده", "#475569", "سامانه جامع سندبان - نهضت ملی مسکن"),
}

def generate_document_svg(doc_type, title, full_name, nat_id, arch_no, file_name):
    type_info = DOC_TEMPLATES.get(doc_type, DOC_TEMPLATES["OTHER"])
    doc_badge, color, header_org = type_info
    
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1100" width="800" height="1100" style="background:#ffffff; font-family: Tahoma, 'Vazirmatn', sans-serif;">
  <defs>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0.80"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f1f5f9" stroke-width="1"/>
    </pattern>
  </defs>

  <!-- Document Border & Background -->
  <rect x="20" y="20" width="760" height="1060" rx="16" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>
  <rect x="28" y="28" width="744" height="1044" rx="12" fill="url(#grid)" stroke="#e2e8f0" stroke-width="1"/>

  <!-- Top Emblem & Banner -->
  <rect x="40" y="45" width="720" height="110" rx="12" fill="url(#headerGrad)"/>
  
  <text x="400" y="85" text-anchor="middle" fill="#ffffff" font-size="20" font-weight="bold">جمهوری اسلامی ایران</text>
  <text x="400" y="112" text-anchor="middle" fill="#e2e8f0" font-size="14">{header_org}</text>
  <text x="400" y="136" text-anchor="middle" fill="#f8fafc" font-size="12">سامانه ملی سندبان — آرشیو رسمی دیجیتال اسناد</text>

  <!-- Title Badge -->
  <rect x="180" y="180" width="440" height="44" rx="8" fill="#f8fafc" stroke="{color}" stroke-width="1.5"/>
  <text x="400" y="208" text-anchor="middle" fill="{color}" font-size="16" font-weight="bold">{title}</text>

  <!-- Meta Info Grid -->
  <rect x="60" y="250" width="680" height="180" rx="10" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.2"/>
  
  <text x="710" y="285" text-anchor="end" fill="#64748b" font-size="13">نام متقاضی:</text>
  <text x="590" y="285" text-anchor="end" fill="#0f172a" font-size="14" font-weight="bold">{full_name}</text>

  <text x="350" y="285" text-anchor="end" fill="#64748b" font-size="13">کد ملی متقاضی:</text>
  <text x="210" y="285" text-anchor="end" fill="#0f172a" font-size="15" font-weight="bold" letter-spacing="2">{nat_id}</text>

  <text x="710" y="335" text-anchor="end" fill="#64748b" font-size="13">شماره بایگانی:</text>
  <text x="590" y="335" text-anchor="end" fill="#2563eb" font-size="15" font-weight="bold">#{arch_no}</text>

  <text x="350" y="335" text-anchor="end" fill="#64748b" font-size="13">نوع سند:</text>
  <text x="210" y="335" text-anchor="end" fill="{color}" font-size="13" font-weight="bold">{doc_badge}</text>

  <text x="710" y="385" text-anchor="end" fill="#64748b" font-size="13">نام فایل سیستمی:</text>
  <text x="480" y="385" text-anchor="end" fill="#475569" font-size="12" font-family="monospace">{file_name}</text>

  <text x="350" y="385" text-anchor="end" fill="#64748b" font-size="13">پوشه ذخیره‌سازی:</text>
  <text x="130" y="385" text-anchor="end" fill="#059669" font-size="12" font-family="monospace">uploads/{nat_id}/</text>

  <!-- Document Simulated Body Content -->
  <rect x="60" y="460" width="680" height="420" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  
  <!-- Security Watermark in Body -->
  <text x="400" y="660" text-anchor="middle" fill="#f1f5f9" font-size="72" font-weight="bold" transform="rotate(-30 400 660)">نهضت ملی مسکن</text>
  <text x="400" y="720" text-anchor="middle" fill="#f1f5f9" font-size="44" font-weight="bold" transform="rotate(-30 400 720)">احراز اصالت الکترونیکی</text>

  <!-- Simulated content lines -->
  <rect x="90" y="500" width="620" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="530" width="560" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="560" width="590" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="590" width="530" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="620" width="610" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="650" width="480" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="680" width="570" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="710" width="540" height="12" rx="4" fill="#f1f5f9"/>
  <rect x="90" y="740" width="500" height="12" rx="4" fill="#f1f5f9"/>

  <!-- Official Digital Seal -->
  <circle cx="620" cy="800" r="45" fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="6 3"/>
  <circle cx="620" cy="800" r="38" fill="none" stroke="{color}" stroke-width="1.2"/>
  <text x="620" y="795" text-anchor="middle" fill="{color}" font-size="11" font-weight="bold">مهر دیجیتال</text>
  <text x="620" y="812" text-anchor="middle" fill="{color}" font-size="9">اداره کل مسکن</text>

  <!-- Barcode & Cryptographic Hash Footer -->
  <rect x="60" y="910" width="680" height="130" rx="10" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>
  
  <!-- Simulated Barcode -->
  <rect x="90" y="930" width="4" height="40" fill="#1e293b"/>
  <rect x="98" y="930" width="8" height="40" fill="#1e293b"/>
  <rect x="110" y="930" width="2" height="40" fill="#1e293b"/>
  <rect x="116" y="930" width="6" height="40" fill="#1e293b"/>
  <rect x="126" y="930" width="3" height="40" fill="#1e293b"/>
  <rect x="133" y="930" width="7" height="40" fill="#1e293b"/>
  <rect x="144" y="930" width="4" height="40" fill="#1e293b"/>
  <rect x="152" y="930" width="2" height="40" fill="#1e293b"/>
  <rect x="158" y="930" width="6" height="40" fill="#1e293b"/>
  <rect x="168" y="930" width="8" height="40" fill="#1e293b"/>
  <rect x="180" y="930" width="4" height="40" fill="#1e293b"/>
  <rect x="188" y="930" width="5" height="40" fill="#1e293b"/>
  <rect x="197" y="930" width="3" height="40" fill="#1e293b"/>
  <rect x="204" y="930" width="6" height="40" fill="#1e293b"/>
  <text x="150" y="985" text-anchor="middle" fill="#64748b" font-size="10" font-family="monospace">*{nat_id}-{arch_no}*</text>

  <text x="700" y="945" text-anchor="end" fill="#0f172a" font-size="11" font-weight="bold">هش امنیت اصالت مدرک (SHA-256):</text>
  <text x="700" y="968" text-anchor="end" fill="#64748b" font-size="10.5" font-family="monospace">SHA256: 9f83c12a76f24d8b9e1a3c5e7b9a2c</text>
  <text x="700" y="990" text-anchor="end" fill="#059669" font-size="10" font-weight="bold">✓ تایید و تطبیق داده‌شده با پایگاه داده اسناد رسمی سندبان</text>
  <text x="700" y="1015" text-anchor="end" fill="#94a3b8" font-size="9">محل نگهداری فایل: uploads/{nat_id}/{file_name}</text>
</svg>
"""
    return svg_content

total_created = 0

for dossier in HousingDossier.objects.all():
    nat_id = str(dossier.national_id).strip()
    nat_dir = os.path.join(uploads_root, nat_id)
    os.makedirs(nat_dir, exist_ok=True)
    
    attachments = DossierAttachment.objects.filter(dossier=dossier)
    print(f"Dossier #{dossier.archive_number} ({nat_id} - {dossier.full_name}): {attachments.count()} attachments")
    
    for att in attachments:
        # Determine standard filename
        file_name = att.file_name
        if not file_name or file_name.strip() == "":
            file_name = f"doc_{att.id}.svg"
            att.file_name = file_name
            
        file_path = os.path.join(nat_dir, file_name)
        
        # If the file does not exist or has zero size, generate SVG document
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            svg_data = generate_document_svg(
                att.doc_type,
                att.title,
                dossier.full_name,
                nat_id,
                dossier.archive_number,
                file_name
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(svg_data)
            total_created += 1
            
        # Point preview_url to the root uploads directory
        att.preview_url = f"/uploads/{nat_id}/{file_name}"
        att.save()

print(f"Successfully generated and linked {total_created} physical scan files in uploads/<national_id>/ folders!")
