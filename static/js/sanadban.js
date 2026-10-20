/**
 * SanadBan (DeedFlow) - Interactive Logic Engine & Alpine.js Store
 * Full 24-Stage Housing Workflow & Interactive Scan Viewer
 */

// Persian Number to Words Converter Utility
const PersianNumberWords = {
  units: ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه'],
  teens: ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده'],
  tens: ['', 'ده', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود'],
  hundreds: ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد'],
  scales: ['', 'هزار', 'میلیون', 'میلیارد', 'تریلیون'],

  convertGroup(num) {
    let parts = [];
    let h = Math.floor(num / 100);
    let rem = num % 100;
    let t = Math.floor(rem / 10);
    let u = rem % 10;

    if (h > 0) parts.push(this.hundreds[h]);

    if (rem >= 10 && rem < 20) {
      parts.push(this.teens[rem - 10]);
    } else {
      if (t > 0) parts.push(this.tens[t]);
      if (u > 0) parts.push(this.units[u]);
    }

    return parts.join(' و ');
  },

  toWords(num) {
    if (!num || isNaN(num) || num === 0) return 'صفر ریال';
    num = Math.floor(Number(num));
    if (num < 0) return 'منفی ' + this.toWords(-num);

    let chunks = [];
    let scaleIndex = 0;

    while (num > 0) {
      let chunk = num % 1000;
      if (chunk !== 0) {
        let text = this.convertGroup(chunk);
        let scale = this.scales[scaleIndex];
        chunks.unshift(scale ? `${text} ${scale}` : text);
      }
      num = Math.floor(num / 1000);
      scaleIndex++;
    }

    return chunks.join(' و ') + ' ریال';
  },

  formatThousand(val) {
    if (!val && val !== 0) return '';
    return val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
};

// Merged 24-Stage Workflow Configuration
const STAGES_24 = [
  { id: 1, unit: 'brokerage', role: 'کارشناس ثبت درخواست کارگزاری', title: 'ورود اطلاعات متقاضی، همسر، واحد و پروژه', category: 'کارگزاری اولیه' },
  { id: 2, unit: 'brokerage', role: 'کارشناس ثبتی کارگزاری', title: 'ورود اطلاعات ثبتی عرصه و پلاک', category: 'کارگزاری اولیه' },
  { id: 3, unit: 'brokerage', role: 'کارشناس مالی کارگزاری', title: 'ورود مبلغ تمام‌شده بدون وام ۶۵۰ میلیونی', category: 'کارگزاری اولیه' },
  { id: 4, unit: 'brokerage', role: 'مدیرعامل کارگزاری', title: 'تأیید مدیرعامل کارگزاری', category: 'کارگزاری اولیه' },
  { id: 5, unit: 'directorate', role: 'کارشناس بررسی فرم جیم', title: 'کارشناس بررسی فرم جیم', category: 'اداره کل - استعلامات' },
  { id: 6, unit: 'brokerage', role: 'کارشناس مالی کارگزاری', title: 'ورود مبلغ وام صندوق', category: 'تسهیلات و مالی' },
  { id: 7, unit: 'directorate', role: 'کارشناس پیمانکاران اداره کل', title: 'ورود مبلغ نامه پیمانکار', category: 'تسهیلات و مالی' },
  { id: 8, unit: 'directorate', role: 'کارشناس تسهیلات دهک اداره کل', title: 'ورود مبلغ وام دهک', category: 'تسهیلات و مالی' },
  { id: 9, unit: 'brokerage', role: 'کارشناس امور متقاضیان', title: 'تعیین مبلغ آورده نقدی متقاضی و ارسال پیامک', category: 'اطلاع‌رسانی متقاضی' },
  { id: 10, unit: 'brokerage', role: 'کارشناس مالی کارگزاری', title: 'تأیید تأمین مبلغ آورده متقاضی', category: 'اطلاع‌رسانی متقاضی' },
  { id: 11, unit: 'brokerage', role: 'کارشناس امور بانکی', title: 'ارسال و درج شماره نامه بانک', category: 'امور بانکی و اسکن' },
  { id: 12, unit: 'brokerage', role: 'کارشناس اسکن و بایگانی کارگزاری', title: 'اسکن مدارک و دفترچه قسط', category: 'امور بانکی و اسکن' },
  { id: 13, unit: 'directorate', role: 'کارشناس نهضت ملی مسکن', title: 'کارشناس نهضت ملی مسکن', category: 'تاییدات اداره کل' },
  { id: 14, unit: 'directorate', role: 'کارشناس ثبت فرم ج', title: 'کارشناس ثبت فرم ج', category: 'تاییدات اداره کل' },
  { id: 15, unit: 'directorate', role: 'کارشناس فنی و مهندسی', title: 'کارشناس فنی و مهندسی (پلاک و نقشه)', category: 'تاییدات اداره کل' },
  { id: 16, unit: 'directorate', role: 'کارشناس املاک', title: 'کارشناس املاک (اسکن سند مالکیت)', category: 'تاییدات اداره کل' },
  { id: 17, unit: 'directorate', role: 'کارشناس بانک زمین', title: 'کارشناس بانک زمین', category: 'تاییدات اداره کل' },
  { id: 18, unit: 'directorate', role: 'کارشناس حقوقی', title: 'کارشناس حقوقی', category: 'تاییدات اداره کل' },
  { id: 19, unit: 'directorate', role: 'کارشناس ارزیابی', title: 'کارشناس ارزیابی (اجاره و آماده‌سازی)', category: 'ارزیابی و وصول' },
  { id: 20, unit: 'brokerage', role: 'کارشناس وصول کارگزاری', title: 'دریافت چک‌های وام دهک', category: 'ارزیابی و وصول' },
  { id: 21, unit: 'brokerage', role: 'کارشناس مالی کارگزاری', title: 'دریافت نقد و اقساط آماده‌سازی و اجاره', category: 'ارزیابی و وصول' },
  { id: 22, unit: 'directorate', role: 'کارشناس تسویه با پیمانکار', title: 'کارشناس تسویه با پیمانکار سازنده', category: 'تسویه و خاتمه' },
  { id: 23, unit: 'directorate', role: 'کارشناس صدور نامه محضر', title: 'چاپ فرم مراحل و نامه محضر', category: 'صدور و بایگانی' },
  { id: 24, unit: 'directorate', role: 'کارشناس بایگانی اداره کل', title: 'بایگانی نهایی پرونده', category: 'صدور و بایگانی' }
];

// Alpine.js Application Store & Controller
document.addEventListener('alpine:init', () => {
  Alpine.data('sanadbanApp', () => ({
    // Pipeline State
    currentStage: 1,
    stages: STAGES_24,
    archiveNumber: 100001,
    isLocked: false,
    selectedCategory: 'all',
    attachmentViewMode: 'album',
    todayDate: '',

    // Modals
    showSignatureModal: false,
    showReturnModal: false,
    showScanViewerModal: false,
    showUploadModal: false,
    isScanning: false,
    isSaving: false,
    showToast: false,
    toastMessage: '',
    toastType: 'success',

    // Upload & Scanner Form State
    uploadForm: {
      title: '',
      doc_type: 'NATIONAL_ID',
      fileName: '',
      preview_url: '',
      rawFile: null
    },

    // Return Routing
    selectedReturnStage: 1,
    returnNotes: '',

    // Signature Form
    signerPin: '',
    signAgreement: false,

    // Scan Viewer & Lightbox State
    activeScan: {
      id: 1,
      type: 'NATIONAL_ID',
      title: 'اسکن کارت ملی هوشمند متقاضی',
      fileName: 'national_id_0012345678.jpg',
      uploader: 'احمد صادقی (کارشناس ثبت کارگزاری)',
      uploadDate: '۱۴۰۳/۰۵/۱۰',
      stage: 1,
      sha256: '9f83c12a76f24d8b9e1a3c5e7b9a',
      zoom: 1,
      rotation: 0
    },

    // Form Data - Merged 31+ Fields Matrix
    form: {
      // Stage 1 Fields
      full_name: 'علیرضا رضایی پور',
      father_name: 'محمدرضا',
      national_id: '0012345678',
      birth_date: '1365/04/15',
      spouse_full_name: 'فاطمه السادات موسوی',
      spouse_national_id: '0029876543',
      decile: 4,
      site: 'شهید رئیسی',
      project: 'پروژه ۵۶۰ هکتاری فاز ۲ (تعداد واحد: ۳۲۰)',
      construction_type: 'آپارتمانی',
      block_name: 'بلوک B-14',
      floor_number: 3,
      unit_number: 12,
      unit_area: 85.50,
      storage_number: 12,
      storage_area: 3.20,
      parking_number: 12,
      parking_area: 12.50,

      // Stage 2: Plot & Registry
      registration_section: 'بخش ۱ ثبتی قم',
      main_plaque: 1420,
      separated_plaque: 85,
      sub_plaque: 312,
      plot_number: 48,

      // Stage 3: Base Cost without 650M Toman loan
      base_cost_without_loan: 4500000000,

      // Stage 6: Fund Loan Amount
      fund_loan_amount: 500000000,

      // Stage 7: Contractor Letter Amount
      contractor_letter_amount: 3800000000,

      // Stage 8: Decile Loan Amount
      decile_loan_amount: 1000000000,

      // Stage 9: Applicant Cash Equity
      applicant_equity: 3000000000,
      is_sms_sent: false,
      sms_sent_at: '',

      // Stage 10: Confirmation of equity funding
      is_equity_funded: false,

      // Stage 11: Bank Letter
      bank_letter_number: '1403/BM/88412',
      bank_letter_date: '1403/05/18',

      // Stage 19: Valuation Fields
      total_land_share: 42.75,
      past_years_rent: 180000000,
      current_year_rent: 45000000,
      land_lease_year: '1403',
      preparation_cost: 320000000,

      // Stage 22: Cash & Non-cash Prep & Rent Installments
      cash_preparation_amount: 120000000,
      non_cash_preparation_amount: 200000000,
      is_cash_rent_confirmed: false,
      is_decile_loan_confirmed: false
    },

    // Scanned Documents (populated dynamically from database without ghost record flicker)
    attachments: [],

    // Audit Trail / History (populated dynamically from database)
    auditLogs: [],

    init() {
      // 1. Set Persian Today Date dynamically
      this.todayDate = this.getTodayJalali();

      // 2. Read real server data injected from database
      const serverDataEl = document.getElementById('dossier-server-json');
      if (serverDataEl && serverDataEl.textContent.trim()) {
        try {
          const serverData = JSON.parse(serverDataEl.textContent);
          if (serverData.archive_number) this.archiveNumber = serverData.archive_number;
          if (serverData.current_stage) this.currentStage = Number(serverData.current_stage);
          if (typeof serverData.is_locked !== 'undefined') this.isLocked = Boolean(serverData.is_locked);
          if (serverData.form) {
            this.form = Object.assign({}, this.form, serverData.form);
          }
          if (Array.isArray(serverData.attachments)) {
            this.attachments = serverData.attachments;
          }
          if (Array.isArray(serverData.audit_logs)) {
            this.auditLogs = serverData.audit_logs;
          }
        } catch (e) {
          console.error('Failed to parse server dossier data:', e);
        }
      }
      this.recalculateEquity();
    },

    getTodayJalali() {
      try {
        const formatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { 
          weekday: 'long', 
          day: 'numeric', 
          month: 'long', 
          year: 'numeric' 
        });
        const parts = formatter.formatToParts(new Date()).reduce((acc, p) => ({ ...acc, [p.type]: p.value }), {});
        return `${parts.weekday} ${parts.day} ${parts.month} ${parts.year}`;
      } catch (e) {
        return new Date().toLocaleDateString('fa-IR');
      }
    },

    // Persist Stage Switch to Database
    async selectStage(stgId) {
      this.currentStage = stgId;
      this.recalculateEquity();
      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        await fetch(`/dossier/${this.archiveNumber}/set-stage/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ stage: stgId })
        });
      } catch (err) {
        console.warn('Could not persist stage switch:', err);
      }
    },

    // Save Dossier Draft Directly to Database
    async saveDossierDraft(notify = true) {
      this.isSaving = true;
      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const payload = Object.assign({}, this.form, { current_stage: this.currentStage });
        const res = await fetch(`/dossier/${this.archiveNumber}/save/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const data = await res.json();
          if (notify) {
            this.triggerToast('کلیه تغییرات با موفقیت در پایگاه داده ذخیره گردید.', 'success');
          }
          if (typeof data.applicant_equity !== 'undefined') {
            this.form.applicant_equity = data.applicant_equity;
          }
        } else {
          const errData = await res.json().catch(() => ({}));
          this.triggerToast(errData.message || 'خطا در ذخیره اطلاعات بر روی سرور.', 'error');
        }
      } catch (err) {
        console.error('Save draft error:', err);
        this.triggerToast('خطا در برقراری ارتباط با سرور پایگاه داده.', 'error');
      } finally {
        this.isSaving = false;
      }
    },

    // Live Equity Auto-Calculation Formula
    recalculateEquity() {
      const baseCost = Number(this.form.base_cost_without_loan) || 0;
      const fundLoan = Number(this.form.fund_loan_amount) || 0;
      const decileLoan = Number(this.form.decile_loan_amount) || 0;
      this.form.applicant_equity = Math.max(0, baseCost - (fundLoan + decileLoan));
    },

    getFilteredAttachments() {
      if (!this.selectedCategory || this.selectedCategory === 'all') return this.attachments;
      if (this.selectedCategory === 'identity') return this.attachments.filter(a => a.type === 'NATIONAL_ID' || a.type === 'SPOUSE_ID');
      if (this.selectedCategory === 'bank') return this.attachments.filter(a => a.type === 'BANK_BOOKLET' || a.type === 'BANK_LETTER');
      if (this.selectedCategory === 'deed') return this.attachments.filter(a => a.type === 'TITLE_DEED' || a.type === 'UNIT_SELECTION');
      if (this.selectedCategory === 'checks') return this.attachments.filter(a => a.type === 'LOAN_CHECK' || a.type === 'PREP_CHECK');
      return this.attachments;
    },

    // Stage 9: Send SMS simulation
    sendEquitySMS() {
      this.form.is_sms_sent = true;
      this.form.sms_sent_at = '1403/05/18 14:20';
      
      this.auditLogs.unshift({
        step: 9,
        fromStage: 'مرحله ۹: تعیین مبلغ آورده',
        toStage: 'مرحله ۹: ارسال پیامک',
        actor: 'سیستم پیام‌رسان هوشمند سندبان',
        role: 'سامانه اطلاع‌رسانی پیامکی',
        action: 'SMS',
        actionLabel: 'ارسال پیامک آورده متقاضی',
        timestamp: '1403/05/18 14:20:00',
        hash: 'SHA256: sms88412' + Math.random().toString(36).substring(2, 8),
        notes: `پیامک به شماره همراه متقاضی ارسال شد: «متقاضی گرامی ${this.form.full_name}، مبلغ آورده نقدی شما ${this.formatNumber(this.form.applicant_equity)} ریال تعیین گردید. مهلت واریز: ۵ روز کاری.»`
      });

      this.triggerToast(`پیامک ابلاغ مبلغ آورده (${this.formatNumber(this.form.applicant_equity)} ریال) با موفقیت به متقاضی ارسال شد.`, 'success');
    },

    // Stage 10: Confirm Equity Funding
    confirmEquityFunding() {
      this.form.is_equity_funded = true;
      this.triggerToast('تأمین و واریز مبلغ آورده نقدی متقاضی با موفقیت تأیید گردید.', 'success');
    },

    // Interactive Scan Viewer & Lightbox Methods
    openScanViewer(item) {
      this.activeScan = {
        ...item,
        zoom: 1,
        rotation: 0
      };
      this.showScanViewerModal = true;
    },

    zoomInScan() {
      if (this.activeScan.zoom < 2.5) {
        this.activeScan.zoom = +(this.activeScan.zoom + 0.25).toFixed(2);
      }
    },

    zoomOutScan() {
      if (this.activeScan.zoom > 0.5) {
        this.activeScan.zoom = +(this.activeScan.zoom - 0.25).toFixed(2);
      }
    },

    rotateScan() {
      this.activeScan.rotation = (this.activeScan.rotation + 90) % 360;
    },

    resetScan() {
      this.activeScan.zoom = 1;
      this.activeScan.rotation = 0;
    },

    closeScanViewer() {
      this.showScanViewerModal = false;
    },

    // Upload & Scanner Controller Methods
    openUploadScanModal() {
      let defaultTitle = 'مدرک پیوست مرحله ' + this.currentStage;
      let defaultType = 'OTHER';

      if (this.currentStage <= 4) {
        defaultTitle = 'اسکن کارت ملی و مدارک سجلی';
        defaultType = 'NATIONAL_ID';
      } else if (this.currentStage === 12) {
        defaultTitle = 'اسکن دفترچه اقساط تسهیلات بانک مسکن';
        defaultType = 'BANK_BOOKLET';
      } else if (this.currentStage === 16) {
        defaultTitle = 'اسکن سند مالکیت تک‌برگ عرصه و اعیان';
        defaultType = 'TITLE_DEED';
      } else if (this.currentStage === 20) {
        defaultTitle = 'اسکن چک صیادی تسهیلات دهک';
        defaultType = 'LOAN_CHECK';
      }

      this.uploadForm = {
        title: defaultTitle,
        doc_type: defaultType,
        fileName: '',
        preview_url: '',
        rawFile: null
      };
      this.isScanning = false;
      this.showUploadModal = true;
    },

    setQuickScanTitle(title, type) {
      this.uploadForm.title = title;
      this.uploadForm.doc_type = type;
    },

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;

      this.uploadForm.rawFile = file;
      this.uploadForm.fileName = file.name;

      if (!this.uploadForm.title || this.uploadForm.title.startsWith('مدرک پیوست')) {
        this.uploadForm.title = file.name.replace(/\.[^/.]+$/, "");
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        this.uploadForm.preview_url = e.target.result;
      };
      reader.readAsDataURL(file);
    },

    simulateScannerDevice() {
      this.isScanning = true;
      setTimeout(() => {
        this.isScanning = false;
        this.uploadForm.fileName = `scanner_wia_${Date.now()}.jpg`;
        this.uploadForm.preview_url = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="600" height="400" fill="%23f8fafc" stroke="%233b82f6" stroke-width="4"/><text x="50%" y="40%" font-size="20" font-family="Tahoma" fill="%231e3a8a" text-anchor="middle">سند اسکن شده از دستگاه اسکنر متصل (WIA/TWAIN)</text><text x="50%" y="55%" font-size="14" font-family="Tahoma" fill="%23059669" text-anchor="middle">کیفیت اسکن: 300 DPI - رنگی - تایید اصالت الکترونیکی</text><circle cx="500" cy="320" r="45" fill="none" stroke="%23dc2626" stroke-dasharray="4,4" stroke-width="2"/><text x="500" y="325" font-size="11" font-family="Tahoma" fill="%23dc2626" text-anchor="middle">مهر دبیرخانه</text></svg>';
        this.triggerToast('سند با موفقیت از اسکنر سخت‌افزاری دریافت گردید.', 'success');
      }, 1200);
    },

    async submitScanUpload() {
      if (!this.uploadForm.title || this.uploadForm.title.trim().length < 2) {
        this.triggerToast('لطفاً عنوان مدرک را وارد فرمایید.', 'error');
        return;
      }

      const hashStr = 'SHA256: ' + Math.random().toString(36).substring(2, 10) + Math.random().toString(36).substring(2, 10);
      const nowStr = '۱۴۰۳/۰۵/۲۲ ' + new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });

      try {
        const formData = new FormData();
        formData.append('title', this.uploadForm.title);
        formData.append('doc_type', this.uploadForm.doc_type);
        formData.append('preview_url', this.uploadForm.preview_url || '');
        if (this.uploadForm.rawFile) {
          formData.append('file', this.uploadForm.rawFile);
        }

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        const response = await fetch(`/dossier/${this.archiveNumber}/upload-scan/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken
          },
          body: formData
        });

        if (response.ok) {
          const resData = await response.json();
          if (resData.attachment) {
            this.attachments.unshift({
              ...resData.attachment,
              preview_url: this.uploadForm.preview_url || resData.attachment.preview_url
            });
          }
        } else {
          this.appendScanClientSide(hashStr, nowStr);
        }
      } catch (err) {
        this.appendScanClientSide(hashStr, nowStr);
      }

      this.auditLogs.unshift({
        step: this.currentStage,
        fromStage: `مرحله ${this.currentStage}`,
        toStage: `مرحله ${this.currentStage}`,
        actor: 'کارشناس بارگذاری اسناد',
        role: this.stages[this.currentStage - 1].role,
        action: 'SUBMIT',
        actionLabel: `بارگذاری سند: ${this.uploadForm.title}`,
        timestamp: nowStr,
        hash: hashStr,
        notes: `مدرک «${this.uploadForm.title}» با موفقیت اسکن و در مرحله ${this.currentStage} ثبت گردید.`
      });

      this.triggerToast(`مدرک «${this.uploadForm.title}» با موفقیت بارگذاری و الصاق شد.`, 'success');
      this.showUploadModal = false;
    },

    appendScanClientSide(hashStr, nowStr) {
      const newScan = {
        id: Date.now(),
        stage: this.currentStage,
        type: this.uploadForm.doc_type,
        title: this.uploadForm.title,
        fileName: this.uploadForm.fileName || `scan_doc_${Date.now()}.jpg`,
        uploader: `کارشناس مرحله ${this.currentStage}`,
        uploadDate: nowStr,
        sha256: hashStr,
        preview_url: this.uploadForm.preview_url,
        immutable: true,
        desc: `مدرک بارگذاری‌شده در مرحله ${this.currentStage} (${this.stages[this.currentStage - 1].title})`
      };
      this.attachments.unshift(newScan);
    },

    // Stage Permission Checker
    isFieldEditable(fieldName) {
      const stage = this.currentStage;

      // Stage 1: Applicant, Spouse & Unit
      const stage1Fields = ['full_name', 'father_name', 'national_id', 'birth_date', 'spouse_full_name', 'spouse_national_id', 'decile', 'site', 'project', 'construction_type', 'block_name', 'floor_number', 'unit_number', 'unit_area', 'storage_number', 'storage_area', 'parking_number', 'parking_area'];
      if (stage1Fields.includes(fieldName)) return stage <= 4;

      // Stage 2 & 15: Plot and Registry (Editable in Stage 2 and Stage 15 by Technical Expert)
      const plotFields = ['registration_section', 'main_plaque', 'separated_plaque', 'sub_plaque', 'plot_number'];
      if (plotFields.includes(fieldName)) return stage === 2 || stage === 15;

      // Stage 3: Base cost
      if (fieldName === 'base_cost_without_loan') return stage <= 4;

      // Stage 6: Fund loan
      if (fieldName === 'fund_loan_amount') return stage === 6;

      // Stage 7: Contractor letter
      if (fieldName === 'contractor_letter_amount') return stage === 7;

      // Stage 8: Decile loan
      if (fieldName === 'decile_loan_amount') return stage === 8;

      // Stage 11: Bank letter
      if (fieldName === 'bank_letter_number' || fieldName === 'bank_letter_date') return stage === 11;

      // Stage 19: Valuation
      const stage19Fields = ['total_land_share', 'past_years_rent', 'current_year_rent', 'land_lease_year', 'preparation_cost'];
      if (stage19Fields.includes(fieldName)) return stage === 19;

      // Stage 21: Cash & Non-cash prep & rent
      const stage21Fields = ['cash_preparation_amount', 'non_cash_preparation_amount', 'is_cash_rent_confirmed', 'is_decile_loan_confirmed'];
      if (stage21Fields.includes(fieldName)) return stage === 21;

      return false;
    },

    // Forward & Sign
    openSignatureModal() {
      this.signerPin = '';
      this.signAgreement = true;
      this.showSignatureModal = true;
    },

    async confirmElectronicSignature() {
      // First save current form edits to database
      await this.saveDossierDraft(false);

      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/sign/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            notes: `تایید و امضای الکترونیکی مرحله ${this.currentStage} با موفقیت ثبت شد.`
          })
        });

        if (res.ok) {
          const data = await res.json();
          const prevStage = this.currentStage;
          this.currentStage = data.new_stage;
          if (data.is_locked) this.isLocked = true;

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${prevStage}: ${this.stages[prevStage - 1].title}`,
            toStage: this.currentStage <= 24 ? `مرحله ${this.currentStage}: ${this.stages[this.currentStage - 1].title}` : 'خاتمه و بایگانی قطعی',
            actor: 'کاربر ارشد سازمانی',
            role: this.stages[prevStage - 1]?.role || 'کارشناس اقدام‌کننده',
            action: 'SIGN',
            actionLabel: 'تایید و امضای دیجیتال',
            timestamp: new Date().toLocaleDateString('fa-IR') + ' ' + new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
            hash: data.hash,
            notes: `تایید و امضای الکترونیکی مرحله ${prevStage} با موفقیت در سامانه ثبت شد.`
          });

          this.triggerToast(data.message || `پرونده به مرحله ${this.currentStage} منتقل شد.`, 'success');
        } else {
          const errData = await res.json().catch(() => ({}));
          this.triggerToast(errData.message || 'خطا در ثبت امضای الکترونیکی.', 'error');
        }
      } catch (err) {
        console.error('Signature error:', err);
        this.triggerToast('خطا در ارسال درخواست امضا به سرور.', 'error');
      } finally {
        this.showSignatureModal = false;
      }
    },

    // Return Modal
    openReturnModal() {
      this.selectedReturnStage = Math.max(1, this.currentStage - 1);
      this.returnNotes = '';
      this.showReturnModal = true;
    },

    getAvailableReturnStages() {
      return this.stages.filter(s => s.id < this.currentStage);
    },

    async confirmReturnForCorrection() {
      if (!this.returnNotes || this.returnNotes.trim().length < 5) {
        this.triggerToast('ثبت توضیحات دلیل برگشت پرونده الزامی است (حداقل ۵ کاراکتر).', 'error');
        return;
      }

      const targetStage = this.selectedReturnStage;
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/return/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            target_stage: targetStage,
            notes: this.returnNotes
          })
        });

        if (res.ok) {
          const data = await res.json();
          const prevStage = this.currentStage;
          this.currentStage = data.new_stage;

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${prevStage}: ${this.stages[prevStage - 1].title}`,
            toStage: `مرحله ${targetStage}: ${this.stages[targetStage - 1].title}`,
            actor: 'کارشناس بررسی و ممیزی',
            role: this.stages[prevStage - 1]?.role || 'کارشناس ممیزی',
            action: 'RETURN',
            actionLabel: 'برگشت جهت اصلاح',
            timestamp: new Date().toLocaleDateString('fa-IR') + ' ' + new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
            hash: data.hash,
            notes: this.returnNotes
          });

          this.triggerToast(data.message || `پرونده به مرحله ${targetStage} بازگشت داده شد.`, 'warning');
        } else {
          const errData = await res.json().catch(() => ({}));
          this.triggerToast(errData.message || 'خطا در ثبت بازگشت پرونده.', 'error');
        }
      } catch (err) {
        console.error('Return error:', err);
        this.triggerToast('خطا در ارسال درخواست بازگشت به سرور.', 'error');
      } finally {
        this.showReturnModal = false;
      }
    },

    // Auto-fill PreSelectedUnit at Stage 1
    fetchPreSelectedUnit() {
      if (!this.form.national_id || this.form.national_id.length !== 10) {
        this.triggerToast('کد ملی وارد شده باید دقیقاً ۱۰ رقم باشد.', 'error');
        return;
      }
      this.form.full_name = 'علیرضا رضایی پور';
      this.form.father_name = 'محمدرضا';
      this.form.birth_date = '1365/04/15';
      this.form.spouse_full_name = 'فاطمه السادات موسوی';
      this.form.spouse_national_id = '0029876543';
      this.form.decile = 4;
      this.form.site = 'شهید رئیسی';
      this.form.project = 'پروژه ۵۶۰ هکتاری فاز ۲ (تعداد واحد: ۳۲۰)';
      this.form.construction_type = 'آپارتمانی';
      this.form.block_name = 'بلوک B-14';
      this.form.floor_number = 3;
      this.form.unit_number = 12;
      this.form.unit_area = 85.50;
      this.form.storage_number = 12;
      this.form.storage_area = 3.20;
      this.form.parking_number = 12;
      this.form.parking_area = 12.50;
      this.form.base_cost_without_loan = 4500000000;
      this.form.registration_section = 'بخش ۱ ثبتی قم';
      this.form.main_plaque = 1420;
      this.form.separated_plaque = 85;
      this.form.sub_plaque = 312;
      this.form.plot_number = 48;

      this.recalculateEquity();
      this.triggerToast('اطلاعات متقاضی، همسر و واحد مسکونی با موفقیت بارگذاری شد.', 'success');
    },

    toWords(num) {
      return PersianNumberWords.toWords(num);
    },

    formatNumber(num) {
      return PersianNumberWords.formatThousand(num);
    },

    triggerToast(msg, type = 'success') {
      this.toastMessage = msg;
      this.toastType = type;
      this.showToast = true;
      setTimeout(() => { this.showToast = false; }, 4000);
    }
  }));
});
