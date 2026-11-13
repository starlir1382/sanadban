// Which form section belongs to which workflow stage(s)
const SECTION_STAGE_MAP = {
  "section-applicant": [1, 2, 8, 9],
  "section-form-j": [3, 11],
  "section-spouse": [1, 2, 8, 9],
  "section-plot": [8, 9, 12],
  "section-cost": [8, 9, 19],
  "section-loans": [4, 19],
  "section-equity": [5],
  "section-applicant-equity": [5],
  "section-bank": [6, 10],
  "section-bank-letter": [6, 10],
  "section-docs-installment": [7, 8, 9, 21, 22],
  "section-notary": [20, 21, 22],
  "section-lease-contract": [21, 22],
  "section-valuation": [16, 19],
  "section-valuation-rent": [16, 19],
  "section-checks": [17, 18],
  "scans-album-section": [1, 7, 11, 13, 17, 18, 20, 21],
};

const FIELD_STAGE_MAP = {
  national_id: [1, 2, 8, 9],
  first_name: [1, 2, 8, 9],
  last_name: [1, 2, 8, 9],
  full_name: [1, 2, 8, 9],
  father_name: [1, 2, 8, 9],
  birth_date: [1, 2, 8, 9],
  applicant_id_number: [1, 2, 8, 9],
  applicant_id_serial: [1, 2, 8, 9],
  applicant_birth_place: [1, 2, 8, 9],
  applicant_phone: [1, 2, 8, 9],
  applicant_address: [1, 2, 8, 9],
  applicant_postal_code: [1, 2, 8, 9],
  applicant_landline_phone: [1, 2, 8, 9],
  selection_rank: [1, 2, 8, 9],
  decile: [1, 2, 4, 8, 9],
  marital_status: [1, 2, 8, 9],
  is_married_confirmed: [1, 2, 8, 9, 10],
  spouse_first_name: [1, 2, 8, 9],
  spouse_last_name: [1, 2, 8, 9],
  spouse_full_name: [1, 2, 8, 9],
  spouse_father_name: [1, 2, 8, 9],
  spouse_national_id: [1, 2, 8, 9],
  spouse_birth_date: [1, 2, 8, 9],
  spouse_id_number: [1, 2, 8, 9],
  spouse_id_serial: [1, 2, 8, 9],
  spouse_birth_place: [1, 2, 8, 9],
  site: [1, 2, 8, 9],
  project: [1, 2, 8, 9],
  project_code: [1, 2, 8, 9, 10],
  bank_name: [1, 2, 6, 8, 9],
  bank_branch: [1, 2, 6, 8, 9],
  construction_type: [1, 2, 8, 9],
  block_name: [1, 2, 8, 9],
  block_code: [1, 2, 8, 9],
  floor_number: [1, 2, 8, 9],
  unit_number: [1, 2, 8, 9],
  unit_code: [1, 2, 8, 9],
  bedroom_count: [1, 2, 8, 9],
  unit_direction: [1, 2, 8, 9],
  net_unit_area: [1, 2, 8, 9],
  common_area: [1, 2, 8, 9],
  total_area: [1, 2, 8, 9],
  unit_area: [1, 2, 8, 9],
  storage_number: [1, 2, 8, 9],
  storage_area: [1, 2, 8, 9],
  parking_number: [1, 2, 8, 9],
  parking_area: [1, 2, 8, 9],
  registration_section: [8, 9, 12],
  main_plaque: [8, 9, 12],
  separated_plaque: [8, 9, 12],
  sub_plaque: [8, 9, 12],
  plot_number: [8, 9, 12],
  renovation_code: [8, 9, 12],
  base_cost_without_loan: [8, 9, 19],
  form_j_registration_type: [3, 10, 11],
  form_j_questionnaire_number: [1, 3, 7, 8, 11],
  computer_code: [11],
  applicant_form_j_status: [1, 3, 8, 11],
  applicant_form_j_directorate_status: [1, 3, 8, 11],
  applicant_form_j_red_description: [1, 3, 8, 11],
  spouse_form_j_status: [1, 3, 8, 11],
  spouse_form_j_directorate_status: [1, 3, 8, 11],
  spouse_form_j_red_description: [1, 3, 8, 11],
  fund_loan_amount: [4, 19],
  contractor_letter_amount: [4, 19],
  decile_loan_amount: [4, 19],
  applicant_equity: [5],
  is_sms_sent: [5],
  sms_sent_at: [5],
  is_equity_funded: [5],
  bank_loan_amount: [6, 10],
  bank_letter_number: [6, 10],
  bank_letter_date: [6, 10],
  is_added_to_bank_shipment_list: [6, 10],
  is_sent_to_bank: [6, 10],
  bank_sent_date: [6, 10],
  bank_sent_letter_number: [6, 10],
  form_j_number: [1, 3, 7, 8, 11],
  has_installment_booklet: [7, 8],
  has_info_form: [7, 8],
  has_form_j: [7, 8],
  has_affidavit: [7, 8],
  has_sana: [7, 8],
  has_national_id_doc: [7, 8],
  total_land_share: [16],
  past_years_rent: [16],
  current_year_rent: [16],
  land_lease_year: [16],
  preparation_cost: [16],
  decile_loan_bank: [17],
  decile_bank_letter_number: [17, 18],
  decile_bank_letter_date: [17, 18],
  supported_institution: [17],
  check_count: [17],
  check_amount: [17],
  last_check_amount: [17],
  total_check_amount: [17],
  commitment_number: [17, 18],
  commitment_date: [17, 18],
  check_entries_json: [17, 18],
  is_decile_loan_confirmed: [17, 18],
  tenant_price: [17, 18],
  tenant_code: [17, 18],
  is_cash_rent_confirmed: [17, 18],
  cash_preparation_amount: [17, 18],
  prepayment_code: [17, 18],
  non_cash_preparation_amount: [17, 18],
  preparation_service_fee: [17, 18],
  preparation_check_count: [17, 18],
  total_preparation_check_amount: [17, 18],
  preparation_check_entries_json: [17, 18],
  is_preparation_checks_confirmed: [17, 18],
  visit_date: [17, 18],
  loan_visit_date: [17],
  prep_visit_date: [18],
  rah_letter: [8, 9, 12, 20],
  rah_letter_date: [8, 9, 12, 20],
  deed_number: [8, 9, 12],
  deed_date: [8, 9, 12],
  is_land_deed_confirmed: [8, 9, 12],
  notary_office_number: [20],
  notary_letter_number: [20],
  notary_letter_date: [20],
  lease_contract_number: [21],
  lease_contract_date: [21],
};

/**
 * SanadBan (DeedFlow) - Interactive Logic Engine & Alpine.js Store
 * Full 21-Stage Housing Workflow & Interactive Scan Viewer
 */

// Persian Number to Words Converter Utility
const PersianNumberWords = {
  units: ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"],
  teens: [
    "ده",
    "یازده",
    "دوازده",
    "سیزده",
    "چهارده",
    "پانزده",
    "شانزده",
    "هفده",
    "هجده",
    "نوزده",
  ],
  tens: [
    "",
    "ده",
    "بیست",
    "سی",
    "چهل",
    "پنجاه",
    "شصت",
    "هفتاد",
    "هشتاد",
    "نود",
  ],
  hundreds: [
    "",
    "یکصد",
    "دویست",
    "سیصد",
    "چهارصد",
    "پانصد",
    "ششصد",
    "هفتصد",
    "هشتصد",
    "نهصد",
  ],
  scales: ["", "هزار", "میلیون", "میلیارد", "تریلیون"],

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

    return parts.join(" و ");
  },

  toWords(num) {
    if (!num || isNaN(num) || num === 0) return "صفر ریال";
    num = Math.floor(Number(num));
    if (num < 0) return "منفی " + this.toWords(-num);

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

    return chunks.join(" و ") + " ریال";
  },

  formatThousand(val) {
    if (!val && val !== 0) return "";
    return val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  },

  toPersianDigits(val) {
    if (val === null || val === undefined) return "";
    const faDigits = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
    return String(val).replace(/[0-9]/g, (d) => faDigits[d]);
  },
};

// Official 22-Stage Housing Workflow Configuration (Stages 1 to 22)
const STAGES_22 = [
  {
    id: 1,
    unit: "brokerage",
    role: "کارشناس ثبت اطلاعات متقاضی و واحد انتخابی",
    title: "ورود اطلاعات انتخاب واحد (پروژه، متقاضی و همسر)",
    category: "کارگزاری مسکن",
  },
  {
    id: 2,
    unit: "brokerage",
    role: "کارشناس اطلاعات و عرصه",
    title: "ورود اطلاعات ثبتی عرصه، پلاک، کد نوسازی و قیمت تمام‌شده",
    category: "کارگزاری مسکن",
  },
  {
    id: 3,
    unit: "directorate",
    role: "کارشناس بررسی فرم ج (عالمی)",
    title: "بررسی فرم جیم",
    category: "استعلامات و تسهیلات",
  },
  {
    id: 4,
    unit: "directorate",
    role: "کارشناس برنامه ریزی مسکن (تسهیلات و برآورد)",
    title: "ورود وام صندوق، نامه پیمانکار، وام دهک و تعیین آورده نقدی",
    category: "استعلامات و تسهیلات",
  },
  {
    id: 5,
    unit: "directorate",
    role: "کارشناس برنامه ریزی مسکن (اطلاع‌رسانی آورده)",
    title: "ارسال پیامک آورده نقدی متقاضی و ثبت تاریخ",
    category: "استعلامات و تسهیلات",
  },
  {
    id: 6,
    unit: "directorate",
    role: "کارشناس برنامه ریزی مسکن (معرفی به بانک)",
    title: "تایید آورده، خروجی اکسل و ثبت شماره نامه معرفی به بانک",
    category: "استعلامات و تسهیلات",
  },
  {
    id: 7,
    unit: "brokerage",
    role: "کارشناس تشکیل پرونده کارگزاری",
    title: "اسکن مدارک، دفترچه اقساط و ثبت شماره فرم ج",
    category: "کارگزاری مسکن",
  },
  {
    id: 8,
    unit: "brokerage",
    role: "کارشناس ممیزی و کنترل پرونده ره آزرم",
    title: "کارشناس ممیزی و کنترل پرونده ره آزرم (بازبینی و کنترل)",
    category: "کارگزاری مسکن",
  },
  {
    id: 9,
    unit: "brokerage",
    role: "مدیرعامل کارگزاری ",
    title: "تأیید و امضای مدیرعامل کارگزاری ره آزرم",
    category: "کارگزاری مسکن",
  },
  {
    id: 10,
    unit: "directorate",
    role: "کارشناس نهضت ملی مسکن و استعلام تسهیلات",
    title: "بررسی و انطباق کارشناس نهضت ملی مسکن",
    category: "تأییدات تخصصی اداره کل",
  },
  {
    id: 11,
    unit: "directorate",
    role: "کارشناس ثبت فرم ج اداره کل",
    title: "بررسی و ثبت فرم ج اداره کل",
    category: "تأییدات تخصصی اداره کل",
  },
  {
    id: 12,
    unit: "directorate",
    role: "کارشناس فنی و مهندسی",
    title: "بررسی کارشناس فنی و مهندسی",
    category: "تأییدات تخصصی اداره کل",
  },
  {
    id: 13,
    unit: "directorate",
    role: "کارشناس املاک",
    title: "بررسی کارشناس املاک و بارگذاری سند عرصه",
    category: "تأییدات تخصصی اداره کل",
  },
  {
    id: 14,
    unit: "directorate",
    role: "کارشناس بانک زمین",
    title: "بررسی کارشناس بانک زمین",
    category: "تأییدات تخصصی اداره کل",
  },
  {
    id: 15,
    unit: "directorate",
    role: "کارشناس حقوقی",
    title: "بررسی کارشناس حقوقی",
    category: "تأییدات تخصصی اداره کل",
  },
  {
    id: 16,
    unit: "directorate",
    role: "کارشناس ارزیابی",
    title: "کارشناس ارزیابی (تعیین اجاره، آماده‌سازی و فرم ارزیابی)",
    category: "ارزیابی و وصول",
  },
  {
    id: 17,
    unit: "brokerage",
    role: "کارشناس اخذ چک تسهیلات دهک",
    title: "دریافت و اسکن چک‌های تسهیلات وام دهک",
    category: "ارزیابی و وصول",
  },
  {
    id: 18,
    unit: "brokerage",
    role: "کارشناس وصول اجاره و آماده‌سازی",
    title: "دریافت نقد و اقساط آماده‌سازی و اجاره عرصه",
    category: "ارزیابی و وصول",
  },
  {
    id: 19,
    unit: "directorate",
    role: "کارشناس تسویه با پیمانکار",
    title: "بررسی کارشناس تسویه با پیمانکار",
    category: "تسویه و خاتمه",
  },
  {
    id: 20,
    unit: "directorate",
    role: "کارشناس صدور نامه محضر",
    title: "تأیید نهایی فرم مراحل و صدور معرفی‌نامه محضر",
    category: "صدور و بایگانی",
  },
  {
    id: 21,
    unit: "directorate",
    role: "کارشناس قرارداد اجاره و چاپ",
    title: "اسکن قرارداد اجاره عرصه و چاپ فرم‌های مراحل و ارزیابی",
    category: "صدور و بایگانی",
  },
  {
    id: 22,
    unit: "directorate",
    role: "کارشناس بایگانی اداره کل",
    title: "بایگانی نهایی توسط اداره کل (قفل قطعی پرونده)",
    category: "صدور و بایگانی",
  },
];
const STAGES_21 = STAGES_22; // Backward compatibility alias

// Comprehensive 22-Stage Workflow Guidance (Stages 1 to 22)
const STAGE_GUIDANCE = {
  1: {
    actionTitle: "ورود اطلاعات متقاضی، همسر، واحد و پروژه",
    actionSummary:
      "واکشی استعلام پیش‌ثبت‌نام متقاضی، احراز زوجیت همسر، مشخصات سایت و پروژه و بارگذاری اسکن مدارک.",
    items: [
      "بررسی و ثبت کدملی، تاریخ تولد و مشخصات متقاضی",
      "تکمیل کامل مشخصات سجلی همسر (کدملی، شماره شناسنامه، تاریخ تولد)",
      "تایید مشخصات بلوک، طبقه و شماره واحد انتخابی",
      "بارگذاری تصویر اسکن کارت هوشمند ملی و برگه انتخاب واحد",
    ],
    targetSection: "#section-applicant",
  },
  2: {
    actionTitle: "کنترل پلاک ثبتی و ورود مبلغ تمام شده واحد",
    actionSummary:
      "تطبیق و ثبت اطلاعات بخش و پلاک ثبتی، و درج قیمت پایه ساخت بدون تسهیلات بانکی.",
    items: [
      "کنترل و ثبت نام بخش ثبتی، پلاک اصلی، مفروز، فرعی و شماره قطعه",
      "ورود مبلغ تمام‌شده واحد بر مبنای قرارداد کارگزاری بدون کسر وام",
      "مشاهده مبلغ به حروف فارسی و تایید درستی ارقام",
    ],
    targetSection: "#section-plot",
  },
  3: {
    actionTitle: "بررسی فرم ج",
    actionSummary:
      "استعلام سیستمی از سامانه جامع مسکن جهت احراز عدم استفاده قبلی متقاضی یا همسر از زمین یا تسهیلات دولتی.",
    items: [
      "استعلام سبزبودن فرم ج متقاضی مسکن",
      "استعلام وضعیت فرم ج همسر متقاضی",
      "ثبت نتیجه استعلام به صورت تاییدشده و سبز",
    ],
    targetSection: "#section-form-j",
  },
  4: {
    actionTitle: "ورود مبلغ وام صندوق، نامه پیمانکار و وام دهک",
    actionSummary:
      "تعیین مبالغ تسهیلات صندوق ملی، تخفیفات پیمانکار و وام ویژه دهک‌های درآمدی.",
    items: [
      "درج رقم مصوب تسهیلات صندوق ملی مسکن (ریال)",
      "ثبت مبلغ کسر یا تخفیف ابلاغی پیمانکار سازنده (ریال)",
      "ورود مبلغ تسهیلات ویژه دهک متقاضی (ریال)",
    ],
    targetSection: "#section-loans",
  },
  5: {
    actionTitle: "ارسال پیامک تعیین آورده نقدی و ثبت تاریخ",
    actionSummary:
      "محاسبه سیستمی آورده نقدی مورد نیاز متقاضی و ارسال پیامک اطلاع‌رسانی تکمیل واریزی.",
    items: [
      "بررسی محاسبه مانده بدهی آورده نقدی متقاضی",
      "ارسال پیامک اعلام واریزی به متقاضی و ثبت تاریخ",
    ],
    targetSection: "#section-equity",
  },
  6: {
    actionTitle: "تایید واریز و ثبت نامه معرفی به بانک",
    actionSummary:
      "ثبت اطلاعات معرفی‌نامه رسمی متقاضی به بانک عامل جهت تقسیط تسهیلات ساخت مسکن.",
    items: [
      "درج شماره نامه رسمی معرفی به بانک",
      "ثبت تاریخ صدور نامه بانکی",
      "تعیین وضعیت ارسال به شعبه بانک",
    ],
    targetSection: "#section-bank",
  },
  7: {
    actionTitle: "اسکن مدارک، دفترچه اقساط و ثبت شماره فرم ج",
    actionSummary:
      "بارگذاری تصاویر اسکن‌شده مدارک هویتی، دفترچه اقساط بانکی و ثبت شماره رسمی فرم ج.",
    items: [
      "بارگذاری تصویر صفحات دفترچه اقساط بانکی",
      "ثبت شماره فرم ج و کنترل کامل بودن مدارک پرونده",
      "تولید لیبل پوشه با شماره بایگانی پرونده",
    ],
    targetSection: "#section-docs-installment",
  },
  8: {
    actionTitle: "بازبینی، ممیزی و کنترل پرونده ره آزرم",
    actionSummary:
      "کنترل و بازبینی دقیق بخش‌های ۱، ۲ و ۴، مدارک هویتی، پلاک‌های ثبتی و قیمت تمام‌شده بدون وام پیش از ارسال به مدیر کارگزاری.",
    items: [
      "کنترل تکمیل بخش ثبتی، پلاک اصلی، مفروز، فرعی، شماره قطعه و قیمت تمام‌شده بدون وام",
      "کنترل و تطبیق فیلدهای بخش‌های ۱، ۲ و ۴ و مدارک هویتی متقاضی و همسر",
      "تایید ممیزی جهت ارسال به مدیرعامل کارگزاری ره آزرم",
    ],
    targetSection: "#section-plot",
  },
  9: {
    actionTitle: "تأیید و امضای مدیرعامل کارگزاری ره آزرم",
    actionSummary:
      "بازبینی کامل بخش‌های ۱، ۲ و ۴ پرونده، بررسی صحت مبالغ و مدارک کارگزاری، و تایید نهایی توسط مدیرعامل کارگزاری.",
    items: [
      "کنترل کلیه بخش‌های ۱، ۲ و ۴ و ضوابط اجرایی مراحل ۱ تا ۸",
      "بررسی تاییدیه مالی و گزارش ممیزی کارشناس ره آزرم",
      "ثبت امضای الکترونیک مدیرعامل کارگزاری جهت ارسال به اداره کل",
    ],
    targetSection: "#audit-timeline-section",
  },
  10: {
    actionTitle: "بررسی و تایید کارشناس نهضت ملی مسکن",
    actionSummary:
      "بررسی کارشناسی و انطباق سوابق متقاضی در طرح نهضت ملی مسکن و تایید احراز زوجیت و دفترچه‌های اقساط.",
    items: [
      "بررسی ضوابط طرح نهضت ملی مسکن و احراز تاهل",
      "تایید اصالت استعلام و دفترچه‌های اقساط",
      "ثبت امضای دیجیتال کارشناس نهضت ملی مسکن",
    ],
    targetSection: "#audit-timeline-section",
  },
  11: {
    actionTitle: "ثبت و بارگذاری استعلام فرم ج اداره کل",
    actionSummary:
      "تکمیل اطلاعات فرم «ج»، شماره پرسش‌نامه، کد کامپیوتری و بارگذاری اسکن تاییدیه رسمی اداره کل.",
    items: [
      "ثبت کد کامپیوتری و ویرایش/تایید اطلاعات فرم ج و شماره پرسش‌نامه",
      "بارگذاری اسکن تاییدیه نهایی فرم جیم صادره اداره کل",
      "تطبیق وضعیت سبز قطعی متقاضی و همسر و ثبت امضای دیجیتال",
    ],
    targetSection: "#section-form-j",
  },
  12: {
    actionTitle: "بررسی کارشناس اداره کل (فنی و مهندسی)",
    actionSummary:
      "کنترل نقشه‌های معماری، پایان‌کار و تایید مشخصات فنی (با قابلیت ویرایش پلاک ثبتی).",
    items: [
      "بررسی پایان‌کار ساختمانی و مشخصات فنی اعیانی",
      "کنترل متراژ مفید، مشاعات و ضرایب متعلقه",
      "ویرایش یا اصلاح پلاک ثبتی در صورت لزوم",
    ],
    targetSection: "#section-plot",
  },
  13: {
    actionTitle: "بررسی کارشناس اداره کل (املاک)",
    actionSummary:
      "تطبیق مشخصات ملک، بارگذاری تصویر سند رسمی تک‌برگ مالکیت عرصه و احراز عدم تعارض.",
    items: [
      "بارگذاری تصویر سند رسمی مالکیت عرصه پروژه",
      "تایید مالکیت دولت / اداره کل راه و شهرسازی",
      "ثبت امضای دیجیتال کارشناس املاک اداره کل",
    ],
    targetSection: "#section-plot",
  },
  14: {
    actionTitle: "بررسی و استعلام کارشناس بانک زمین",
    actionSummary:
      "استعلام و تطبیق موقعیت جغرافیایی و ثبتی ملک در سامانه جامع بانک زمین اداره کل.",
    items: [
      "بررسی کاداستر و مختصات UTM عرصه پروژه",
      "تطبیق با بانک اطلاعات زمین سازمان ملی مسکن",
      "ثبت امضای دیجیتال کارشناس بانک زمین",
    ],
    targetSection: "#audit-timeline-section",
  },
  15: {
    actionTitle: "بررسی و تایید کارشناس حقوقی اداره کل",
    actionSummary:
      "بررسی عدم موانع حقوقی، پرونده‌های مفتوح قضایی یا تعارضات مالکیتی و قراردادهای واگذاری.",
    items: [
      "استعلام وضعیت حقوقی و سوابق پرونده‌های قضایی زمین",
      "تایید عدم وجود معارض و منع قانونی انتقال سندی",
      "ثبت امضای دیجیتال کارشناس حقوقی اداره کل",
    ],
    targetSection: "#audit-timeline-section",
  },
  16: {
    actionTitle: "کارشناس ارزیابی (قدرالسهم، اجاره و آماده‌سازی)",
    actionSummary:
      "محاسبه قدرالسهم عرصه، اجاره سنواتی، اجاره سال جاری و هزینه‌های آماده‌سازی پروژه مسکونی.",
    items: [
      "ورود متراژ دقیق قدرالسهم متقاضی از عرصه (متر مربع)",
      "محاسبه و درج مبلغ اجاره سنوات گذشته و سال جاری (ریال)",
      "تولید فرم رسمی ارزیابی و تعیین هزینه آماده‌سازی",
    ],
    targetSection: "#section-valuation",
  },
  17: {
    actionTitle: "دریافت و اسکن چک‌های تسهیلات دهک",
    actionSummary:
      "دریافت، ثبت و بارگذاری اسکن چک‌های صیادی تسهیلات دهک درآمدی متقاضی.",
    items: [
      "دریافت چک‌های صیادی تسهیلات دهک درآمدی",
      "ثبت مشخصات و مبالغ و سررسید چک‌ها",
      "بارگذاری اسکن چک‌ها و صدور رسید تحویل چک",
    ],
    targetSection: "#section-checks",
  },
  18: {
    actionTitle: "دریافت نقد و اقساط آماده‌سازی و اجاره عرصه",
    actionSummary:
      "دریافت وجه نقد اجاره و آماده‌سازی (۲۰٪ نقد و ۸۰٪ اقساط) و بارگذاری فیش‌ها و چک‌ها.",
    items: [
      "دریافت فیش واریز نقدی اجاره عرصه و پیش‌پرداخت آماده‌سازی",
      "دریافت چک‌های اقساط ۸۰٪ آماده‌سازی",
      "بارگذاری اسکن و تایید وصول مالی",
    ],
    targetSection: "#section-checks",
  },
  19: {
    actionTitle: "بررسی کارشناس تسویه با پیمانکار",
    actionSummary:
      "بررسی صورت‌جلسه تسویه قطعی پیمانکار با قابلیت ویرایش مراحل ۲ و ۴.",
    items: [
      "بررسی اسناد تسویه حساب مالی با شرکت پیمانکار سازنده",
      "امکان بازبینی و اصلاح مبالغ مرحله ۲ و ۴",
      "ثبت امضای دیجیتال کارشناس تسویه پیمانکار",
    ],
    targetSection: "#audit-timeline-section",
  },
  20: {
    actionTitle: "تأیید نهایی فرم مراحل و صدور نامه محضر",
    actionSummary:
      "بررسی و تایید نهایی فرم مراحل و صدور رسمی نامه معرفی متقاضی به دفتر اسناد رسمی.",
    items: [
      "تایید نهایی فرم مراحل و امضاها",
      "صدور و ثبت شماره و تاریخ نامه محضر",
      "تولید معرفی‌نامه رسمی دفتر اسناد رسمی",
    ],
    targetSection: "#section-notary",
  },
  21: {
    actionTitle: "اسکن قرارداد اجاره عرصه و چاپ فرم‌های رسمی",
    actionSummary:
      "ثبت شماره و تاریخ سند قرارداد اجاره، بارگذاری اسکن آن و چاپ فرم رسمی مراحل و فرم ارزیابی.",
    items: [
      "ثبت شماره سند قرارداد اجاره و تاریخ قرارداد",
      "اسکن و بارگذاری اجباری صفحه قرارداد اجاره عرصه",
      "چاپ فرم رسمی مراحل و فرم ارزیابی تکمیل‌شده",
    ],
    targetSection: "#section-lease-contract",
  },
  22: {
    actionTitle: "مشاهده فرم نهایی و بایگانی قطعی پرونده",
    actionSummary:
      "رویت شناسنامه جامع سندی، اعمال قفل سیستمی دائم و اتمام فرآیند در آرشیو قطعی اداره کل.",
    items: [
      "بررسی خلاصه سوابق و کلیه امضاهای مراحل پرونده",
      "چاپ برگه خلاصه نهایی و رسیدهای مربوطه",
      "فشردن دکمه «تایید و بایگانی قطعی پرونده» جهت بایگانی نهایی",
    ],
    targetSection: "#audit-timeline-section",
  },
};

// Alpine.js Application Store & Controller
document.addEventListener("alpine:init", () => {
  Alpine.data("sanadbanApp", () => ({
    // Pipeline State
    currentStage: 1,
    status: "IN_PROGRESS",
    returnReason: "",
    returnBy: "",
    returnFromStage: null,
    stages: STAGES_22,
    archiveNumber: null,
    isLoaded: false,
    isLocked: false,
    userCanAction: true,
    isViewOnly: false,
    isChief: false,
    showRoadmap: false,
    stageDetails: {},
    selectedCategory: "all",
    attachmentViewMode: "album",
    todayDate: "",

    // Active Tab Navigation
    tab: "form",
    moreOpen: false,
    simpleMode:
      document.documentElement.getAttribute("data-ui-mode") === "simple",

    get isRedJ() {
      return Boolean(
        this.isRedFormJ ||
        (this.form &&
          this.form.applicant_form_j_status &&
          this.form.applicant_form_j_status.includes("قرمز")) ||
        (this.form &&
          this.form.spouse_form_j_status &&
          this.form.spouse_form_j_status.includes("قرمز")),
      );
    },

    // Sections shown in simple mode: applicant (stage 1) + sections of the user's own stages
    get simpleVisibleSections() {
      const ids = new Set(["section-applicant"]);
      const allowed = this.userAllowedStages;
      const restricted =
        Array.isArray(allowed) &&
        allowed.length > 0 &&
        !this.isSuperuser &&
        !this.isChief;
      const stages = restricted
        ? allowed.map(Number)
        : [Number(this.currentStage)];
      Object.keys(SECTION_STAGE_MAP).forEach((sid) => {
        if (SECTION_STAGE_MAP[sid].some((s) => stages.includes(s)))
          ids.add(sid);
      });
      return ids;
    },

    get simpleFocusStage() {
      const allowed = Array.isArray(this.userAllowedStages)
        ? this.userAllowedStages
        : [];
      const numeric = allowed
        .map(Number)
        .filter((n) => !Number.isNaN(n) && n > 0);
      if (numeric.length > 0) {
        const cur = Number(this.currentStage);
        if (numeric.includes(cur)) return cur;
        return numeric[0];
      }
      return Number(this.currentStage) || 1;
    },

    applySimpleModeVisibility() {
      const visible = this.simpleVisibleSections;
      const on = Boolean(
        this.simpleMode ||
        document.documentElement.getAttribute("data-ui-mode") === "simple",
      );
      document
        .querySelectorAll("#form .form-card, .form-sections-wrapper .form-card")
        .forEach((el) => {
          if (!el || !el.id) return;
          el.classList.toggle("sb-simple-hidden", on && !visible.has(el.id));
        });
    },

    go(t) {
      if (t === "scans") {
        this.toggleAlbumPopup();
        return;
      }
      this.tab = t;
      if (location.hash !== "#" + t) {
        history.replaceState(null, "", "#" + t);
      }
      const syncTabScroll = () => {
        if (document.body && document.body.scrollTop) {
          document.body.scrollTop = 0;
        }
        const anchor =
          document.getElementById("dt-tabs-anchor") ||
          document.querySelector(".dt-tabs");
        if (!anchor) return;
        const anchorTop = Math.max(
          0,
          anchor.getBoundingClientRect().top + window.pageYOffset - 80,
        );
        const maxScroll = Math.max(
          0,
          document.documentElement.scrollHeight - window.innerHeight,
        );
        if (window.pageYOffset > anchorTop + 12) {
          window.scrollTo({
            top: Math.max(0, Math.min(anchorTop, maxScroll)),
            behavior: "auto",
          });
        } else if (window.pageYOffset > maxScroll) {
          window.scrollTo({ top: maxScroll, behavior: "auto" });
        }
      };
      if (typeof this.$nextTick === "function") {
        this.$nextTick(() => requestAnimationFrame(syncTabScroll));
      } else {
        requestAnimationFrame(syncTabScroll);
      }
    },

    // Modals
    showAlbumPopup: false,
    isAlbumMinimized: false,
    isAlbumMaximized: false,
    openAlbumPopup() {
      this.showAlbumPopup = true;
      this.isAlbumMinimized = false;
    },
    closeAlbumPopup() {
      this.showAlbumPopup = false;
      this.isAlbumMinimized = false;
    },
    toggleAlbumPopup() {
      if (this.showAlbumPopup && !this.isAlbumMinimized) {
        this.showAlbumPopup = false;
      } else {
        this.showAlbumPopup = true;
        this.isAlbumMinimized = false;
      }
    },
    toggleMinimizeAlbumPopup() {
      this.isAlbumMinimized = !this.isAlbumMinimized;
    },
    toggleMaximizeAlbumPopup() {
      this.isAlbumMaximized = !this.isAlbumMaximized;
    },
    showSignatureModal: false,
    showArchiveIssuedModal: false,
    archiveCopied: false,
    issuedArchiveInfo: {
      archive_number: "",
      full_name: "",
      national_id: "",
      new_stage: 8,
      redirect_url: "",
    },
    showReturnModal: false,
    showScanViewerModal: false,
    showGuidanceModal: false,
    albumPage: 1,
    albumPerPage: 4,
    attachmentViewMode: "album",
    activeScanIndex: 0,
    showUploadModal: false,
    isScanning: false,
    isUploadingScan: false,
    scanUploadProgress: 0,
    scanUploadPhase: "",
    scanUploadStatus: "",
    scanUploadDetails: "",
    isUploadingInlineScan: false,
    inlineUploadProgress: 0,
    projectsList: [],
    projectsCatalog: { projects: [], sites: [], banks: [], branches: [] },
    landRateInfo: null,
    isSaving: false,
    showToast: false,
    toastMessage: "",
    toastType: "success",

    // Upload & Scanner Form State
    draggedIdx: null,
    dragOverIdx: null,
    uploadForm: {
      title: "",
      doc_type: "NATIONAL_ID",
      fileName: "",
      preview_url: "",
      rawFile: null,
    },

    // Return Routing
    selectedReturnStage: 1,
    returnNotes: "",

    // Signature Form
    signerPin: "",
    signAgreement: false,

    // Scan Viewer & Lightbox State
    activeScan: {
      id: null,
      type: "",
      title: "",
      fileName: "",
      uploader: "",
      uploadDate: "",
      stage: 1,
      sha256: "",
      zoom: 1,
      rotation: 0,
    },

    // Form Data - Merged 45+ Fields Matrix
    form: {
      // Stage 1 Fields
      first_name: "",
      last_name: "",
      full_name: "",
      father_name: "",
      national_id: "",
      birth_date: "",
      applicant_phone: "",
      applicant_address: "",
      applicant_postal_code: "",
      applicant_landline_phone: "",
      applicant_id_serial: "",
      selection_rank: null,
      form_j_questionnaire_number: "",
      form_j_number: "",
      computer_code: "",
      applicant_form_j_status: "سبز (استعلام شده)",
      applicant_form_j_directorate_status: "تایید نهایی اداره کل",
      applicant_form_j_red_description: "",
      spouse_first_name: "",
      spouse_last_name: "",
      spouse_full_name: "",
      spouse_father_name: "",
      spouse_national_id: "",
      spouse_birth_date: "",
      spouse_id_number: "",
      spouse_id_serial: "",
      spouse_birth_place: "",
      spouse_form_j_status: "سبز (استعلام شده)",
      spouse_form_j_directorate_status: "تایید نهایی اداره کل",
      spouse_form_j_red_description: "",
      marital_status: "متاهل ",
      is_married_confirmed: true,
      decile: 1,
      site: "",
      project: "",
      construction_type: "آپارتمانی",
      block_name: "",
      block_code: "",
      floor_number: 1,
      unit_number: 1,
      unit_code: "",
      bedroom_count: 2,
      unit_direction: "",
      net_unit_area: 0,
      common_area: 0,
      total_area: 0,
      unit_area: 0,
      storage_number: null,
      storage_area: 0,
      parking_number: null,
      parking_area: 0,

      // Stage 2: Plot & Registry
      registration_section: "",
      main_plaque: null,
      separated_plaque: null,
      sub_plaque: null,
      plot_number: null,

      // Stage 3: Base Cost & Bank Loan Amount (Default 650M Tomans, can be 550M or custom)
      base_cost_without_loan: 0,
      bank_loan_amount: 0,

      // Stage 6: Fund Loan Amount
      fund_loan_amount: 0,

      // Stage 7: Contractor Letter Amount
      contractor_letter_amount: 0,

      // Stage 8: Decile Loan Amount
      decile_loan_amount: 0,

      // Stage 9: Applicant Cash Equity
      applicant_equity: 0,
      is_sms_sent: false,
      sms_sent_at: "",

      // Stage 10: Confirmation of equity funding
      is_equity_funded: false,

      // Stage 11: Bank Letter
      bank_letter_number: "",
      bank_letter_date: "",

      // Stage 19: Valuation Fields
      total_land_share: 0,
      past_years_rent: 0,
      current_year_rent: 0,
      land_lease_year: "",
      preparation_cost: 0,

      // Stage 18: BankCheckTracker & TashilatCheck Fields (وام دهک، چک‌ها، آماده‌سازی و اجاره)
      decile_loan_bank: "",
      decile_bank_letter_number: "",
      decile_bank_letter_date: "",
      supported_institution: "هیچکدام",
      check_count: 0,
      check_amount: 0,
      last_check_amount: 0,
      total_check_amount: 0,
      commitment_number: "",
      commitment_date: "",
      check_entries: [],

      // TashilatCheck: Rent & 20%/80% Preparation
      tenant_price: 0,
      tenant_code: "",
      cash_preparation_amount: 0,
      prepayment_code: "",
      non_cash_preparation_amount: 0,
      preparation_service_fee: 0,
      preparation_check_count: 0,
      total_preparation_check_amount: 0,
      preparation_check_entries: [],
      rah_letter: "",
      rah_letter_date: "",
      deed_number: "",
      deed_date: "",
      is_land_deed_confirmed: false,
      notary_office_number: "",
      notary_letter_number: "",
      notary_letter_date: "",
      lease_contract_number: "",
      lease_contract_date: "",
      is_cash_rent_confirmed: false,
      cash_rent_confirmed_by: "",
      cash_rent_confirmed_at: "",
      is_decile_loan_confirmed: false,
      loan_checks_confirmed_by: "",
      loan_checks_confirmed_at: "",
      is_preparation_checks_confirmed: false,
      prep_checks_confirmed_by: "",
      prep_checks_confirmed_at: "",
      visit_date: "",
      visited_by: "",
      visited_at: "",
      is_loan_visited: false,
      loan_visit_date: "",
      loan_visited_by: "",
      loan_visited_at: "",
      is_prep_visited: false,
      prep_visit_date: "",
      prep_visited_by: "",
      prep_visited_at: "",
      is_loan_sent_to_directorate: false,
      loan_directorate_sent_date: "",
      loan_directorate_sent_by: "",
      loan_directorate_sent_at: "",
      loan_directorate_shipment_code: "",
      is_prep_sent_to_directorate: false,
      prep_directorate_sent_date: "",
      prep_directorate_sent_by: "",
      prep_directorate_sent_at: "",
      prep_directorate_shipment_code: "",
    },

    // Scanned Documents (populated dynamically from database without ghost record flicker)
    attachments: [],

    // Audit Trail / History (populated dynamically from database)
    auditLogs: [],

    // Field-level Change Audit Trail
    fieldChanges: [],
    stageSignatures: {},
    auditActiveTab: "stages", // 'stages' or 'fields'
    showAuditDetails: true, // Expanded by default so audit logs load immediately
    stepperExpanded: false, // 21-step progress bar expansion toggle

    // Deletion and Archive State
    isDeleted: false,
    deletionReason: "",
    deletedBy: "",
    deletedAt: "",
    showDeleteModal: false,
    deleteReason: "",

    // Red Form J Disqualification State
    isRejected: false,
    isRedFormJ: false,
    rejectionLetterNumber: "",
    rejectionLetterDate: "",
    rejectionReason: "",
    rejectedBy: "",
    showRedRejectionModal: false,
    redLetterNumber: "",
    redLetterDate: "",
    redLetterReason: "",

    // Red Form J Return for Correction State
    showRedReturnModal: false,
    redReturnStage: 0,
    redReturnNotes: "",
    redResetFormJ: true,

    // Check Admin Authorization (Superuser, Chief, or Kargozari Check Admin)
    isCheckAdmin: false,
    canManageDirectorateShipments: false,
    userAllowedStages: "all",
    isSuperuser: false,
    signaturesList: [],

    // Check Generator State (BankCheckTracker intelligent generation)
    checkGenerator: {
      count: 4,
      startDate: "",
      interval: "1year",
    },

    // Preparation Check Generator State (tashilatCheck intelligent 6-month installment generation)
    prepCheckGenerator: {
      count: 3,
      startDate: "",
      interval: "6months",
    },

    // Interactive Persian Date Picker Modal State
    datePickerModal: {
      isOpen: false,
      targetField: "",
      title: "انتخاب تاریخ شمسی",
      year: 1405,
      month: 7,
      day: 30,
      yearsList: [
        1400, 1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408, 1409, 1410, 1411,
        1412, 1413, 1414, 1415,
      ],
      monthsList: [
        { num: 1, name: "فروردین", days: 31 },
        { num: 2, name: "اردیبهشت", days: 31 },
        { num: 3, name: "خرداد", days: 31 },
        { num: 4, name: "تیر", days: 31 },
        { num: 5, name: "مرداد", days: 31 },
        { num: 6, name: "شهریور", days: 31 },
        { num: 7, name: "مهر", days: 30 },
        { num: 8, name: "آبان", days: 30 },
        { num: 9, name: "آذر", days: 30 },
        { num: 10, name: "دی", days: 30 },
        { num: 11, name: "بهمن", days: 30 },
        { num: 12, name: "اسفند", days: 29 },
      ],
    },

    init() {
      // 1. Sync active tab from URL hash (#form)
      const validTabs = ["form", "map", "history"];
      const currentHash = location.hash.slice(1);
      if (validTabs.includes(currentHash)) {
        this.tab = currentHash;
      }
      window.addEventListener("hashchange", () => {
        const h = location.hash.slice(1);
        if (validTabs.includes(h)) {
          this.tab = h;
        }
      });

      // 2. Set Persian Today Date dynamically
      this.todayDate = this.getTodayJalaliDisplay();

      // Simple / advanced mode (حالت ساده / پیشرفته)
      window.SanadbanAppInstance = this;
      this.simpleMode = window.SanadbanUiMode
        ? window.SanadbanUiMode.get() === "simple"
        : true;
      window.addEventListener("sanadban-ui-mode-changed", (e) => {
        this.simpleMode = Boolean(e.detail && e.detail.mode === "simple");
        this.applySimpleModeVisibility();
      });
      this.$watch("simpleMode", () => {
        this.applySimpleModeVisibility();
      });
      this.$nextTick(() => {
        this.applySimpleModeVisibility();
      });

      // 2. Read real server data injected from database
      const serverDataEl = document.getElementById("dossier-server-json");
      if (serverDataEl && serverDataEl.textContent.trim()) {
        try {
          const serverData = JSON.parse(serverDataEl.textContent);
          if (serverData.archive_number)
            this.archiveNumber = serverData.archive_number;
          if (typeof serverData.current_stage !== "undefined")
            this.currentStage = Number(serverData.current_stage);
          if (typeof serverData.is_locked !== "undefined")
            this.isLocked = Boolean(serverData.is_locked);
          if (serverData.status) this.status = serverData.status;
          if (serverData.return_reason)
            this.returnReason = serverData.return_reason;
          if (serverData.return_by) this.returnBy = serverData.return_by;
          if (
            typeof serverData.return_from_stage !== "undefined" &&
            serverData.return_from_stage !== null
          )
            this.returnFromStage = serverData.return_from_stage;
          if (typeof serverData.user_can_action !== "undefined")
            this.userCanAction = Boolean(serverData.user_can_action);
          if (typeof serverData.is_view_only !== "undefined")
            this.isViewOnly = Boolean(serverData.is_view_only);
          if (typeof serverData.is_chief !== "undefined")
            this.isChief = Boolean(serverData.is_chief);
          if (typeof serverData.is_superuser !== "undefined")
            this.isSuperuser = Boolean(serverData.is_superuser);
          if (typeof serverData.is_check_admin !== "undefined")
            this.isCheckAdmin = Boolean(serverData.is_check_admin);
          if (typeof serverData.can_manage_directorate_shipments !== "undefined")
            this.canManageDirectorateShipments = Boolean(serverData.can_manage_directorate_shipments);
          if (typeof serverData.user_allowed_stages !== "undefined")
            this.userAllowedStages = serverData.user_allowed_stages;
          if (typeof serverData.is_superuser !== "undefined")
            this.isSuperuser = Boolean(serverData.is_superuser);
          if (Array.isArray(serverData.signatures_list))
            this.signaturesList = serverData.signatures_list;
          if (typeof serverData.is_rejected !== "undefined")
            this.isRejected = Boolean(serverData.is_rejected);
          if (typeof serverData.is_red_form_j !== "undefined")
            this.isRedFormJ = Boolean(serverData.is_red_form_j);
          if (serverData.stage_details)
            this.stageDetails = serverData.stage_details;
          if (serverData.land_rate_info)
            this.landRateInfo = serverData.land_rate_info;
          if (serverData.projects_catalog) {
            this.projectsCatalog = serverData.projects_catalog;
            if (Array.isArray(serverData.projects_catalog.projects)) {
              this.projectsList = serverData.projects_catalog.projects;
              window.ALL_PROJECTS = this.projectsList;
            }
          }
          if (serverData.rejection_letter_number)
            this.rejectionLetterNumber = serverData.rejection_letter_number;
          if (serverData.rejection_letter_date)
            this.rejectionLetterDate = serverData.rejection_letter_date;
          if (serverData.rejection_reason)
            this.rejectionReason = serverData.rejection_reason;
          if (serverData.rejected_by) this.rejectedBy = serverData.rejected_by;
          if (typeof serverData.is_deleted !== "undefined")
            this.isDeleted = Boolean(serverData.is_deleted);
          if (serverData.deletion_reason)
            this.deletionReason = serverData.deletion_reason;
          if (serverData.deleted_by)
            this.deletedBy = serverData.deleted_by;
          if (serverData.deleted_at)
            this.deletedAt = serverData.deleted_at;
          if (serverData.form) {
            this.form = Object.assign({}, this.form, serverData.form);
          }
          const canonicalFormJ = String(
            this.form.form_j_number ||
              this.form.form_j_questionnaire_number ||
              "",
          ).trim();
          this.form.form_j_number = canonicalFormJ;
          this.form.form_j_questionnaire_number = canonicalFormJ;
          if (Array.isArray(serverData.attachments)) {
            this.attachments = serverData.attachments;
          }
          if (Array.isArray(serverData.audit_logs)) {
            this.auditLogs = serverData.audit_logs;
          }
          if (Array.isArray(serverData.field_changes)) {
            this.fieldChanges = serverData.field_changes;
          }
          if (serverData.stage_signatures) {
            this.stageSignatures = serverData.stage_signatures;
          }
        } catch (e) {
          console.error("Failed to parse server dossier data:", e);
        }
      }
      this.syncConstructionTypeBySite();
      this.syncUnitDirectionByConstruction();
      this.recalculateEquity();

      this.$watch("form.site", (val) => {
        this.syncConstructionTypeBySite(val);
        this.syncUnitDirectionByConstruction();
      });

      this.$watch("form.construction_type", () => {
        this.syncUnitDirectionByConstruction();
      });

      // Two-way sync between "شماره رسمی فرم «ج»" (form_j_number) and "شماره پرسش‌نامه فرم ج" (form_j_questionnaire_number)
      this.$watch("form.form_j_number", (val) => {
        const nextVal = val == null ? "" : String(val);
        if (this.form.form_j_questionnaire_number !== nextVal) {
          this.form.form_j_questionnaire_number = nextVal;
        }
      });
      this.$watch("form.form_j_questionnaire_number", (val) => {
        const nextVal = val == null ? "" : String(val);
        if (this.form.form_j_number !== nextVal) {
          this.form.form_j_number = nextVal;
        }
      });

      if (
        !this.form.check_entries ||
        !Array.isArray(this.form.check_entries) ||
        this.form.check_entries.length === 0
      ) {
        this.form.check_entries = [
          {
            row_number: 1,
            cash_date: "",
            check_amount: 0,
            check_sayadi_code: "",
            bank_name: "",
          },
        ];
      }
      this.recalculateChecks();

      // Initialize Check Generator defaults from existing data or +1 year from today
      const firstCheckDate =
        this.form.check_entries &&
        this.form.check_entries[0] &&
        this.form.check_entries[0].cash_date
          ? this.form.check_entries[0].cash_date
          : "";
      this.checkGenerator.startDate =
        firstCheckDate || this.addYearsToJalali(this.getTodayJalali(), 1);
      if (this.form.check_entries && this.form.check_entries.length > 0) {
        this.checkGenerator.count = this.form.check_entries.length;
      }

      // Initialize Preparation Check entries for tashilatCheck (آماده‌سازی)
      if (
        !this.form.preparation_check_entries ||
        !Array.isArray(this.form.preparation_check_entries) ||
        this.form.preparation_check_entries.length === 0
      ) {
        this.form.preparation_check_entries = [
          {
            row_number: 1,
            cash_date: "",
            check_amount: 0,
            check_sayadi_code: "",
            bank_name: "",
          },
        ];
      }
      this.recalculatePrepChecks();

      // Initialize Preparation Check Generator defaults (+6 months from today, or first prep check date)
      const firstPrepDate =
        this.form.preparation_check_entries &&
        this.form.preparation_check_entries[0] &&
        this.form.preparation_check_entries[0].cash_date
          ? this.form.preparation_check_entries[0].cash_date
          : "";
      this.prepCheckGenerator.startDate =
        firstPrepDate || this.addSixMonthsCustomJalali(this.getTodayJalali());
      if (
        this.form.preparation_check_entries &&
        this.form.preparation_check_entries.length > 0
      ) {
        this.prepCheckGenerator.count =
          this.form.preparation_check_entries.length;
      }
      this.isLoaded = true;
    },

    getTodayJalali() {
      try {
        const parts = new Intl.DateTimeFormat("en-US-u-ca-persian", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }).formatToParts(new Date());
        const y = parts.find((p) => p.type === "year")?.value || "1405";
        const m = parts.find((p) => p.type === "month")?.value || "07";
        const d = parts.find((p) => p.type === "day")?.value || "30";
        return `${y}/${m}/${d}`;
      } catch (e) {
        return "1405/07/30";
      }
    },

    getTodayJalaliDisplay() {
      try {
        const formatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
        });
        const parts = formatter
          .formatToParts(new Date())
          .reduce((acc, p) => ({ ...acc, [p.type]: p.value }), {});
        return `${parts.weekday} ${parts.day} ${parts.month} ${parts.year}`;
      } catch (e) {
        return new Date().toLocaleDateString("fa-IR");
      }
    },

    isJalaliLeapYear(year) {
      return [1, 5, 9, 13, 17, 22, 26, 30].includes(Number(year) % 33);
    },

    getDaysInJalaliMonth(year, month) {
      const m = Number(month);
      if (m <= 6) return 31;
      if (m <= 11) return 30;
      return this.isJalaliLeapYear(year) ? 30 : 29;
    },

    normalizeJalaliDigits(str) {
      if (!str) return "";
      return String(str)
        .replace(/[۰٠]/g, "0")
        .replace(/[۱١]/g, "1")
        .replace(/[۲٢]/g, "2")
        .replace(/[۳٣]/g, "3")
        .replace(/[۴٤]/g, "4")
        .replace(/[۵٥]/g, "5")
        .replace(/[۶٦]/g, "6")
        .replace(/[۷٧]/g, "7")
        .replace(/[۸٨]/g, "8")
        .replace(/[۹٩]/g, "9");
    },

    parseJalaliDate(dateStr) {
      if (!dateStr) return null;
      const clean = this.normalizeJalaliDigits(dateStr)
        .replace(/[-.]/g, "/")
        .trim();
      const parts = clean.split("/");
      if (parts.length === 3) {
        const y = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        const d = parseInt(parts[2], 10);
        if (!isNaN(y) && !isNaN(m) && !isNaN(d)) {
          return { year: y, month: m, day: d };
        }
      }
      return null;
    },

    formatJalaliDate(y, m, d) {
      const sy = String(y);
      const sm = String(m).padStart(2, "0");
      const sd = String(d).padStart(2, "0");
      return `${sy}/${sm}/${sd}`;
    },

    addYearsToJalali(dateStr, yearsToAdd) {
      const parsed =
        this.parseJalaliDate(dateStr) ||
        this.parseJalaliDate(this.getTodayJalali());
      const newYear = parsed.year + Number(yearsToAdd);
      const month = parsed.month;
      let day = parsed.day;
      const maxDay = this.getDaysInJalaliMonth(newYear, month);
      if (day > maxDay) day = maxDay;
      return this.formatJalaliDate(newYear, month, day);
    },

    advanceJalaliDate(startDateStr, index, interval) {
      if (index === 0) {
        const p = this.parseJalaliDate(startDateStr);
        return p
          ? this.formatJalaliDate(p.year, p.month, p.day)
          : this.getTodayJalali();
      }
      if (interval === "6months") {
        const p =
          this.parseJalaliDate(startDateStr) ||
          this.parseJalaliDate(this.getTodayJalali());
        const totalMonths = p.month - 1 + index * 6;
        const newYear = p.year + Math.floor(totalMonths / 12);
        const newMonth = (totalMonths % 12) + 1;
        let day = p.day;
        const maxDay = this.getDaysInJalaliMonth(newYear, newMonth);
        if (day > maxDay) day = maxDay;
        return this.formatJalaliDate(newYear, newMonth, day);
      }
      return this.addYearsToJalali(startDateStr, index);
    },

    addSixMonthsCustomJalali(dateStr) {
      const parsed =
        this.parseJalaliDate(dateStr) ||
        this.parseJalaliDate(this.getTodayJalali());
      let year = parsed.year;
      let month = parsed.month + 6;
      let day = parsed.day;

      if (month > 12) {
        month -= 12;
        year += 1;
      }

      // Rule from tashilatCheck: Month 12 (Esfand) is avoided for installment checks -> cap to 11/30 (Bahman 30)
      if (month === 12) {
        month = 11;
        day = 30;
      } else if (month >= 7 && month <= 11) {
        if (day > 30) day = 30;
      } else {
        const maxD = this.getDaysInJalaliMonth(year, month);
        if (day > maxD) day = maxD;
      }

      return this.formatJalaliDate(year, month, day);
    },

    // Workflow stage is sticky - arbitrary jumping is prevented
    async selectStage(stgId) {
      this.triggerToast(
        "جابجایی دستی مرحله غیرفعال است. تغییر مرحله صرفاً از طریق تایید و امضای الکترونیک یا برگشت جهت اصلاح انجام می‌گیرد.",
        "warning",
      );
    },

    // Get CSRF Token reliably from DOM or cookie
    getCSRFToken() {
      const input = document.querySelector("[name=csrfmiddlewaretoken]");
      if (input && input.value) return input.value;
      const match = document.cookie.match(/(?:^|;)\\s*csrftoken=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : "";
    },

    // Save Dossier Draft Directly to Database
    async saveDossierDraft(notify = true) {
      if (this.isViewOnly || this.isLocked) {
        if (notify) this.triggerToast("امکان تغییر اطلاعات در حالت فقط خواندنی وجود ندارد.", "warning");
        return false;
      }
      this.isSaving = true;
      try {
        const csrfToken = this.getCSRFToken();
        const payload = Object.assign({}, this.form, {
          current_stage: this.currentStage,
        });
        const res = await fetch(`/dossier/${this.archiveNumber}/save/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify(payload),
        });

        if (res.ok) {
          const data = await res.json();
          if (notify) {
            this.triggerToast(
              data.message ||
                "کلیه تغییرات با موفقیت در پایگاه داده ذخیره گردید.",
              "success",
            );
          }
          if (typeof data.applicant_equity !== "undefined") {
            this.form.applicant_equity = data.applicant_equity;
          }
          if (typeof data.cash_rent_confirmed_by !== "undefined") {
            this.form.cash_rent_confirmed_by = data.cash_rent_confirmed_by;
            this.form.cash_rent_confirmed_at = data.cash_rent_confirmed_at;
          }
          if (typeof data.prep_checks_confirmed_by !== "undefined") {
            this.form.prep_checks_confirmed_by = data.prep_checks_confirmed_by;
            this.form.prep_checks_confirmed_at = data.prep_checks_confirmed_at;
          }
          if (typeof data.loan_checks_confirmed_by !== "undefined") {
            this.form.loan_checks_confirmed_by = data.loan_checks_confirmed_by;
            this.form.loan_checks_confirmed_at = data.loan_checks_confirmed_at;
          }
          if (Array.isArray(data.new_changes) && data.new_changes.length > 0) {
            this.fieldChanges.unshift(...data.new_changes);
          }
          return true;
        } else {
          const errData = await res.json().catch(() => ({}));
          this.triggerToast(
            errData.message || "خطا در ذخیره اطلاعات بر روی سرور.",
            "error",
          );
          return false;
        }
      } catch (err) {
        console.error("Save draft error:", err);
        this.triggerToast(
          "خطا در برقراری ارتباط با سرور پایگاه داده.",
          "error",
        );
        return false;
      } finally {
        this.isSaving = false;
      }
    },

    // Live Equity Auto-Calculation Formula
    getStageSignature(stageId) {
      if (!this.stageSignatures) return null;
      return (
        this.stageSignatures[stageId] ||
        this.stageSignatures[String(stageId)] ||
        null
      );
    },

    getStageSignerName(stageId) {
      const sig = this.getStageSignature(stageId);
      return sig && sig.actor ? sig.actor : "کارشناس اقدام";
    },

    getStageSignerDate(stageId) {
      const sig = this.getStageSignature(stageId);
      return sig && sig.date ? sig.date : "-";
    },

    setBankLoan(amount) {
      this.form.bank_loan_amount = Number(amount) || 0;
      this.recalculateEquity();
    },

    recalculateEquity() {
      const baseCost = Number(this.form.base_cost_without_loan) || 0;
      const fundLoan = Number(this.form.fund_loan_amount) || 0;
      const decileLoan = Number(this.form.decile_loan_amount) || 0;
      this.form.applicant_equity = Math.max(
        0,
        baseCost - (fundLoan + decileLoan),
      );
    },

    scrollToCategory(cat) {
      this.selectedCategory = cat || "all";
      const album = document.getElementById("attachments-card");
      if (album) {
        album.scrollIntoView({ behavior: "smooth", block: "start" });
        album.classList.add("pulse-highlight");
        setTimeout(() => album.classList.remove("pulse-highlight"), 1600);
      }
    },

    getFilteredAttachments() {
      // Unified album: All scans are thrown together in custom arranged order
      return this.attachments || [];
    },

    async rotateAttachment(item, degrees = 90) {
      if (this.isLocked || this.isViewOnly) {
        this.triggerToast("این پرونده در حالت فقط خواندنی است و امکان ویرایش تصویر وجود ندارد.", "warning");
        return;
      }
      try {
        const csrf =
          document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        const resp = await fetch(
          `/dossier/${this.archiveNumber}/attachment/${item.id}/edit-image/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrf,
            },
            body: JSON.stringify({ action: "rotate", degrees: degrees }),
          },
        );
        const res = await resp.json();
        if (res.status === "success") {
          item.preview_url =
            res.preview_url || item.preview_url + "?t=" + Date.now();
          if (res.new_sha256) item.sha256 = res.new_sha256;
          this.triggerToast(
            "چرخش تصویر با موفقیت اعمال و در لاگ امنیتی ثبت شد.",
            "success",
          );
        } else {
          alert("خطا در چرخش تصویر: " + (res.message || ""));
        }
      } catch (e) {
        alert("خطای ارتباط: " + e.message);
      }
    },

    async moveAttachment(item, direction) {
      if (this.isLocked) return;
      const idx = this.attachments.findIndex((a) => a.id === item.id);
      if (idx === -1) return;
      const targetIdx = idx + direction;
      if (targetIdx < 0 || targetIdx >= this.attachments.length) return;

      const swapItem = this.attachments[targetIdx];
      this.attachments[idx] = swapItem;
      this.attachments[targetIdx] = item;
      this.attachments = [...this.attachments];

      const orderedIds = this.attachments.map((a) => a.id);
      try {
        const csrf =
          document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        await fetch(`/dossier/${this.archiveNumber}/attachment/reorder/`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify({ ordered_ids: orderedIds }),
        });
        this.triggerToast("ترتیب آلبوم مدارک با موفقیت بروزرسانی شد.", "info");
      } catch (e) {
        console.error("Reorder error:", e);
      }
    },

    openCropModal(item) {
      if (this.isLocked) return;
      this.cropTargetItem = item;
      this.isCropModalOpen = true;
    },

    getCategoryCount(cat) {
      if (!this.attachments) return 0;
      if (cat === "all") return this.attachments.length;
      if (cat === "identity")
        return this.attachments.filter(
          (a) =>
            a.type === "NATIONAL_ID" ||
            a.type === "SPOUSE_ID" ||
            a.type === "FORM_J" ||
            a.doc_type === "FORM_J",
        ).length;
      if (cat === "form_j")
        return this.attachments.filter(
          (a) => a.type === "FORM_J" || a.doc_type === "FORM_J",
        ).length;
      if (cat === "bank")
        return this.attachments.filter(
          (a) => a.type === "BANK_BOOKLET" || a.type === "BANK_LETTER",
        ).length;
      if (cat === "deed")
        return this.attachments.filter(
          (a) => a.type === "TITLE_DEED" || a.type === "UNIT_SELECTION",
        ).length;
      if (cat === "checks")
        return this.attachments.filter(
          (a) =>
            a.type === "LOAN_CHECK" ||
            a.type === "PREP_CHECK" ||
            a.type === "CHECK_RECEIPT",
        ).length;
      return 0;
    },



    // Stage 9: Send SMS simulation
    sendEquitySMS() {
      this.form.is_sms_sent = true;
      if (!this.form.sms_sent_date) {
        this.form.sms_sent_date = this.getTodayJalali();
      }
      this.form.sms_sent_at = this.getTodayJalali() + " 14:20";

      this.auditLogs.unshift({
        step: 9,
        fromStage: "مرحله ۹: تعیین مبلغ آورده",
        toStage: "مرحله ۹: ارسال پیامک",
        actor: "سیستم پیام‌رسان هوشمند مسکن یار",
        role: "سامانه اطلاع‌رسانی پیامکی",
        action: "SMS",
        actionLabel: "ارسال پیامک آورده متقاضی",
        timestamp: "1403/05/18 14:20:00",
        hash: "SHA256: sms88412" + Math.random().toString(36).substring(2, 8),
        notes: `پیامک به شماره همراه متقاضی ارسال شد: «متقاضی گرامی ${this.form.full_name}، مبلغ آورده نقدی شما ${this.formatNumber(this.form.applicant_equity)} ریال تعیین گردید. مهلت واریز: ۵ روز کاری.»`,
      });

      this.triggerToast(
        `پیامک ابلاغ مبلغ آورده (${this.formatNumber(this.form.applicant_equity)} ریال) با موفقیت به متقاضی ارسال شد.`,
        "success",
      );
    },

    // Stage 10: Confirm Equity Funding
    confirmEquityFunding() {
      this.form.is_equity_funded = true;
      this.triggerToast(
        "تأمین و واریز مبلغ آورده نقدی متقاضی با موفقیت تأیید گردید.",
        "success",
      );
    },

    // Interactive Scan Viewer & Lightbox Methods
    getSectionAttachments(types) {
      if (!this.attachments || !Array.isArray(this.attachments)) return [];
      if (!types) return this.attachments;
      const typeList = Array.isArray(types) ? types : [types];
      return this.attachments.filter((a) => {
        const t = a.type || a.doc_type;
        return typeList.includes(t);
      });
    },

    _makeUploadToken() {
      return (
        "up_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9)
      );
    },

    _postFormDataWithProgress(url, formData, callbacks = {}) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const startTime = Date.now();
        const csrfToken = this.getCSRFToken();

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && e.total > 0 && callbacks.onProgress) {
            const elapsed = Math.max(0.05, (Date.now() - startTime) / 1000);
            const pct = Math.min(100, Math.round((e.loaded / e.total) * 100));
            const speedBps = e.loaded / elapsed;
            const speedStr =
              speedBps > 1024 * 1024
                ? (speedBps / (1024 * 1024)).toFixed(1) + " MB/s"
                : Math.round(speedBps / 1024) + " KB/s";
            const loadedMb = (e.loaded / (1024 * 1024)).toFixed(1);
            const totalMb = (e.total / (1024 * 1024)).toFixed(1);
            callbacks.onProgress({
              percent: pct,
              loadedMb,
              totalMb,
              speedStr,
            });
          }
        };

        xhr.upload.onload = () => {
          if (callbacks.onUploadDone) {
            callbacks.onUploadDone();
          }
        };

        xhr.onload = () => {
          let data = {};
          try {
            data = JSON.parse(xhr.responseText || "{}");
          } catch (e) {
            data = {};
          }
          resolve({
            ok: xhr.status >= 200 && xhr.status < 300,
            status: xhr.status,
            data,
          });
        };

        xhr.onerror = () => {
          reject(new Error("خطای ارتباط با سرور"));
        };
        xhr.onabort = () => {
          reject(new Error("بارگذاری لغو شد"));
        };

        xhr.open("POST", url, true);
        if (csrfToken) xhr.setRequestHeader("X-CSRFToken", csrfToken);
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.send(formData);
      });
    },

    async uploadSectionAttachment(docType, defaultTitle, event) {
      if (this.isUploadingInlineScan) return;
      const file = event.target.files && event.target.files[0];
      if (!file) return;

      this.isUploadingInlineScan = true;
      this.inlineUploadProgress = 0;
      this.triggerToast(
        `در حال بارگذاری «${defaultTitle || file.name}»...`,
        "info",
      );

      try {
        const formData = new FormData();
        formData.append("title", defaultTitle || file.name);
        formData.append("doc_type", docType || "OTHER");
        formData.append("file", file);
        formData.append("upload_token", this._makeUploadToken());

        const { ok, data } = await this._postFormDataWithProgress(
          `/dossier/${this.archiveNumber}/upload-scan/`,
          formData,
          {
            onProgress: ({ percent }) => {
              this.inlineUploadProgress = percent;
            },
          },
        );
        if (ok && data.status === "success") {
          if (data.attachment) {
            const exists = this.attachments.some(
              (a) => a.id === data.attachment.id,
            );
            if (!exists) {
              this.attachments.unshift(data.attachment);
            }
          }
          const nowStr =
            new Date().toLocaleDateString("fa-IR") +
            " " +
            new Date().toLocaleTimeString("fa-IR", {
              hour: "2-digit",
              minute: "2-digit",
            });
          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${this.currentStage}`,
            toStage: `مرحله ${this.currentStage}`,
            actor: data.attachment
              ? data.attachment.uploader
              : "کارشناس سامانه",
            role: this.getStage(this.currentStage)?.role || "کارشناس",
            action: "SUBMIT",
            actionLabel: `بارگذاری سند: ${defaultTitle || file.name}`,
            timestamp: nowStr,
            hash: data.attachment ? data.attachment.sha256 : "",
            notes: `سند «${defaultTitle || file.name}» با موفقیت در این بخش بارگذاری گردید.`,
          });
          this.fieldChanges.unshift({
            field_name: "attachment",
            field_label: "بارگذاری و الصاق مدرک",
            old_value: "-",
            new_value: `${defaultTitle || file.name}`,
            changed_by: data.attachment
              ? data.attachment.uploader
              : "کارشناس سامانه",
            role: this.getStage(this.currentStage)?.role || "کارشناس",
            stage: this.currentStage,
            timestamp: nowStr,
          });
          this.triggerToast(
            `مدرک «${defaultTitle || file.name}» با موفقیت بارگذاری و الصاق شد.`,
            "success",
          );
        } else {
          this.triggerToast(data.message || "خطا در بارگذاری مدرک.", "error");
        }
      } catch (err) {
        console.error("Error uploading section attachment:", err);
        this.triggerToast(
          "خطا در برقراری ارتباط با سرور جهت بارگذاری مدرک.",
          "error",
        );
      } finally {
        this.isUploadingInlineScan = false;
        this.inlineUploadProgress = 0;
        if (event && event.target) event.target.value = "";
      }
    },

    canDeleteAttachment(item) {
      if (!item || this.isLocked || this.isViewOnly) return false;
      return item.can_delete === true;
    },

    async deleteAttachment(attId) {
      if (this.isLocked || this.isViewOnly) {
        this.triggerToast("امکان حذف اسناد در حالت فقط خواندنی وجود ندارد.", "error");
        return;
      }
      const targetItem = this.attachments.find((a) => a.id === attId);
      if (targetItem && !this.canDeleteAttachment(targetItem)) {
        this.triggerToast("فقط کاربری که این تصویر را بارگذاری کرده است مجاز به حذف آن می‌باشد.", "error");
        return;
      }
      if (!confirm("آیا از حذف این مدرک از پرونده اطمینان دارید؟")) return;

      try {
        const csrfToken = this.getCSRFToken();
        const res = await fetch(
          `/dossier/${this.archiveNumber}/attachment/${attId}/delete/`,
          {
            method: "POST",
            headers: {
              "X-CSRFToken": csrfToken,
            },
          },
        );

        const data = await res.json();
        if (res.ok && data.status === "success") {
          const removedItem = this.attachments.find((a) => a.id === attId);
          const attTitle = removedItem ? removedItem.title : `شناسه ${attId}`;
          this.attachments = this.attachments.filter((a) => a.id !== attId);
          if (this.activeScan && this.activeScan.id === attId) {
            this.closeScanViewer();
          }
          const nowStr =
            new Date().toLocaleDateString("fa-IR") +
            " " +
            new Date().toLocaleTimeString("fa-IR", {
              hour: "2-digit",
              minute: "2-digit",
            });
          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${this.currentStage}`,
            toStage: `مرحله ${this.currentStage}`,
            actor: "کاربر سامانه",
            role: this.getStage(this.currentStage)?.role || "کارشناس",
            action: "DELETE",
            actionLabel: `حذف مدرک: ${attTitle}`,
            timestamp: nowStr,
            hash: "",
            notes: `مدرک پیوست «${attTitle}» با موفقیت از پرونده حذف شد.`,
          });
          this.fieldChanges.unshift({
            field_name: "attachment",
            field_label: "حذف مدرک پیوست",
            old_value: attTitle,
            new_value: "حذف قطعی",
            changed_by: "کاربر سامانه",
            role: this.getStage(this.currentStage)?.role || "کارشناس",
            stage: this.currentStage,
            timestamp: nowStr,
          });
          this.triggerToast(
            data.message || "مدرک با موفقیت حذف گردید.",
            "success",
          );
        } else {
          this.triggerToast(data.message || "خطا در حذف مدرک.", "error");
        }
      } catch (err) {
        console.error("Error deleting attachment:", err);
        this.triggerToast(
          "خطا در برقراری ارتباط با سرور جهت حذف مدرک.",
          "error",
        );
      }
    },

    getPaginatedAttachments() {
      const all = this.getFilteredAttachments() || [];
      const start = (this.albumPage - 1) * this.albumPerPage;
      return all.slice(start, start + this.albumPerPage);
    },

    totalAlbumPages() {
      const all = this.getFilteredAttachments() || [];
      if (!all.length) return 1;
      return Math.max(1, Math.ceil(all.length / this.albumPerPage));
    },

    nextAlbumPage() {
      if (this.albumPage < this.totalAlbumPages()) {
        this.albumPage++;
      }
    },

    prevAlbumPage() {
      if (this.albumPage > 1) {
        this.albumPage--;
      }
    },

    setAlbumPage(p) {
      if (p >= 1 && p <= this.totalAlbumPages()) {
        this.albumPage = p;
      }
    },

    setAlbumPerPage(num) {
      this.albumPerPage = Number(num) === 3 ? 3 : 4;
      this.albumPage = 1;
    },

    openScanViewer(item) {
      const list = this.getFilteredAttachments() || [];
      const idx = list.findIndex((a) => a.id === item.id);
      this.activeScanIndex = idx >= 0 ? idx : 0;
      this.activeScan = {
        ...item,
        zoom: 1,
        rotation: 0,
      };
      this.showScanViewerModal = true;
    },

    nextScan() {
      const list = this.getFilteredAttachments() || [];
      if (!list.length) return;
      this.activeScanIndex = (this.activeScanIndex + 1) % list.length;
      const nextItem = list[this.activeScanIndex];
      if (nextItem) {
        this.activeScan = {
          ...nextItem,
          zoom: 1,
          rotation: 0,
        };
      }
    },

    prevScan() {
      const list = this.getFilteredAttachments() || [];
      if (!list.length) return;
      this.activeScanIndex =
        (this.activeScanIndex - 1 + list.length) % list.length;
      const prevItem = list[this.activeScanIndex];
      if (prevItem) {
        this.activeScan = {
          ...prevItem,
          zoom: 1,
          rotation: 0,
        };
      }
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

    printActiveScan() {
      if (!this.activeScan) return;
      this.printScan(this.activeScan);
    },

    printScan(item) {
      if (!item) return;

      // 1. If it's a check / amadesazi receipt (or any official print document):
      // It has the official Header (dossier, project, etc.) and Footer (financials, signatures) as requested
      if (
        this.isHtmlDoc(item) ||
        (item.preview_url && item.preview_url.includes("/print/checks/"))
      ) {
        const printUrl = item.preview_url.includes("auto_print=1")
          ? item.preview_url
          : item.preview_url +
            (item.preview_url.includes("?") ? "&" : "?") +
            "auto_print=1";
        const printWin = window.open(printUrl, "_blank");
        if (printWin) {
          printWin.focus();
        }
        return;
      }

      // 2. If it's a PDF document:
      if (this.isPdfFile(item) && item.preview_url) {
        const printWin = window.open(item.preview_url, "_blank");
        if (printWin) {
          printWin.focus();
        }
        return;
      }

      // 3. If it's a real scan/image in the album:
      // Print ONLY the scan image, full-page, with NO uploader name, NO header, NO footer
      if (item.preview_url) {
        const printWindow = window.open("", "_blank", "width=900,height=1200");
        if (!printWindow) {
          this.triggerToast(
            "لطفاً اجازه باز شدن پنجره پاپ‌آپ (Pop-up) را در مرورگر صادر فرمایید.",
            "error",
          );
          return;
        }
        printWindow.document.write(`<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="utf-8">
    <title>چاپ برگه اسکن</title>
    <style>
        @page {
            size: A4 portrait;
            margin: 0;
        }
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .scan-container {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            padding: 8mm;
        }
        img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            display: block;
        }
        @media print {
            html, body {
                margin: 0 !important;
                padding: 0 !important;
            }
            .scan-container {
                padding: 0 !important;
            }
            img {
                max-width: 100vw !important;
                max-height: 100vh !important;
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="scan-container">
        <img src="${item.preview_url}" onload="setTimeout(function(){ window.print(); window.close(); }, 350);" onerror="alert('خطا در دریافت تصویر سند'); window.close();" />
    </div>
</body>
</html>`);
        printWindow.document.close();
        return;
      }

      // 4. Fallback for simulated documents
      window.print();
    },

    // Helper methods for Document Album & File types
    isPdfFile(item) {
      if (!item) return false;
      const url = (item.preview_url || "").toLowerCase();
      const name = (item.fileName || item.file_name || "").toLowerCase();
      return (
        url.endsWith(".pdf") || name.endsWith(".pdf") || url.includes(".pdf?")
      );
    },

    isHtmlDoc(item) {
      if (!item) return false;
      const url = (item.preview_url || "").toLowerCase();
      const name = (item.fileName || item.file_name || "").toLowerCase();
      return (
        url.includes("/print/") ||
        url.endsWith(".html") ||
        name.endsWith(".html")
      );
    },

    _upsertAttachments(items) {
      (items || []).forEach((att) => {
        if (!att) return;
        const idx = this.attachments.findIndex((a) => a.id === att.id);
        if (idx >= 0) {
          this.attachments.splice(idx, 1, att);
        } else {
          this.attachments.unshift(att);
        }
      });
    },

    async handleCheckScanUploadAndReceipt(event, type = "loan") {
      if (this.isUploadingInlineScan) {
        if (event && event.target) event.target.value = "";
        return;
      }
      const file = event.target.files && event.target.files[0];
      if (!file) return;

      const typeLabel =
        type === "prep" ? "اقساط آماده‌سازی" : "تسهیلات وام دهک";
      this.isUploadingInlineScan = true;
      this.inlineUploadProgress = 0;
      this.triggerToast(
        `در حال بارگذاری اسکن و تولید برگه رسید چک‌های ${typeLabel}...`,
        "info",
      );

      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("check_type", type);
        formData.append("upload_token", this._makeUploadToken());

        const { ok, data } = await this._postFormDataWithProgress(
          `/dossier/${this.archiveNumber}/checks/upload-scan-and-create-receipt/`,
          formData,
          {
            onProgress: ({ percent }) => {
              this.inlineUploadProgress = percent;
            },
          },
        );
        if (ok && data.status === "success") {
          if (data.attachment) {
            this._upsertAttachments([data.attachment]);
          }
          this.triggerToast(
            "تصویر اسکن دریافت، سربرگ و امضاها افزوده و به عنوان رسید چک‌ها ذخیره گردید ✓",
            "success",
          );

          // No auto-print; added to scan album directly
        } else {
          this.triggerToast(
            data.message || "خطا در بارگذاری اسکن چک.",
            "error",
          );
        }
      } catch (err) {
        console.error("Error uploading check scan and creating receipt:", err);
        this.triggerToast("خطا در ارتباط با سرور جهت تولید رسید چک.", "error");
      } finally {
        this.isUploadingInlineScan = false;
        this.inlineUploadProgress = 0;
        if (event && event.target) event.target.value = "";
      }
    },

    getPrepCheckScans() {
      return (this.attachments || []).filter(
        (a) =>
          (a.type === "PREP_CHECK" || a.doc_type === "PREP_CHECK") &&
          a.preview_url &&
          !a.preview_url.includes("/print/checks/"),
      );
    },

    getLoanCheckScans() {
      return (this.attachments || []).filter(
        (a) =>
          (a.type === "LOAN_CHECK" || a.doc_type === "LOAN_CHECK") &&
          a.preview_url &&
          !a.preview_url.includes("/print/checks/"),
      );
    },

    async handleMultiCheckScanUpload(event, type = "prep") {
      if (this.isUploadingInlineScan) {
        if (event && event.target) event.target.value = "";
        return;
      }
      const files = event.target.files;
      if (!files || files.length === 0) return;

      const count = files.length;
      const typeLabel =
        type === "prep" ? "اقساط آماده‌سازی" : "تسهیلات وام دهک";
      this.isUploadingInlineScan = true;
      this.inlineUploadProgress = 0;
      this.triggerToast(
        `در حال بارگذاری ${count} برگ اسکن و تولید صفحات متوالی چاپ چک‌های ${typeLabel}...`,
        "info",
      );

      try {
        const formData = new FormData();
        formData.append("check_type", type);
        formData.append("upload_token", this._makeUploadToken());
        for (let i = 0; i < files.length; i++) {
          formData.append("files", files[i]);
        }

        const { ok, data } = await this._postFormDataWithProgress(
          `/dossier/${this.archiveNumber}/checks/upload-scan-and-create-receipt/`,
          formData,
          {
            onProgress: ({ percent }) => {
              this.inlineUploadProgress = percent;
            },
          },
        );
        if (ok && data.status === "success") {
          if (data.attachments && Array.isArray(data.attachments)) {
            this._upsertAttachments(data.attachments);
          } else if (data.attachment) {
            this._upsertAttachments([data.attachment]);
          }

          this.triggerToast(
            `تعداد ${count} برگ اسکن دریافت، سربرگ متمرکز و امضاها اعمال شد و در آلبوم اسناد ذخیره گردید ✓`,
            "success",
          );

          // No auto-print; added to scan album directly
        } else {
          this.triggerToast(
            data.message || "خطا در بارگذاری اسکن چک‌ها.",
            "error",
          );
        }
      } catch (err) {
        console.error("Error uploading multi-scan checks:", err);
        this.triggerToast(
          "خطا در ارتباط با سرور جهت بارگذاری اسکن چک‌ها.",
          "error",
        );
      } finally {
        this.isUploadingInlineScan = false;
        this.inlineUploadProgress = 0;
        if (event && event.target) event.target.value = "";
      }
    },

    printCheckScans(type = "prep") {
      const printUrl = `/dossier/${this.archiveNumber}/print/checks/?type=${type}&auto_archive=1&auto_print=1`;
      window.open(printUrl, "_blank");
    },

    async deleteCheckScan(attachmentId, type = "prep") {
      const targetItem = this.attachments.find((a) => a.id === attachmentId);
      if (targetItem && !this.canDeleteAttachment(targetItem)) {
        this.triggerToast("فقط کاربری که این تصویر را بارگذاری کرده است مجاز به حذف آن می‌باشد.", "error");
        return;
      }
      if (!confirm("آیا از حذف این برگ اسکن اطمینان دارید؟")) return;
      await this.deleteAttachment(attachmentId);
    },

    async printExistingCheckScanReceipt(type = "loan") {
      this.printCheckScans(type);
    },

    async printChecksReceipt(type = "loan") {
      this.printCheckScans(type);
    },

    isImageFile(item) {
      if (!item) return false;
      const url = (item.preview_url || "").toLowerCase();
      const name = (item.fileName || item.file_name || "").toLowerCase();
      const isImg =
        url.endsWith(".jpg") ||
        url.endsWith(".jpeg") ||
        url.endsWith(".png") ||
        url.endsWith(".webp") ||
        url.endsWith(".jfif") ||
        name.endsWith(".jpg") ||
        name.endsWith(".jpeg") ||
        name.endsWith(".png") ||
        name.endsWith(".webp") ||
        name.endsWith(".jfif");
      return isImg || url.startsWith("data:image");
    },

    isUploadAllowed() {
      if (this.isLocked) return false;
      return true;
    },

    async generateAndArchiveDocument(docType) {
      if (!this.archiveNumber) return;
      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/generate-doc/${docType}/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCSRFToken()
          }
        });
        const data = await res.json();
        if (data.status === "success") {
          this.triggerToast(data.message, "success");
          if (docType === "affidavit" || docType === "iqrar") {
            this.form.has_affidavit = true;
          } else if (docType === "info_form" || docType === "info") {
            this.form.has_info_form = true;
          }
          if (data.attachment && Array.isArray(this.attachments)) {
            const existingIdx = this.attachments.findIndex(a => a.doc_type === data.attachment.doc_type);
            if (existingIdx >= 0) {
              this.attachments.splice(existingIdx, 1, data.attachment);
            } else {
              this.attachments.unshift(data.attachment);
            }
          }
          if (data.print_url) {
            window.open(data.print_url, "_blank");
          }
        } else {
          this.triggerToast(data.message || "خطا در تولید سند", "error");
        }
      } catch (err) {
        console.error(err);
        this.triggerToast("خطای شبکه در تولید مدرک", "error");
      }
    },

    // Upload & Scanner Controller Methods
    openUploadScanModal(docType = null, defaultTitle = null) {
      if (this.isUploadingScan) return;
      if (this.isLocked || this.isViewOnly) {
        this.triggerToast(
          "در حالت فقط خواندنی امکان بارگذاری مدارک جدید وجود ندارد.",
          "error",
        );
        return;
      }

      let finalTitle = defaultTitle;
      let finalType = docType;

      if (!finalTitle || !finalType) {
        let computedTitle = "مدرک پیوست مرحله " + this.currentStage;
        let computedType = "OTHER";

        if (this.currentStage === 1) {
          computedTitle = "اسکن کارت ملی و مدارک سجلی";
          computedType = "NATIONAL_ID";
        } else if (this.currentStage === 3 || this.currentStage === 10) {
          computedTitle = "تصویر و استعلام رسمی فرم (ج) اداره کل";
          computedType = "FORM_J";
        } else if (this.currentStage === 7) {
          computedTitle = "اسکن دفترچه اقساط تسهیلات بانک مسکن";
          computedType = "BANK_BOOKLET";
        } else if (this.currentStage === 12 || this.currentStage === 13) {
          computedTitle = "اسکن سند مالکیت عرصه";
          computedType = "TITLE_DEED";
        } else if (this.currentStage === 16 || this.currentStage === 17) {
          computedTitle = "اسکن چک صیادی تسهیلات دهک";
          computedType = "LOAN_CHECK";
        } else if (this.currentStage === 18) {
          computedTitle = "اسکن چک‌های آماده‌سازی و اجاره";
          computedType = "PREP_CHECK";
        } else if (this.currentStage === 20) {
          computedTitle = "اسکن معرفی‌نامه دفتر اسناد رسمی (محضر)";
          computedType = "NOTARY_LETTER";
        } else if (this.currentStage === 21) {
          computedTitle = "اسکن سند قرارداد اجاره عرصه";
          computedType = "LEASE_CONTRACT";
        }

        finalTitle = finalTitle || computedTitle;
        finalType = finalType || computedType;
      }

      this.uploadForm = {
        title: finalTitle || "",
        doc_type: finalType || "OTHER",
        filesList: [],
      };
      this.isScanning = false;
      this.isUploadingScan = false;
      this.scanUploadProgress = 0;
      this.scanUploadPhase = "";
      this.scanUploadStatus = "";
      this.scanUploadDetails = "";
      this.showUploadModal = true;
    },

    setQuickScanTitle(title, type) {
      this.uploadForm.title = title;
      this.uploadForm.doc_type = type;
    },

    handleFileSelect(event) {
      const files = Array.from(event.target.files || []);
      if (!files.length) return;

      files.forEach((f) => {
        const isImg =
          (f.type && f.type.startsWith("image/")) ||
          /\.(jpe?g|jfif|png|webp|gif|bmp|svg)$/i.test(f.name);

        let syncPreview = "";
        if (isImg) {
          try {
            syncPreview = URL.createObjectURL(f);
          } catch (e) {
            syncPreview = "";
          }
        }

        const itemObj = {
          file: f,
          fileName: f.name,
          sizeStr:
            f.size > 1048576
              ? (f.size / 1048576).toFixed(1) + " مگابایت"
              : Math.round(f.size / 1024) + " کیلوبایت",
          previewUrl: syncPreview,
          isScanner: false,
        };
        this.uploadForm.filesList.push(itemObj);

        if (isImg && !itemObj.previewUrl) {
          const reader = new FileReader();
          reader.onload = (e) => {
            itemObj.previewUrl = e.target.result;
          };
          reader.readAsDataURL(f);
        }
      });

      if (!this.uploadForm.title && files.length === 1) {
        this.uploadForm.title = files[0].name.replace(/\.[^/.]+$/, "");
      }

      if (event.target) event.target.value = "";
    },

    moveUploadFileUp(idx) {
      if (!this.uploadForm.filesList || idx <= 0) return;
      const item = this.uploadForm.filesList.splice(idx, 1)[0];
      this.uploadForm.filesList.splice(idx - 1, 0, item);
    },

    moveUploadFileDown(idx) {
      if (
        !this.uploadForm.filesList ||
        idx >= this.uploadForm.filesList.length - 1
      )
        return;
      const item = this.uploadForm.filesList.splice(idx, 1)[0];
      this.uploadForm.filesList.splice(idx + 1, 0, item);
    },

    reorderFiles(fromIdx, toIdx) {
      if (
        !this.uploadForm.filesList ||
        fromIdx === null ||
        toIdx === null ||
        fromIdx === toIdx
      )
        return;
      const item = this.uploadForm.filesList.splice(fromIdx, 1)[0];
      this.uploadForm.filesList.splice(toIdx, 0, item);
    },

    removeUploadFile(index) {
      if (this.uploadForm.filesList) {
        this.uploadForm.filesList.splice(index, 1);
      }
    },

    clearAllUploadFiles() {
      if (this.uploadForm.filesList) {
        this.uploadForm.filesList = [];
      }
    },

    simulateScannerDevice() {
      this.isScanning = true;
      setTimeout(() => {
        this.isScanning = false;
        const scanIdx =
          (this.uploadForm.filesList ? this.uploadForm.filesList.length : 0) +
          1;
        const dummySvg =
          'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="600" height="400" fill="%23f8fafc" stroke="%233b82f6" stroke-width="4"/><text x="50%" y="40%" font-size="20" font-family="Tahoma" fill="%231e3a8a" text-anchor="middle">سند اسکن شده از دستگاه اسکنر متصل (WIA/TWAIN)</text><text x="50%" y="55%" font-size="14" font-family="Tahoma" fill="%23059669" text-anchor="middle">کیفیت اسکن: 300 DPI - رنگی - برگه ' +
          scanIdx +
          '</text><circle cx="500" cy="320" r="45" fill="none" stroke="%23dc2626" stroke-dasharray="4,4" stroke-width="2"/><text x="500" y="325" font-size="11" font-family="Tahoma" fill="%23dc2626" text-anchor="middle">مهر دبیرخانه</text></svg>';

        if (!this.uploadForm.filesList) this.uploadForm.filesList = [];
        this.uploadForm.filesList.push({
          file: null,
          fileName: `scanner_wia_${Date.now()}_sheet_${scanIdx}.jpg`,
          sizeStr: "300 DPI (اسکن سخت‌افزاری)",
          previewUrl: dummySvg,
          isScanner: true,
        });
        this.triggerToast(
          `برگه اسکن شماره ${scanIdx} با موفقیت از دستگاه اسکنر دریافت شد.`,
          "success",
        );
      }, 1000);
    },

    async submitScanUpload() {
      if (this.isUploadingScan) {
        return;
      }

      if (
        !this.uploadForm.filesList ||
        this.uploadForm.filesList.length === 0
      ) {
        this.triggerToast(
          "لطفاً حداقل یک فایل مدرک انتخاب یا از طریق اسکنر دریافت نمایید.",
          "error",
        );
        return;
      }

      if (this.isLocked) {
        this.triggerToast(
          "این پرونده نهایی و بایگانی شده است و امکان بارگذاری مدرک جدید وجود ندارد.",
          "error",
        );
        return;
      }

      const totalCount = this.uploadForm.filesList.length;
      const customTitle = (this.uploadForm.title || "").trim();

      this.isUploadingScan = true;
      this.scanUploadProgress = 0;
      this.scanUploadPhase = "uploading";
      this.scanUploadStatus = `در حال ارسال ${totalCount} برگ مدرک به سرور...`;
      this.scanUploadDetails =
        "لطفاً تا پایان ذخیره منتظر بمانید و مجدداً کلیک نکنید.";

      try {
        const formData = new FormData();
        if (customTitle) {
          formData.append("title", customTitle);
        }
        formData.append("doc_type", this.uploadForm.doc_type || "OTHER");
        formData.append("upload_token", this._makeUploadToken());

        this.uploadForm.filesList.forEach((item) => {
          if (item.file) {
            formData.append("files", item.file);
          } else if (item.previewUrl) {
            formData.append("preview_urls", item.previewUrl);
          }
        });

        const { ok: responseOk, data: resData } =
          await this._postFormDataWithProgress(
            `/dossier/${this.archiveNumber}/upload-scan/`,
            formData,
            {
              onProgress: ({ percent, loadedMb, totalMb, speedStr }) => {
                this.scanUploadProgress = percent;
                if (percent < 100) {
                  this.scanUploadPhase = "uploading";
                  this.scanUploadStatus = `در حال ارسال ${totalCount} برگ مدرک به سرور...`;
                  this.scanUploadDetails = `${loadedMb} از ${totalMb} مگابایت (${speedStr})`;
                } else {
                  this.scanUploadPhase = "saving";
                  this.scanUploadStatus =
                    "فایل‌ها ارسال شدند؛ در حال ثبت نهایی در پرونده...";
                  this.scanUploadDetails = "لطفاً صفحه را نبندید.";
                }
              },
              onUploadDone: () => {
                this.scanUploadProgress = 100;
                this.scanUploadPhase = "saving";
                this.scanUploadStatus =
                  "در حال بهینه‌سازی تصاویر و ثبت در سامانه...";
                this.scanUploadDetails = "چند لحظه تا تکمیل بایگانی...";
              },
            },
          );

        if (responseOk && resData.status === "success") {
          const newAttachments =
            resData.attachments ||
            (resData.attachment ? [resData.attachment] : []);

          this.scanUploadPhase = "done";
          // Prepend new attachments to UI list without duplicates
          this._upsertAttachments(newAttachments);

          const nowStr =
            "۱۴۰۳/۰۵/۲۲ " +
            new Date().toLocaleTimeString("fa-IR", {
              hour: "2-digit",
              minute: "2-digit",
            });
          const logLabel =
            newAttachments.length === 1
              ? `بارگذاری سند: ${newAttachments[0].title}`
              : `بارگذاری دسته‌جمعی ${newAttachments.length} برگ سند اسکن‌شده`;

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${this.currentStage}`,
            toStage: `مرحله ${this.currentStage}`,
            actor: newAttachments[0]
              ? newAttachments[0].uploader
              : "کارشناس بایگانی اسناد",
            role: this.getStage(this.currentStage).role,
            action: "SUBMIT",
            actionLabel: logLabel,
            timestamp: nowStr,
            hash: newAttachments[0] ? newAttachments[0].sha256 : "",
            notes: `تعداد ${newAttachments.length} برگ سند با موفقیت در پوشه پرونده ذخیره و الصاق گردید.`,
          });

          newAttachments.forEach((att) => {
            this.fieldChanges.unshift({
              field_name: "attachment",
              field_label: "بارگذاری مدرک اسکن",
              old_value: "-",
              new_value: `${att.title} (${att.fileName || ""})`,
              changed_by: att.uploader || "کارشناس سامانه",
              role: this.getStage(this.currentStage)?.role || "کارشناس",
              stage: this.currentStage,
              timestamp: nowStr,
            });
          });

          this.triggerToast(
            `تعداد ${newAttachments.length} برگ سند اسکن‌شده با موفقیت الصاق گردید.`,
            "success",
          );
          this.showUploadModal = false;
          this.uploadForm.filesList = [];
        } else {
          this.triggerToast(
            resData.message || "خطا در بارگذاری مدارک.",
            "error",
          );
        }
      } catch (err) {
        console.error("Upload error:", err);
        this.triggerToast(
          "خطای ارتباط با سرور در هنگام بارگذاری مدارک.",
          "error",
        );
      } finally {
        this.isUploadingScan = false;
        this.scanUploadProgress = 0;
        this.scanUploadPhase = "";
        this.scanUploadStatus = "";
        this.scanUploadDetails = "";
      }
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
        desc: `مدرک بارگذاری‌شده در مرحله ${this.currentStage} (${this.getStage(this.currentStage).title})`,
      };
      this.attachments.unshift(newScan);
    },

    // Workflow Phase, Guidance & Section Helpers
    getPhaseName(stg) {
      stg = Number(stg);
      if (stg <= 2) return "فاز اول: ثبت‌نام، مشخصات متقاضی و پلاک (کارگزاری)";
      if (stg <= 10)
        return "فاز دوم: استعلامات، تسهیلات بانکی و تایید مدیرعامل";
      if (stg <= 17) return "فاز سوم: ممیزی تخصصی اراضی، فنی و حقوقی اداره کل";
      return "فاز چهارم: وصول تضامین، تسویه، معرفی محضر و بایگانی";
    },

    getStageGuidance(stg) {
      return (
        STAGE_GUIDANCE[Number(stg)] || {
          actionTitle: "اقدام کارشناسی این مرحله",
          actionSummary:
            "بررسی مدارک و مستندات پرونده، کنترل اطلاعات و ثبت امضای دیجیتال.",
          items: [
            "بررسی سوابق مراحل قبلی",
            "تطبیق اطلاعات با مستندات ثبتی",
            "ثبت تاییدیه الکترونیکی",
          ],
          targetSection: "#form-sections",
        }
      );
    },

    scrollToActiveSection(targetSelector) {
      if (!targetSelector) return;
      const el = document.querySelector(targetSelector);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("pulse-highlight");
        setTimeout(() => {
          el.classList.remove("pulse-highlight");
        }, 2800);
      }
    },

    isSectionActive(sectionId) {
      // Locked/archived dossiers have no active action stage
      if (this.isLocked || Number(this.currentStage) >= 22) return false;
      const stg = Number(this.currentStage);
      const mapping = SECTION_STAGE_MAP;
      return mapping[sectionId] ? mapping[sectionId].includes(stg) : false;
    },

    shouldSectionOpen(sectionId) {
      // For archived/locked dossiers, keep all sections expanded and viewable
      if (this.isLocked || Number(this.currentStage) >= 22) return true;
      if (this.isChief || this.isSuperuser) return true;
      if (this.isSectionActive(sectionId)) return true;
      const allowed = Array.isArray(this.userAllowedStages)
        ? this.userAllowedStages.map(Number)
        : [];
      const mapping = SECTION_STAGE_MAP[sectionId] || [];
      return allowed.some((stg) => mapping.includes(stg));
    },

    // Helper to safely get stage metadata by ID

    // --------------------------------------------------------------------------
    // Strict Catalog Searchable Dropdowns (Sites, Projects, Codes, Banks, Branches)
    // --------------------------------------------------------------------------
    normalizeCatalogText(val) {
      if (val === null || val === undefined) return "";
      const faDigits = "۰۱۲۳۴۵۶۷۸۹";
      const arDigits = "٠١٢٣٤٥٦٧٨٩";
      return String(val)
        .replace(/[۰-۹]/g, (d) => String(faDigits.indexOf(d)))
        .replace(/[٠-٩]/g, (d) => String(arDigits.indexOf(d)))
        .replace(/ي/g, "ی")
        .replace(/ك/g, "ک")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
    },

    isApartmentSite(siteName) {
      const s = this.normalizeCatalogText(siteName);
      if (!s) return null;
      return s.includes("560") || s.includes("27");
    },

    isVillaConstruction() {
      const bySite = this.isApartmentSite(this.form && this.form.site);
      if (bySite === true) return false;
      if (bySite === false) return true;
      const ct = String((this.form && this.form.construction_type) || "").trim();
      return ct.includes("ویلایی");
    },

    syncConstructionTypeBySite(siteName = null) {
      if (!this.form || !this.isFieldEditable("construction_type")) return;
      const targetSite = siteName !== null ? siteName : this.form.site;
      const isApt = this.isApartmentSite(targetSite);
      if (isApt === true) {
        if (this.form.construction_type !== "آپارتمانی") {
          this.form.construction_type = "آپارتمانی";
        }
      } else if (isApt === false) {
        const cur = String(this.form.construction_type || "").trim();
        if (!cur.includes("ویلایی")) {
          this.form.construction_type = "ویلایی";
        }
      }
      this.syncUnitDirectionByConstruction();
    },

    syncUnitDirectionByConstruction() {
      if (!this.form) return;
      if (this.isVillaConstruction()) {
        if (
          this.isFieldEditable("unit_direction") &&
          this.form.unit_direction !== "شمالی"
        ) {
          this.form.unit_direction = "شمالی";
        }
      }
    },

    _catalogProjects() {
      const cat = this.projectsCatalog || {};
      if (Array.isArray(cat.projects) && cat.projects.length) return cat.projects;
      return this.projectsList || window.ALL_PROJECTS || [];
    },

    getCatalogItems(kind, query, typing = true) {
      const cat = this.projectsCatalog || {};
      const q = typing ? this.normalizeCatalogText(query) : "";
      const norm = (v) => this.normalizeCatalogText(v);

      if (kind === "site") {
        const list = Array.isArray(cat.sites) ? cat.sites : [];
        return list
          .filter(
            (s) =>
              !q ||
              norm(s.value).includes(q) ||
              norm(s.csv_label).includes(q) ||
              norm(s.city).includes(q),
          )
          .map((s) => ({
            key: `site-${s.value}`,
            value: s.value,
            primary: s.value,
            secondary: s.csv_label && s.csv_label !== s.value ? s.csv_label : "",
            badge: "",
            aliases: [s.value, s.csv_label],
            raw: s,
          }));
      }

      if (kind === "bank") {
        const list = Array.isArray(cat.banks) ? cat.banks : [];
        return list
          .filter(
            (b) =>
              !q || norm(b.value).includes(q) || norm(b.csv_label).includes(q),
          )
          .map((b) => ({
            key: `bank-${b.value}`,
            value: b.value,
            primary: b.value,
            secondary: b.csv_label && b.csv_label !== b.value ? b.csv_label : "",
            badge: "",
            aliases: [b.value, b.csv_label],
            raw: b,
          }));
      }

      if (kind === "branch") {
        let list = Array.isArray(cat.branches) ? cat.branches.slice() : [];
        const activeBank = norm(this.form.bank_name);
        if (!q && activeBank) {
          list.sort((a, b) => {
            const am = norm(a.bank_name) === activeBank ? 0 : 1;
            const bm = norm(b.bank_name) === activeBank ? 0 : 1;
            return am - bm;
          });
        }
        return list
          .filter(
            (br) =>
              !q ||
              norm(br.branch_name).includes(q) ||
              norm(br.branch_code).includes(q) ||
              norm(br.bank_name).includes(q),
          )
          .map((br) => ({
            key: `branch-${br.branch_code}-${br.bank_name}-${br.branch_name}`,
            value: br.branch_name,
            primary: br.branch_name,
            secondary: br.bank_name,
            badge: br.branch_code,
            aliases: [br.branch_name, br.branch_code],
            raw: br,
          }));
      }

      if (kind === "code") {
        const list = this._catalogProjects();
        return list
          .filter(
            (p) =>
              !q ||
              norm(p.code).includes(q) ||
              norm(p.name).includes(q) ||
              norm(p.site).includes(q),
          )
          .map((p) => ({
            key: `code-${p.code}`,
            value: p.code,
            primary: p.code,
            secondary: p.name,
            badge: p.site,
            aliases: [p.code],
            raw: p,
          }));
      }

      // Default: 'project'
      let projects = this._catalogProjects().slice();
      const activeSite = norm(this.form.site);
      if (!q && activeSite) {
        projects.sort((a, b) => {
          const am = norm(a.site) === activeSite ? 0 : 1;
          const bm = norm(b.site) === activeSite ? 0 : 1;
          return am - bm;
        });
      }
      return projects
        .filter(
          (p) =>
            !q ||
            norm(p.name).includes(q) ||
            norm(p.code).includes(q) ||
            norm(p.site).includes(q) ||
            norm(p.bank_name).includes(q) ||
            norm(p.branch_name).includes(q),
        )
        .map((p) => ({
          key: `proj-${p.code}-${p.name}`,
          value: p.name,
          primary: p.name,
          secondary: [p.site, p.bank_name, p.branch_name ? `شعبه ${p.branch_name}` : ""]
            .filter(Boolean)
            .join(" • "),
          badge: p.code,
          aliases: [p.name],
          raw: p,
        }));
    },

    findExactCatalogItem(kind, rawVal) {
      const target = this.normalizeCatalogText(rawVal);
      if (!target) return null;
      const items = this.getCatalogItems(kind, "", false);
      return (
        items.find((it) => {
          if (this.normalizeCatalogText(it.value) === target) return true;
          return Array.isArray(it.aliases)
            ? it.aliases.some((a) => this.normalizeCatalogText(a) === target)
            : false;
        }) || null
      );
    },

    selectCatalogItem(kind, item) {
      if (!item) return;
      if (kind === "project" || kind === "code") {
        this.selectProject(item.raw);
        return;
      }
      if (kind === "site") {
        this.form.site = item.value;
        return;
      }
      if (kind === "bank") {
        this.form.bank_name = item.value;
        const curBranch = this.normalizeCatalogText(this.form.bank_branch);
        if (curBranch && this.isFieldEditable("bank_branch")) {
          const branches = (this.projectsCatalog && this.projectsCatalog.branches) || [];
          const matchesBank = branches.some(
            (b) =>
              this.normalizeCatalogText(b.branch_name) === curBranch &&
              this.normalizeCatalogText(b.bank_name) ===
                this.normalizeCatalogText(item.value),
          );
          if (!matchesBank) this.form.bank_branch = "";
        }
        return;
      }
      if (kind === "branch") {
        this.form.bank_branch = item.value;
        if (
          item.raw &&
          item.raw.bank_name &&
          this.isFieldEditable("bank_name")
        ) {
          this.form.bank_name = item.raw.bank_name;
        }
      }
    },

    commitCatalogInput(kind, fieldName, wasTyping, prevVal) {
      if (!this.isFieldEditable(fieldName)) return this.form[fieldName] || "";
      const cur = String(this.form[fieldName] || "").trim();
      const prevClean = String(prevVal || "").trim();
      if (!wasTyping && cur === prevClean) return prevClean;
      if (!cur) {
        this.form[fieldName] = "";
        return "";
      }
      const exact = this.findExactCatalogItem(kind, cur);
      if (exact) {
        this.selectCatalogItem(kind, exact);
        return this.form[fieldName] || exact.value;
      }
      this.form[fieldName] = prevClean;
      this.triggerToast(
        "تنها امکان انتخاب از گزینه‌های لیست مصوب وجود دارد.",
        "warning",
      );
      return prevClean;
    },

    getFilteredProjects(query) {
      return this.getCatalogItems("project", query, true).map((it) => it.raw);
    },

    selectProject(p) {
      if (!p) return;
      if (this.isFieldEditable("project")) {
        this.form.project = p.name || "";
      }
      if (p.code && this.isFieldEditable("project_code")) {
        this.form.project_code = p.code;
      }
      if (p.site && this.isFieldEditable("site")) {
        this.form.site = p.site;
      }
      if (p.bank_name && this.isFieldEditable("bank_name")) {
        this.form.bank_name = p.bank_name;
      }
      if (p.branch_name && this.isFieldEditable("bank_branch")) {
        this.form.bank_branch = p.branch_name;
      }
    },

    getStage(id) {
      return (
        this.stages.find((s) => s.id === Number(id)) || {
          id,
          title: `مرحله ${id}`,
          role: "کارشناس اقدام‌کننده",
          unit: "brokerage",
        }
      );
    },

    // Permission Checker: all fields are editable across stages if user has permission, locked upon final archive
    isFieldEditable(fieldName) {
      if (this.isLocked || this.isViewOnly) return false;
      if (
        [
          "is_loan_sent_to_directorate",
          "loan_directorate_sent_date",
          "is_prep_sent_to_directorate",
          "prep_directorate_sent_date",
        ].includes(fieldName)
      ) {
        return false;
      }
      if (
        ["visit_date", "loan_visit_date", "prep_visit_date"].includes(fieldName) &&
        !this.canManageDirectorateShipments
      ) {
        return false;
      }
      if (
        this.isSuperuser ||
        this.isChief ||
        this.userAllowedStages === "all"
      ) {
        if (this.isViewOnly) return false;
        return true;
      }
      if (typeof this.userCanAction !== "undefined" && !this.userCanAction) {
        return false;
      }
      const fieldStages = FIELD_STAGE_MAP[fieldName];
      if (!fieldStages) {
        return false;
      }
      const allowed = Array.isArray(this.userAllowedStages)
        ? this.userAllowedStages
        : [];
      return fieldStages.some((stg) => allowed.includes(stg));
    },

    canSeeFullSection1() {
      if (
        this.isSuperuser ||
        this.isChief ||
        this.userAllowedStages === "all"
      ) {
        return true;
      }
      const allowed = Array.isArray(this.userAllowedStages)
        ? this.userAllowedStages.map(Number)
        : [];
      if (
        allowed.includes(1) ||
        allowed.includes(8) ||
        allowed.includes(9)
      ) {
        return true;
      }
      return [8, 9].includes(Number(this.currentStage));
    },

    getStage8MissingFields() {
      if (Number(this.currentStage) !== 8 || !this.form) return [];
      const isEmpty = (v) =>
        v === null || v === undefined || String(v).trim() === "";
      const missing = [];
      if (isEmpty(this.form.registration_section)) missing.push("بخش ثبتی");
      if (isEmpty(this.form.main_plaque)) missing.push("پلاک اصلی");
      if (isEmpty(this.form.separated_plaque)) missing.push("پلاک مفروز");
      if (isEmpty(this.form.sub_plaque)) missing.push("فرعی از");
      if (isEmpty(this.form.plot_number)) missing.push("شماره قطعه");
      const baseCost = Number(this.form.base_cost_without_loan);
      if (
        isEmpty(this.form.base_cost_without_loan) ||
        Number.isNaN(baseCost) ||
        baseCost <= 0
      ) {
        missing.push("قیمت تمام‌شده بدون وام بانکی");
      }
      return missing;
    },

    getStage21MissingFields() {
      if (Number(this.currentStage) !== 21 || !this.form) return [];
      const isEmpty = (v) =>
        v === null || v === undefined || String(v).trim() === "";
      const missing = [];
      if (isEmpty(this.form.lease_contract_number)) {
        missing.push("شماره سند قرارداد اجاره");
      }
      if (isEmpty(this.form.lease_contract_date)) {
        missing.push("تاریخ قرارداد اجاره");
      }
      if (!this.hasLeaseContractAttachment()) {
        missing.push("اسکن سند قرارداد اجاره");
      }
      return missing;
    },

    getCurrentStageMissingFields() {
      const stg = Number(this.currentStage);
      if (stg === 8) return this.getStage8MissingFields();
      if (stg === 21) return this.getStage21MissingFields();
      return [];
    },

    _validateBeforeSign() {
      const stg = Number(this.currentStage);
      const missing = this.getCurrentStageMissingFields();
      if (missing.length > 0) {
        if (stg === 8) {
          this.triggerToast(
            `امکان امضای مرحله ۸ وجود ندارد؛ لطفاً ابتدا فیلدهای الزامی زیر را تکمیل نمایید: ${missing.join("، ")}`,
            "error",
          );
          const targetId =
            missing.length === 1 && missing[0].includes("قیمت")
              ? "#section-cost"
              : "#section-plot";
          this.tab = "form";
          this.$nextTick(() => this.scrollToActiveSection(targetId));
          return false;
        }
        if (stg === 21) {
          this.triggerToast(
            `برای ادامه و تایید مرحله ۲۱، تکمیل موارد زیر الزامی است: ${missing.join("، ")}`,
            "error",
          );
          this.tab = "form";
          this.$nextTick(() => {
            this.scrollToActiveSection("#section-lease-contract");
            if (!this.hasLeaseContractAttachment()) {
              this.openUploadScanModal("LEASE_CONTRACT", "اسکن سند قرارداد اجاره عرصه");
            }
          });
          return false;
        }
      }
      return true;
    },

    isStage8User() {
      if (this.isSuperuser || this.isChief) return true;
      if (this.userAllowedStages === "all") return true;
      if (
        Array.isArray(this.userAllowedStages) &&
        (this.userAllowedStages.includes(8) ||
          this.userAllowedStages.includes("8"))
      ) {
        return true;
      }
      return Number(this.currentStage) === 8;
    },

    canSignCurrentStage() {
      if (this.isLocked || this.isRejected || this.isRedJ || this.isViewOnly) return false;
      if (!this.userCanAction) return false;
      if ([17, 18].includes(Number(this.currentStage))) {
        return Boolean(
          this.isCheckAdmin ||
          this.isChief ||
          this.isSuperuser ||
          this.userAllowedStages === "all"
        );
      }
      return true;
    },

    getFormJAttachment() {
      return (this.attachments || []).find(
        (a) => a.type === "FORM_J" || a.doc_type === "FORM_J",
      );
    },
    hasFormJ() {
      return Boolean(this.getFormJAttachment());
    },

    getDeedAttachment() {
      return (this.attachments || []).find(
        (a) =>
          a.type === "TITLE_DEED" ||
          a.doc_type === "TITLE_DEED" ||
          a.type === "LAND_DEED" ||
          a.doc_type === "LAND_DEED" ||
          (a.title && a.title.includes("سند")),
      );
    },
    hasDeedAttachment() {
      return Boolean(this.getDeedAttachment());
    },

    getNotaryAttachment() {
      return (this.attachments || []).find(
        (a) =>
          a.type === "NOTARY_LETTER" ||
          a.doc_type === "NOTARY_LETTER" ||
          (a.title && (a.title.includes("محضر") || a.title.includes("دفترخانه"))),
      );
    },
    hasNotaryAttachment() {
      return Boolean(this.getNotaryAttachment());
    },

    getLeaseContractAttachment() {
      return (this.attachments || []).find(
        (a) =>
          a.type === "LEASE_CONTRACT" ||
          a.doc_type === "LEASE_CONTRACT" ||
          (a.title && a.title.includes("قرارداد اجاره")),
      );
    },
    hasLeaseContractAttachment() {
      return Boolean(this.getLeaseContractAttachment());
    },

    // --------------------------------------------------------------------------
    // BankCheckTracker & TashilatCheck Dynamic Helpers
    // --------------------------------------------------------------------------
    calculateCheckInstallments(totalRials, count) {
      const ONE_MILLION_TOMAN = 10000000;
      const total = Math.max(0, Number(totalRials) || 0);
      const n = Math.max(1, Number(count) || 1);
      if (total === 0) return { baseCheck: 0, lastCheck: 0 };
      const totalMillionToman = Math.floor(total / ONE_MILLION_TOMAN);
      const baseMillionToman = Math.floor(totalMillionToman / n);
      let baseCheck = 0;
      let lastCheck = 0;
      if (baseMillionToman > 0) {
        baseCheck = baseMillionToman * ONE_MILLION_TOMAN;
        lastCheck = total - baseCheck * (n - 1);
      } else {
        baseCheck = Math.floor(total / n);
        lastCheck = total - baseCheck * (n - 1);
      }
      return { baseCheck, lastCheck };
    },

    parseRawNumber(val) {
      if (val === null || val === undefined) return 0;
      let s = String(val);
      s = s.replace(/[۰-۹]/g, (d) =>
        String.fromCharCode(d.charCodeAt(0) - 1776 + 48),
      );
      s = s.replace(/[٠-٩]/g, (d) =>
        String.fromCharCode(d.charCodeAt(0) - 1632 + 48),
      );
      s = s.replace(/[^\d]/g, "");
      return s ? parseInt(s, 10) : 0;
    },

    updateFormattedAmount(obj, key, event) {
      const input = event.target;
      const raw = input.value;
      const oldCursor = input.selectionEnd || 0;
      const oldLength = raw.length;
      const numeric = this.parseRawNumber(raw);
      obj[key] = numeric;
      if (numeric > 0) {
        const formatted = this.formatNumber(numeric);
        input.value = formatted;
        const diff = formatted.length - oldLength;
        const newCursor = Math.max(0, oldCursor + diff);
        if (input.setSelectionRange) {
          try {
            input.setSelectionRange(newCursor, newCursor);
          } catch (e) {}
        }
      } else if (raw === "" || raw === "0") {
        input.value = raw;
      }
    },

    formatAmountOnBlur(obj, key, event) {
      const numeric = Number(obj[key]) || 0;
      if (numeric > 0) {
        event.target.value = this.formatNumber(numeric);
      } else {
        event.target.value = "";
      }
    },

    generateChecksAuto() {
      const count = Math.max(
        1,
        Math.min(12, Number(this.checkGenerator.count) || 4),
      );
      const totalAmount =
        Number(this.form.decile_loan_amount) ||
        Number(this.form.total_check_amount) ||
        0;
      let startDate = this.checkGenerator.startDate;
      if (!startDate) {
        startDate = this.addYearsToJalali(this.getTodayJalali(), 1);
        this.checkGenerator.startDate = startDate;
      }

      const { baseCheck, lastCheck } = this.calculateCheckInstallments(
        totalAmount,
        count,
      );

      const newEntries = [];
      for (let i = 0; i < count; i++) {
        const dueDate = this.advanceJalaliDate(
          startDate,
          i,
          this.checkGenerator.interval,
        );
        const amt = i === count - 1 ? lastCheck : baseCheck;
        const existingSayadi =
          this.form.check_entries && this.form.check_entries[i]
            ? this.form.check_entries[i].check_sayadi_code || ""
            : "";
        const existingBank =
          this.form.check_entries && this.form.check_entries[i]
            ? this.form.check_entries[i].bank_name || ""
            : "";
        newEntries.push({
          row_number: i + 1,
          cash_date: dueDate,
          check_amount: amt,
          check_sayadi_code: existingSayadi,
          bank_name: existingBank,
        });
      }

      this.form.check_entries = newEntries;
      this.recalculateChecks();
      this.triggerToast(
        `تعداد ${count} فقره چک با تاریخ‌های سررسید خودکار و مبالغ متوازن ایجاد گردید.`,
        "success",
      );
    },

    addCheckEntry() {
      if (!this.form.check_entries) this.form.check_entries = [];
      const count = this.form.check_entries.length;
      const lastEntry = count > 0 ? this.form.check_entries[count - 1] : null;
      const firstEntry = count > 0 ? this.form.check_entries[0] : null;

      let nextDate = "";
      if (lastEntry && lastEntry.cash_date) {
        nextDate = this.addYearsToJalali(lastEntry.cash_date, 1);
      } else if (firstEntry && firstEntry.cash_date) {
        nextDate = this.addYearsToJalali(firstEntry.cash_date, count);
      } else {
        nextDate = this.addYearsToJalali(this.getTodayJalali(), count + 1);
      }

      const nextAmount = lastEntry ? lastEntry.check_amount || 0 : 0;
      const nextBank =
        lastEntry && lastEntry.bank_name ? lastEntry.bank_name : "";

      this.form.check_entries.push({
        row_number: count + 1,
        cash_date: nextDate,
        check_amount: nextAmount,
        check_sayadi_code: "",
        bank_name: nextBank,
      });
      this.recalculateChecks();
      this.triggerToast(
        `چک ردیف ${count + 1} با سررسید خودکار (${nextDate}) اضافه گردید.`,
        "info",
      );
    },

    removeCheckEntry(idx) {
      if (!this.form.check_entries) return;
      if (this.form.check_entries.length > 1) {
        this.form.check_entries.splice(idx, 1);
      } else {
        this.form.check_entries[0] = {
          row_number: 1,
          cash_date: "",
          check_amount: 0,
          check_sayadi_code: "",
          bank_name: "",
        };
      }
      this.form.check_entries.forEach((c, i) => (c.row_number = i + 1));
      this.recalculateChecks();
    },

    recalculateChecks() {
      if (!this.form.check_entries || !Array.isArray(this.form.check_entries))
        return;
      let total = 0;
      this.form.check_entries.forEach((c) => {
        const val = Number(c.check_amount) || 0;
        total += val;
      });
      this.form.total_check_amount = total;
      this.form.check_count = this.form.check_entries.length;
      if (this.form.check_entries.length > 0) {
        this.form.check_amount = this.form.check_entries[0].check_amount || 0;
        this.form.last_check_amount =
          this.form.check_entries[this.form.check_entries.length - 1]
            .check_amount || 0;
      }
    },

    // --------------------------------------------------------------------------
    // Interactive Persian Date Picker Modal Handlers
    // --------------------------------------------------------------------------
    openDatePicker(targetField, currentValue, title) {
      this.datePickerModal.targetField = targetField;
      this.datePickerModal.title = title || "انتخاب تاریخ شمسی";

      const parsed =
        this.parseJalaliDate(currentValue) ||
        this.parseJalaliDate(this.getTodayJalali());
      this.datePickerModal.year = parsed.year;
      this.datePickerModal.month = parsed.month;
      this.datePickerModal.day = parsed.day;
      this.normalizePickerDay();
      this.datePickerModal.isOpen = true;
    },

    closeDatePicker() {
      this.datePickerModal.isOpen = false;
    },

    normalizePickerDay() {
      const maxD = this.getDaysInJalaliMonth(
        this.datePickerModal.year,
        this.datePickerModal.month,
      );
      if (this.datePickerModal.day > maxD) {
        this.datePickerModal.day = maxD;
      }
    },

    setPickerYear(y) {
      this.datePickerModal.year = Number(y);
      this.normalizePickerDay();
    },

    setPickerMonth(m) {
      this.datePickerModal.month = Number(m);
      this.normalizePickerDay();
    },

    setPickerDay(d) {
      this.datePickerModal.day = Number(d);
    },

    setPickerPreset(preset) {
      const today = this.parseJalaliDate(this.getTodayJalali());
      if (preset === "today") {
        this.datePickerModal.year = today.year;
        this.datePickerModal.month = today.month;
        this.datePickerModal.day = today.day;
      } else if (
        typeof preset === "number" ||
        (typeof preset === "string" && preset.startsWith("+"))
      ) {
        const addYears =
          parseInt(String(preset).replace("+", "").replace("y", ""), 10) || 1;
        this.datePickerModal.year = today.year + addYears;
        this.datePickerModal.month = today.month;
        this.datePickerModal.day = today.day;
      }
      this.normalizePickerDay();
    },

    applyDatePicker() {
      const formatted = this.formatJalaliDate(
        this.datePickerModal.year,
        this.datePickerModal.month,
        this.datePickerModal.day,
      );
      const field = this.datePickerModal.targetField;
      if (field.startsWith("prep_check_")) {
        const idx = parseInt(field.split("_")[2], 10);
        if (
          this.form.preparation_check_entries &&
          this.form.preparation_check_entries[idx]
        ) {
          this.form.preparation_check_entries[idx].cash_date = formatted;
        }
      } else if (field === "prepCheckGenerator.startDate") {
        this.prepCheckGenerator.startDate = formatted;
      } else if (field.startsWith("check_")) {
        const idx = parseInt(field.split("_")[1], 10);
        if (this.form.check_entries && this.form.check_entries[idx]) {
          this.form.check_entries[idx].cash_date = formatted;
        }
      } else if (field === "checkGenerator.startDate") {
        this.checkGenerator.startDate = formatted;
      } else {
        this.form[field] = formatted;
      }
      this.datePickerModal.isOpen = false;
      this.triggerToast(`تاریخ (${formatted}) ثبت گردید.`, "info");
    },

    clearDatePickerField() {
      const field = this.datePickerModal.targetField;
      if (field.startsWith("prep_check_")) {
        const idx = parseInt(field.split("_")[2], 10);
        if (
          this.form.preparation_check_entries &&
          this.form.preparation_check_entries[idx]
        ) {
          this.form.preparation_check_entries[idx].cash_date = "";
        }
      } else if (field === "prepCheckGenerator.startDate") {
        this.prepCheckGenerator.startDate = "";
      } else if (field.startsWith("check_")) {
        const idx = parseInt(field.split("_")[1], 10);
        if (this.form.check_entries && this.form.check_entries[idx]) {
          this.form.check_entries[idx].cash_date = "";
        }
      } else if (field === "checkGenerator.startDate") {
        this.checkGenerator.startDate = "";
      } else {
        this.form[field] = "";
      }
      this.datePickerModal.isOpen = false;
      this.triggerToast("تاریخ پاک شد.", "info");
    },

    // --------------------------------------------------------------------------
    // tashilatCheck: Preparation Installment Checks Dynamic Helpers (آماده‌سازی)
    // --------------------------------------------------------------------------
    generatePrepChecksAuto() {
      const count = Math.max(
        1,
        Math.min(10, Number(this.prepCheckGenerator.count) || 3),
      );
      const totalAmount =
        Number(this.form.non_cash_preparation_amount) ||
        Number(this.form.total_preparation_check_amount) ||
        0;
      let startDate = this.prepCheckGenerator.startDate;
      if (!startDate) {
        startDate = this.addSixMonthsCustomJalali(this.getTodayJalali());
        this.prepCheckGenerator.startDate = startDate;
      }

      const { baseCheck, lastCheck } = this.calculateCheckInstallments(
        totalAmount,
        count,
      );

      const newEntries = [];
      let curDate = startDate;
      for (let i = 0; i < count; i++) {
        const dueDate =
          i === 0 ? startDate : this.addSixMonthsCustomJalali(curDate);
        curDate = dueDate;
        const amt = i === count - 1 ? lastCheck : baseCheck;
        const existingSayadi =
          this.form.preparation_check_entries &&
          this.form.preparation_check_entries[i]
            ? this.form.preparation_check_entries[i].check_sayadi_code || ""
            : "";
        const existingBank =
          this.form.preparation_check_entries &&
          this.form.preparation_check_entries[i]
            ? this.form.preparation_check_entries[i].bank_name || ""
            : "";
        newEntries.push({
          row_number: i + 1,
          cash_date: dueDate,
          check_amount: amt,
          check_sayadi_code: existingSayadi,
          bank_name: existingBank,
        });
      }

      this.form.preparation_check_entries = newEntries;
      this.recalculatePrepChecks();
      this.triggerToast(
        `تعداد ${count} فقره چک اقساط آماده‌سازی با سررسیدهای ۶ ماهه ایجاد گردید.`,
        "success",
      );
    },

    addPrepCheckEntry() {
      if (!this.form.preparation_check_entries)
        this.form.preparation_check_entries = [];
      const count = this.form.preparation_check_entries.length;
      const lastEntry =
        count > 0 ? this.form.preparation_check_entries[count - 1] : null;

      let nextDate = "";
      if (lastEntry && lastEntry.cash_date) {
        nextDate = this.addSixMonthsCustomJalali(lastEntry.cash_date);
      } else {
        nextDate = this.addSixMonthsCustomJalali(this.getTodayJalali());
      }

      const nextAmount = lastEntry ? lastEntry.check_amount || 0 : 0;
      const nextBank =
        lastEntry && lastEntry.bank_name ? lastEntry.bank_name : "";

      this.form.preparation_check_entries.push({
        row_number: count + 1,
        cash_date: nextDate,
        check_amount: nextAmount,
        check_sayadi_code: "",
        bank_name: nextBank,
      });
      this.recalculatePrepChecks();
      this.triggerToast(
        `چک آماده‌سازی ردیف ${count + 1} با سررسید خودکار (${nextDate}) اضافه گردید.`,
        "info",
      );
    },

    removePrepCheckEntry(idx) {
      if (!this.form.preparation_check_entries) return;
      if (this.form.preparation_check_entries.length > 1) {
        this.form.preparation_check_entries.splice(idx, 1);
      } else {
        this.form.preparation_check_entries[0] = {
          row_number: 1,
          cash_date: "",
          check_amount: 0,
          check_sayadi_code: "",
          bank_name: "",
        };
      }
      this.form.preparation_check_entries.forEach(
        (c, i) => (c.row_number = i + 1),
      );
      this.recalculatePrepChecks();
    },

    recalculatePrepChecks() {
      if (
        !this.form.preparation_check_entries ||
        !Array.isArray(this.form.preparation_check_entries)
      )
        return;
      let total = 0;
      this.form.preparation_check_entries.forEach((c) => {
        const val = Number(c.check_amount) || 0;
        total += val;
      });
      this.form.total_preparation_check_amount = total;
      this.form.preparation_check_count =
        this.form.preparation_check_entries.length;
    },

    getAppraisalCash() {
      const prep = Math.max(0, Number(this.form.preparation_cost) || 0);
      return prep - this.getAppraisalInstallment();
    },

    getAppraisalInstallment() {
      const prep = Math.max(0, Number(this.form.preparation_cost) || 0);
      if (prep <= 0) return 0;
      const ROUND_UNIT = 10000000;
      return Math.floor(Math.round(prep * 0.8) / ROUND_UNIT) * ROUND_UNIT;
    },

    getAppraisalRent() {
      const past = Number(this.form.past_years_rent) || 0;
      const curr = Number(this.form.current_year_rent) || 0;
      return past + curr;
    },

    applyAppraisalCash() {
      this.form.cash_preparation_amount = this.getAppraisalCash();
      this.triggerToast("مبلغ ۲۰٪ نقد ارزیابی آماده‌سازی اعمال گردید.", "info");
    },

    applyAppraisalInstallment() {
      this.form.non_cash_preparation_amount = this.getAppraisalInstallment();
      this.generatePrepChecksAuto();
      this.triggerToast(
        "مبلغ ۸۰٪ اقساط ارزیابی آماده‌سازی اعمال و اقلام چک‌ها تولید گردید.",
        "info",
      );
    },

    applyAppraisalRent() {
      this.form.tenant_price = this.getAppraisalRent();
      this.triggerToast(
        "مجموع مبالغ اجاره سنوات و سال جاری اعمال گردید.",
        "info",
      );
    },

    // Forward & Sign
    openSignatureModal() {
      if (!this._validateBeforeSign()) {
        return;
      }
      this.signerPin = "";
      this.signAgreement = true;
      this.showSignatureModal = true;
    },

    async confirmOutOfOrderStageSign(targetStage) {
      const stageLabel = targetStage === 17 ? "۱۷ (تسهیلات چک)" : "۱۸ (آماده‌سازی)";
      if (!confirm(`آیا از تایید و امضای الکترونیک خارج از نوبت مرحله ${stageLabel} اطمینان دارید؟`)) {
        return;
      }
      const saved = await this.saveDossierDraft(false);
      if (!saved) {
        this.triggerToast("ذخیره‌سازی اطلاعات ناموفق بود. امضا لغو شد.", "error");
        return;
      }
      const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/sign/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            target_stage: targetStage,
            notes: `تایید و امضای خارج از نوبت مرحله ${targetStage} با موفقیت ثبت شد.`,
          }),
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
          if (!this.stageSignatures) this.stageSignatures = {};
          this.stageSignatures[targetStage] = {
            actor: "کاربر مجاز",
            date: this.getTodayJalali(),
            action: "SIGN",
            action_label: `تایید و امضای خارج از نوبت مرحله ${targetStage}`,
          };
          this.triggerToast(data.message || `مرحله ${stageLabel} امضا شد.`, "success");
          setTimeout(() => window.location.reload(), 900);
        } else {
          this.triggerToast(data.message || "خطا در ثبت امضا", "error");
        }
      } catch (err) {
        this.triggerToast("خطا در ارتباط با سرور: " + err.message, "error");
      }
    },

    async confirmElectronicSignature() {
      if (!this._validateBeforeSign()) {
        this.showSignatureModal = false;
        return;
      }
      // First save current form edits to database
      const saved = await this.saveDossierDraft(false);
      if (!saved) {
        this.triggerToast(
          "ذخیره‌سازی اطلاعات ناموفق بود. امضای الکترونیکی لغو شد.",
          "error",
        );
        this.showSignatureModal = false;
        return;
      }

      const csrfToken =
        document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/sign/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            notes: `تایید و امضای الکترونیکی مرحله ${this.currentStage} با موفقیت ثبت شد.`,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          const prevStage = Number(this.currentStage);
          this.currentStage = Number(data.new_stage);
          if (data.is_locked) this.isLocked = true;

          const fromInfo = this.getStage(prevStage);
          const toInfo = this.getStage(this.currentStage);

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${prevStage}: ${fromInfo.title}`,
            toStage:
              this.currentStage <= 22
                ? `مرحله ${this.currentStage}: ${toInfo.title}`
                : "خاتمه و بایگانی قطعی",
            actor: "کاربر ارشد سازمانی",
            role: fromInfo.role,
            action: "SIGN",
            actionLabel: "تایید و امضای دیجیتال",
            timestamp:
              new Date().toLocaleDateString("fa-IR") +
              " " +
              new Date().toLocaleTimeString("fa-IR", {
                hour: "2-digit",
                minute: "2-digit",
              }),
            hash: data.hash,
            notes: `تایید و امضای الکترونیکی مرحله ${prevStage} با موفقیت در سامانه ثبت شد.`,
          });

          if (
            prevStage === 7 &&
            Number(data.new_stage) >= 8 &&
            data.dossier_status !== "REJECT_RED_PENDING"
          ) {
            this.issuedArchiveInfo = {
              archive_number: data.archive_number || this.archiveNumber,
              full_name:
                (this.form && this.form.full_name) || data.full_name || "",
              national_id:
                (this.form && this.form.national_id) || data.national_id || "",
              new_stage: Number(data.new_stage),
              redirect_url: data.redirect_url || "",
            };
            this.archiveCopied = false;
            this.showSignatureModal = false;
            this.showArchiveIssuedModal = true;
            return;
          }

          this.triggerToast(
            data.message || `پرونده به مرحله ${this.currentStage} منتقل شد.`,
            "success",
          );
          setTimeout(() => {
            if (data.redirect_url) {
              window.location.href = data.redirect_url;
            } else {
              window.location.reload();
            }
          }, 600);
        } else {
          const errData = await res.json().catch(() => ({}));
          this.triggerToast(
            errData.message || "خطا در ثبت امضای الکترونیکی.",
            "error",
          );
        }
      } catch (err) {
        console.error("Signature error:", err);
        this.triggerToast("خطا در ارسال درخواست امضا به سرور.", "error");
      } finally {
        this.showSignatureModal = false;
      }
    },

    copyIssuedArchiveNumber() {
      const val = String(
        this.issuedArchiveInfo.archive_number || this.archiveNumber || "",
      );
      if (!val) return;
      const onCopied = () => {
        this.archiveCopied = true;
        this.triggerToast(`شماره بایگانی ${val} کپی شد.`, "success");
        setTimeout(() => {
          this.archiveCopied = false;
        }, 2500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(val).then(onCopied).catch(() => {});
      } else {
        const ta = document.createElement("textarea");
        ta.value = val;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          onCopied();
        } catch (e) {}
        document.body.removeChild(ta);
      }
    },

    closeArchiveIssuedModal() {
      const target = this.issuedArchiveInfo.redirect_url;
      this.showArchiveIssuedModal = false;
      if (target) {
        window.location.href = target;
      } else {
        window.location.reload();
      }
    },

    // Return Modal
    openReturnModal() {
      this.selectedReturnStage = Math.max(1, this.currentStage - 1);
      this.returnNotes = "";
      this.showReturnModal = true;
    },

    getAvailableReturnStages() {
      return this.stages.filter((s) => s.id < this.currentStage);
    },

    async confirmReturnForCorrection() {
      if (!this.returnNotes || this.returnNotes.trim().length < 5) {
        this.triggerToast(
          "ثبت توضیحات دلیل برگشت پرونده الزامی است (حداقل ۵ کاراکتر).",
          "error",
        );
        return;
      }

      const targetStage = this.selectedReturnStage;
      const csrfToken =
        document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";

      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/return/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            target_stage: targetStage,
            notes: this.returnNotes,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          const prevStage = this.currentStage;
          this.currentStage = data.new_stage;

          const fromInfo = this.getStage(prevStage);
          const targetInfo = this.getStage(targetStage);

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${prevStage}: ${fromInfo.title}`,
            toStage: `مرحله ${targetStage}: ${targetInfo.title}`,
            actor: "کارشناس بررسی و ممیزی",
            role: fromInfo.role,
            action: "RETURN",
            actionLabel: "برگشت جهت اصلاح",
            timestamp:
              new Date().toLocaleDateString("fa-IR") +
              " " +
              new Date().toLocaleTimeString("fa-IR", {
                hour: "2-digit",
                minute: "2-digit",
              }),
            hash: data.hash,
            notes: this.returnNotes,
          });

          this.triggerToast(
            data.message || `پرونده به مرحله ${targetStage} بازگشت داده شد.`,
            "warning",
          );
          setTimeout(() => {
            if (data.redirect_url) {
              window.location.href = data.redirect_url;
            } else {
              window.location.reload();
            }
          }, 600);
        } else {
          const errData = await res.json().catch(() => ({}));
          this.triggerToast(
            errData.message || "خطا در ثبت بازگشت پرونده.",
            "error",
          );
        }
      } catch (err) {
        console.error("Return error:", err);
        this.triggerToast("خطا در ارسال درخواست بازگشت به سرور.", "error");
      } finally {
        this.showReturnModal = false;
      }
    },

    // General Dossier Deletion & Archival Handlers
    openDeleteModal() {
      this.deleteReason = "";
      this.showDeleteModal = true;
    },

    async confirmDeleteDossier() {
      if (!this.deleteReason || !this.deleteReason.trim()) {
        this.triggerToast("لطفاً علت حذف پرونده را مرقوم فرمایید.", "warning");
        return;
      }
      this.isSaving = true;
      try {
        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        const res = await fetch(`/dossier/${this.archiveNumber}/delete-archive/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            reason: this.deleteReason.trim(),
          }),
        });
        if (res.ok) {
          const data = await res.json();
          this.status = data.dossier_status || "DELETED";
          this.isLocked = Boolean(data.is_locked);
          this.isDeleted = true;
          this.deletionReason = data.deletion_reason;
          this.deletedBy = data.deleted_by;
          this.showDeleteModal = false;
          this.triggerToast(
            data.message || "پرونده با موفقیت حذف و به بایگانی راکد منتقل گردید.",
            "success"
          );
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          const err = await res.json().catch(() => ({}));
          this.triggerToast(err.message || "خطا در حذف پرونده.", "error");
        }
      } catch (e) {
        console.error("Delete error:", e);
        this.triggerToast("خطا در برقراری ارتباط با سرور.", "error");
      } finally {
        this.isSaving = false;
      }
    },

    async restoreDeletedDossier() {
      if (!confirm("آیا از بازیابی این پرونده و بازگردانی آن به چرخه فعال اطمینان دارید؟")) {
        return;
      }
      this.isSaving = true;
      try {
        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        const res = await fetch(`/dossier/${this.archiveNumber}/restore/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
        });
        if (res.ok) {
          const data = await res.json();
          this.status = data.dossier_status || "IN_PROGRESS";
          this.isLocked = false;
          this.isDeleted = false;
          this.triggerToast(data.message || "پرونده با موفقیت بازیابی شد.", "success");
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          const err = await res.json().catch(() => ({}));
          this.triggerToast(err.message || "خطا در بازیابی پرونده.", "error");
        }
      } catch (e) {
        console.error("Restore error:", e);
        this.triggerToast("خطا در برقراری ارتباط با سرور.", "error");
      } finally {
        this.isSaving = false;
      }
    },

    // Red Form J Disqualification & Archival Handler
    openRedRejectionModal() {
      this.redLetterNumber =
        this.rejectionLetterNumber || "1403/رد/" + this.archiveNumber;
      this.redLetterDate = this.rejectionLetterDate || this.getTodayJalali();
      this.redLetterReason =
        this.rejectionReason ||
        this.form.applicant_form_j_red_description ||
        this.form.spouse_form_j_red_description ||
        "دارای سابقه مسکن دولتی و فاقد شرایط قانونی دریافت واحد";
      this.showRedRejectionModal = true;
    },

    async confirmRedRejection() {
      this.isSaving = true;
      try {
        const csrfToken =
          document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        const res = await fetch(`/dossier/${this.archiveNumber}/reject-red/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            letter_number: this.redLetterNumber,
            letter_date: this.redLetterDate,
            reason: this.redLetterReason,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          this.status = data.dossier_status || "REJECTED_RED";
          this.isLocked = Boolean(data.is_locked);
          this.isRejected = true;
          this.rejectionLetterNumber = data.rejection_letter_number;
          this.rejectionLetterDate = data.rejection_letter_date;
          this.rejectionReason = data.rejection_reason;
          this.rejectedBy = data.rejected_by;
          this.showRedRejectionModal = false;
          this.triggerToast(
            data.message ||
              "نامه رد صلاحیت صادر و پرونده با موفقیت بایگانی گردید.",
            "success",
          );
          setTimeout(() => {
            window.location.reload();
          }, 1200);
        } else {
          const err = await res.json().catch(() => ({}));
          this.triggerToast(
            err.message || "خطا در صدور ابلاغیه رد صلاحیت.",
            "error",
          );
        }
      } catch (e) {
        console.error("Red rejection error:", e);
        this.triggerToast("خطا در برقراری ارتباط با سرور.", "error");
      } finally {
        this.isSaving = false;
      }
    },

    openRedReturnModal() {
      this.redReturnStage = 0;
      this.redReturnNotes = "";
      this.redResetFormJ = true;
      this.showRedReturnModal = true;
    },

    async confirmRedReturnForCorrection() {
      if (!this.redReturnNotes || this.redReturnNotes.trim().length < 5) {
        this.triggerToast(
          "ثبت دستور اداری / علت بازگشت پرونده الزامی است (حداقل ۵ کاراکتر).",
          "error",
        );
        return;
      }

      this.isSaving = true;
      try {
        const csrfToken =
          document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        const res = await fetch(`/dossier/${this.archiveNumber}/return-red/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            target_stage: this.redReturnStage,
            notes: this.redReturnNotes,
            reset_form_j: this.redResetFormJ,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          this.status = data.dossier_status || "RETURNED";
          this.isLocked = Boolean(data.is_locked);
          this.isRejected = false;
          this.currentStage = data.new_stage;
          if (data.applicant_form_j_status) {
            this.form.applicant_form_j_status = data.applicant_form_j_status;
          }
          if (data.spouse_form_j_status) {
            this.form.spouse_form_j_status = data.spouse_form_j_status;
          }
          this.isRedFormJ =
            (this.form.applicant_form_j_status &&
              this.form.applicant_form_j_status.includes("قرمز")) ||
            (this.form.spouse_form_j_status &&
              this.form.spouse_form_j_status.includes("قرمز"));
          this.showRedReturnModal = false;
          this.triggerToast(
            data.message ||
              "پرونده با موفقیت بازگردانده شد و قفل آن باز گردید.",
            "success",
          );
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          const err = await res.json().catch(() => ({}));
          this.triggerToast(
            err.message || "خطا در بازگشت پرونده جهت اصلاح.",
            "error",
          );
        }
      } catch (e) {
        console.error("Red return error:", e);
        this.triggerToast("خطا در برقراری ارتباط با سرور.", "error");
      } finally {
        this.isSaving = false;
      }
    },

    // Auto-fill PreSelectedUnit at Stage 1 from backend database
    async fetchPreSelectedUnit() {
      if (
        !this.form.national_id ||
        this.form.national_id.trim().length !== 10
      ) {
        this.triggerToast("کد ملی وارد شده باید دقیقاً ۱۰ رقم باشد.", "error");
        return;
      }
      try {
        const cleanNatId = this.form.national_id.trim();
        const res = await fetch(`/api/lookup-unit/?national_id=${cleanNatId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "success") {
            for (const [key, val] of Object.entries(data)) {
              if (key !== "status" && key in this.form) {
                this.form[key] = val;
              }
            }
            this.recalculateEquity();
            this.triggerToast(
              "اطلاعات متقاضی، همسر و واحد مسکونی با موفقیت از پایگاه داده بارگذاری شد.",
              "success",
            );
            return;
          }
        }
        this.triggerToast(
          "اطلاعاتی با این کد ملی در بانک انتخاب واحد یافت نشد.",
          "error",
        );
      } catch (err) {
        console.error("Fetch preselected unit error:", err);
        this.triggerToast("خطا در واکشی اطلاعات از سامانه.", "error");
      }
    },

    async recalculateLandRates() {
      const code = (this.form.renovation_code || "").trim();
      const project = (this.form.project || "").trim();
      const plot = String(this.form.plot_number || "").trim();
      const block = (this.form.block_name || this.form.block_code || "").trim();
      const site = (this.form.site || "").trim();
      const constructionType = (this.form.construction_type || "").trim();
      const mainPlaque = String(this.form.main_plaque ?? "").trim();
      const separatedPlaque = String(this.form.separated_plaque ?? "").trim();
      const subPlaque = String(this.form.sub_plaque ?? "").trim();
      const isVilla = this.isVillaConstruction();

      if (isVilla ? (!mainPlaque && !separatedPlaque && !subPlaque) : (!code && !project && !plot && !block)) {
        this.triggerToast("لطفاً حداقل نام پروژه و کد بلوک (یا کد نوسازی) را مشخص فرمایید.", "warning");
        return;
      }
      const net = this.form.net_unit_area || this.form.unit_area || 0;
      const storage = this.form.storage_area || 0;
      const parking = this.form.parking_area || 0;
      const landArea = this.form.total_land_share || 0;
      try {
        const params = new URLSearchParams({
          code: code,
          project: project,
          plot: plot,
          block: block,
          block_code: block,
          site: site,
          construction_type: constructionType,
          main_plaque: mainPlaque,
          separated_plaque: separatedPlaque,
          sub_plaque: subPlaque,
          land_area: landArea,
          net: net,
          storage: storage,
          parking: parking,
        });
        const resp = await fetch(`/api/calculate-land-rates/?${params.toString()}`);
        const res = await resp.json();
        if (res.success && res.data) {
          const d = res.data;
          if (d.total_land_share !== undefined && d.total_land_share !== null && Number(d.total_land_share) > 0) { this.form.total_land_share = d.total_land_share; }
          this.form.land_lease_year = d.land_lease_year;
          this.form.preparation_cost = d.preparation_cost;
          this.form.past_years_rent = d.past_years_rent;
          this.form.current_year_rent = d.current_year_rent;
          this.landRateInfo = {
            rate_type: d.rate_type || "apartment",
            registry_plaque: d.registry_plaque || "",
            street_width: d.street_width || "",
            allocation_type: d.allocation_type || "",
            land_area: d.land_area || "0",
            rent_current: Number(d.rent_current || 0),
            rent_to_date: Number(d.rent_to_date || 0),
            preparation_cost: Number(d.preparation_cost || 0),
            renovation_code: d.renovation_code || "",
            project_name: d.project_name || "",
            block_name: d.block_name || "",
            plot_number: d.plot_number || "",
            share_coefficient: d.share_coefficient || "0",
            rent_current_per_m2: Number(d.rent_current_per_m2 || 0),
            rent_to_date_per_m2: Number(d.rent_to_date_per_m2 || 0),
            prep_per_m2: Number(d.prep_per_m2 || 0),
          };
          if (!this.form.renovation_code && d.renovation_code) {
            this.form.renovation_code = d.renovation_code;
          }
          if (!this.form.plot_number && d.plot_number) {
            this.form.plot_number = d.plot_number;
          }
          if (!this.form.block_name && d.block_name) {
            this.form.block_name = d.block_name;
          }
          this.triggerToast("ارقام بخش ۹ بر اساس نرخ مصوب با موفقیت محاسبه شدند.", "success");
        } else {
          this.triggerToast(res.error || "نرخ مصوب برای این بلوک/پروژه یافت نشد.", "error");
        }
      } catch (err) {
        console.error("Calculate land rates error:", err);
        this.triggerToast("خطا در محاسبه آنلاین: " + err.message, "error");
      }
    },

    getValuationNetArea() {
      return Number(this.form.net_unit_area || this.form.unit_area || 0) || 0;
    },

    getValuationStorageArea() {
      return Number(this.form.storage_area || 0) || 0;
    },

    getValuationParkingArea() {
      return Number(this.form.parking_area || 0) || 0;
    },

    getValuationTotalArea() {
      return (
        this.getValuationNetArea() +
        this.getValuationStorageArea() +
        this.getValuationParkingArea()
      );
    },

    fmtFormulaNumber(val, decimals = 2) {
      const n = Number(val || 0);
      if (Number.isNaN(n)) return "0";
      return String(Number(n.toFixed(decimals)));
    },

    getValuationComputedShare() {
      if (this.landRateInfo && this.landRateInfo.share_coefficient) {
        const coeff = Number(this.landRateInfo.share_coefficient || 0);
        if (!Number.isNaN(coeff)) {
          return Math.round(this.getValuationTotalArea() * coeff * 100) / 100;
        }
      }
      return Number(this.form.total_land_share || 0) || 0;
    },

    getValuationActiveShare() {
      const saved = Number(this.form.total_land_share);
      if (!Number.isNaN(saved) && saved > 0) return saved;
      return this.getValuationComputedShare();
    },

    getValuationRateAmount(rateKey) {
      if (!this.landRateInfo) return 0;
      const perM2 = Number(this.landRateInfo[rateKey] || 0);
      if (Number.isNaN(perM2)) return 0;
      return Math.round(this.getValuationActiveShare() * perM2);
    },

    toWords(num) {
      return PersianNumberWords.toWords(num);
    },

    formatNumber(num) {
      return PersianNumberWords.formatThousand(num);
    },

    toPersianDigits(num) {
      return PersianNumberWords.toPersianDigits(num);
    },

    triggerToast(msg, type = "success") {
      if (!msg || !String(msg).trim()) return;
      this.toastMessage = String(msg).trim();
      this.toastType = type;
      this.showToast = true;
      if (this._toastTimer) clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => {
        this.showToast = false;
        setTimeout(() => {
          if (!this.showToast) this.toastMessage = "";
        }, 350);
      }, 4000);
    },
  }));
});

// ==========================================================================
// Smart Auto-Hide Header and Sticky Action Bar on Scroll
// ==========================================================================
(function () {
  let lastScrollY = window.pageYOffset || document.documentElement.scrollTop;
  let ticking = false;
  const threshold = 8;

  function onScrollUpdate() {
    const currentScrollY =
      window.pageYOffset || document.documentElement.scrollTop;
    const header = document.querySelector(".sanadban-header");
    const actionBar = document.querySelector(".sticky-action-bar");
    const tabs = document.querySelector(".dt-tabs");

    // At top of page: always show
    if (currentScrollY <= 25) {
      document.body.classList.remove("nav-hidden");
      if (header) header.classList.remove("nav-hidden");
      if (actionBar) actionBar.classList.remove("nav-hidden");
      if (tabs) tabs.classList.remove("top-pinned");
      lastScrollY = currentScrollY;
      ticking = false;
      return;
    }

    const scrollHeight = document.documentElement.scrollHeight;
    const clientHeight = document.documentElement.clientHeight;
    const nearBottom = currentScrollY + clientHeight >= scrollHeight - 40;

    const diff = currentScrollY - lastScrollY;

    if (Math.abs(diff) > threshold) {
      if (diff > 0 && currentScrollY > 70) {
        // Scrolling DOWN -> Hide only the top brand header, KEEP tabs & action bar sticky and visible
        document.body.classList.add("nav-hidden");
        document.documentElement.classList.add("nav-hidden");
        if (header) header.classList.add("nav-hidden");
      } else if (diff < 0) {
        // Scrolling UP -> Reveal top brand header
        document.body.classList.remove("nav-hidden");
        document.documentElement.classList.remove("nav-hidden");
        if (header) header.classList.remove("nav-hidden");
      }
      lastScrollY = currentScrollY;
    }

    if (nearBottom && actionBar) {
      actionBar.classList.remove("nav-hidden");
    }

    ticking = false;
  }

  window.addEventListener(
    "scroll",
    function () {
      if (!ticking) {
        window.requestAnimationFrame(onScrollUpdate);
        ticking = true;
      }
    },
    { passive: true },
  );

  // Mouse hover at top/bottom zones reveals header/footer smoothly
  document.addEventListener(
    "mousemove",
    function (e) {
      if (e.clientY < 45) {
        const header = document.querySelector(".sanadban-header");
        if (header && header.classList.contains("nav-hidden")) {
          header.classList.remove("nav-hidden");
          document.body.classList.remove("nav-hidden");
        }
      } else if (e.clientY > window.innerHeight - 45) {
        const actionBar = document.querySelector(".sticky-action-bar");
        if (actionBar && actionBar.classList.contains("nav-hidden")) {
          actionBar.classList.remove("nav-hidden");
        }
      }
    },
    { passive: true },
  );
})();

// =========================================================================
// Real-Time Excel Downloader & Concurrency Guard with Speed & Progress Bar
// =========================================================================
window.SanadbanDownloader = {
  isDownloading: false,
  modalEl: null,
  xhr: null,

  ensureModal() {
    if (this.modalEl && document.body.contains(this.modalEl)) return;
    const div = document.createElement("div");
    div.id = "sb-download-tracker-modal";
    div.style.cssText = `
      position: fixed;
      bottom: 24px;
      left: 24px;
      z-index: 99999;
      width: 380px;
      max-width: 90vw;
      background: #ffffff;
      border: 1.5px solid #93c5fd;
      border-radius: 14px;
      box-shadow: 0 12px 36px rgba(15, 23, 42, 0.22);
      font-family: inherit;
      direction: rtl;
      padding: 14px 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      display: none;
    `;
    div.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <div id="sb-dl-spinner" style="width: 20px; height: 20px; border: 2.5px solid #dbeafe; border-top-color: #2563eb; border-radius: 50%; animation: sb-spin 0.8s linear infinite;"></div>
          <span id="sb-dl-title" style="font-size: 0.86rem; font-weight: 800; color: #1e3a8a;">در حال آماده‌سازی و دریافت اکسل...</span>
        </div>
        <span id="sb-dl-pct" class="fa-num" style="font-size: 0.84rem; font-weight: 800; color: #2563eb;">۰٪</span>
      </div>
      <div style="width: 100%; height: 8px; background: #f1f5f9; border-radius: 999px; overflow: hidden; margin-bottom: 8px; border: 1px solid #e2e8f0;">
        <div id="sb-dl-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #3b82f6, #1d4ed8); transition: width 0.2s ease; border-radius: 999px;"></div>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.74rem; color: #64748b;" class="fa-num">
        <span id="sb-dl-size">دریافت: در حال محاسبه...</span>
        <span id="sb-dl-speed">سرعت: در حال محاسبه...</span>
      </div>
      <div id="sb-dl-eta" style="font-size: 0.72rem; color: #0284c7; margin-top: 4px; text-align: left; font-weight: 700;" class="fa-num">
        زمان باقیمانده: چند لحظه...
      </div>
    `;
    document.body.appendChild(div);
    this.modalEl = div;

    if (!document.getElementById("sb-download-styles")) {
      const style = document.createElement("style");
      style.id = "sb-download-styles";
      style.textContent = `
        @keyframes sb-spin {
          to { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }
  },

  download(url, filename) {
    if (this.isDownloading) {
      alert(
        "یک عملیات دانلود هم‌اکنون در جریان است. لطفاً تا اتمام آن شکیبا باشید.",
      );
      return;
    }
    this.ensureModal();
    this.isDownloading = true;

    const modal = this.modalEl;
    const bar = document.getElementById("sb-dl-bar");
    const pct = document.getElementById("sb-dl-pct");
    const title = document.getElementById("sb-dl-title");
    const sizeEl = document.getElementById("sb-dl-size");
    const speedEl = document.getElementById("sb-dl-speed");
    const etaEl = document.getElementById("sb-dl-eta");
    const spinner = document.getElementById("sb-dl-spinner");

    modal.style.display = "block";
    bar.style.width = "5%";
    pct.textContent = "۵٪";
    title.textContent = "در حال ارتباط با سرور و آماده‌سازی...";
    sizeEl.textContent = "در حال شروع...";
    speedEl.textContent = "";
    etaEl.textContent = "لطفاً منتظر بمانید...";
    spinner.style.display = "block";

    const startTime = Date.now();
    let simPct = 5;
    let prepTimer = setInterval(() => {
      if (simPct < 85) {
        simPct += Math.floor(Math.random() * 6) + 3;
        if (simPct > 85) simPct = 85;
        bar.style.width = simPct + "%";
        pct.textContent = simPct.toLocaleString("fa-IR") + "٪";

        if (simPct < 25) {
          title.textContent = "در حال استخراج رکوردها از پایگاه داده...";
          sizeEl.textContent = "پردازش پرونده‌های مسکن";
        } else if (simPct < 50) {
          title.textContent = "در حال چینش ستون‌ها و محاسبات مالی...";
          sizeEl.textContent = "اعتبارسنجی ارقام و آورده‌ها";
        } else if (simPct < 75) {
          title.textContent = "در حال تولید ساختار فایل اکسل...";
          sizeEl.textContent = "اعمال استایل و فونت فارسی";
        } else {
          title.textContent = "در حال فشرده‌سازی و ارسال داده‌ها...";
          sizeEl.textContent = "آماده‌سازی انتقال";
        }
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        etaEl.textContent = `زمان سپری‌شده: ${elapsed.toLocaleString("fa-IR")} ثانیه`;
      }
    }, 700);

    const xhr = new XMLHttpRequest();
    this.xhr = xhr;
    xhr.open("GET", url, true);
    xhr.responseType = "blob";

    xhr.onprogress = (e) => {
      clearInterval(prepTimer);
      const now = Date.now();
      const elapsedSec = (now - startTime) / 1000;
      const loaded = e.loaded;
      const loadedMb = (loaded / (1024 * 1024)).toFixed(1);
      const speedBps = elapsedSec > 0 ? loaded / elapsedSec : 0;
      let speedStr = "";
      if (speedBps > 1024 * 1024) {
        speedStr = (speedBps / (1024 * 1024)).toFixed(1) + " MB/s";
      } else {
        speedStr = (speedBps / 1024).toFixed(0) + " KB/s";
      }

      if (e.lengthComputable && e.total > 0) {
        const percent = Math.min(100, Math.round((loaded / e.total) * 100));
        const totalMb = (e.total / (1024 * 1024)).toFixed(1);
        bar.style.width = percent + "%";
        pct.textContent = percent + "٪";
        title.textContent = "در حال دریافت فایل اکسل...";
        sizeEl.textContent = `${loadedMb} MB از ${totalMb} MB`;
        speedEl.textContent = "سرعت: " + speedStr;

        const remainingBytes = e.total - loaded;
        if (speedBps > 0 && remainingBytes > 0) {
          const etaSec = Math.ceil(remainingBytes / speedBps);
          etaEl.textContent = `زمان باقیمانده: حدود ${etaSec} ثانیه`;
        } else {
          etaEl.textContent = "در حال تکمیل...";
        }
      } else {
        title.textContent = "در حال دریافت فایل اکسل...";
        sizeEl.textContent = `دریافت شده: ${loadedMb} MB`;
        speedEl.textContent = "سرعت: " + speedStr;
        etaEl.textContent = `زمان سپری‌شده: ${Math.round(elapsedSec)} ثانیه`;
        bar.style.width = "80%";
        pct.textContent = "...";
      }
    };

    xhr.onload = () => {
      clearInterval(prepTimer);
      if (xhr.status >= 200 && xhr.status < 300) {
        bar.style.width = "100%";
        pct.textContent = "۱۰۰٪";
        title.textContent = "فایل آماده شد! در حال ذخیره... ✓";
        spinner.style.display = "none";

        const blob = xhr.response;
        const link = document.createElement("a");
        link.href = window.URL.createObjectURL(blob);
        link.download = filename || "MaskanYar_Dossiers_Export.xlsx";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => window.URL.revokeObjectURL(link.href), 1000);

        setTimeout(() => {
          modal.style.display = "none";
          this.isDownloading = false;
        }, 2200);
      } else {
        title.textContent = "خطا در دریافت فایل (" + xhr.status + ")";
        spinner.style.display = "none";
        etaEl.textContent = "لطفاً چند لحظه بعد مجدداً تلاش نمایید.";
        setTimeout(() => {
          modal.style.display = "none";
          this.isDownloading = false;
        }, 4000);
      }
    };

    xhr.onerror = () => {
      clearInterval(prepTimer);
      title.textContent = "خطا در ارتباط با سرور";
      spinner.style.display = "none";
      setTimeout(() => {
        modal.style.display = "none";
        this.isDownloading = false;
      }, 3000);
    };

    xhr.send();
  },
};

// =========================================================================
// Dark / Light Theme Manager & System Sync
// =========================================================================
window.SanadbanTheme = {
  storageKey: "sb-theme",

  get() {
    return document.documentElement.getAttribute("data-theme") || "light";
  },

  set(theme) {
    if (theme !== "dark" && theme !== "light") theme = "light";
    document.documentElement.setAttribute("data-theme", theme);
    if (document.body) {
      document.body.setAttribute("data-theme", theme);
    }
    try {
      localStorage.setItem(this.storageKey, theme);
    } catch (e) {}

    window.dispatchEvent(
      new CustomEvent("sanadban-theme-changed", { detail: { theme } }),
    );
    this.syncUI();
  },

  toggle() {
    const next = this.get() === "dark" ? "light" : "dark";
    this.set(next);
    return next;
  },

  syncUI() {
    const isDark = this.get() === "dark";
    document.querySelectorAll(".sb-theme-toggle-btn").forEach((btn) => {
      btn.setAttribute("aria-pressed", isDark ? "true" : "false");
      btn.setAttribute(
        "title",
        isDark ? "تغییر به تم روشن (روز)" : "تغییر به تم تاریک (شب)",
      );
      const label = btn.querySelector(".sb-theme-label");
      if (label) {
        label.textContent = isDark ? "تم روز" : "تم شب";
      }
    });

    document.querySelectorAll(".sb-theme-switch-track").forEach((track) => {
      track.setAttribute("aria-checked", isDark ? "true" : "false");
    });
  },

  init() {
    try {
      const saved = localStorage.getItem(this.storageKey);
      // Default to 'light' (Day theme)
      const initial = saved || "light";
      this.set(initial);
    } catch (e) {
      this.set("light");
    }

    // Keyboard shortcut: Alt + T or Ctrl + Alt + D
    window.addEventListener("keydown", (e) => {
      if (
        (e.altKey && (e.key === "t" || e.key === "T" || e.key === "ف")) ||
        (e.ctrlKey &&
          e.altKey &&
          (e.key === "d" || e.key === "D" || e.key === "ی"))
      ) {
        e.preventDefault();
        this.toggle();
      }
    });

    this.syncUI();
  },
};

// Auto-run early
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () =>
    window.SanadbanTheme.init(),
  );
} else {
  window.SanadbanTheme.init();
}

// =========================================================================
// UI Mode Manager: حالت ساده / حالت پیشرفته (saved on the user's profile)
// =========================================================================
window.SanadbanUiMode = {
  get() {
    const attr = document.documentElement.getAttribute("data-ui-mode");
    if (attr === "simple" || attr === "advanced") return attr;
    try {
      const local = localStorage.getItem("sb-ui-mode");
      if (local === "simple" || local === "advanced") return local;
    } catch (_) {}
    return "simple";
  },

  set(mode, persist = true) {
    if (mode !== "simple" && mode !== "advanced") mode = "advanced";
    this._apply(mode);
    if (persist) this.save(mode);
  },

  toggle() {
    const next = this.get() === "simple" ? "advanced" : "simple";
    this.set(next);
    return next;
  },

  _apply(mode) {
    document.documentElement.setAttribute("data-ui-mode", mode);
    try {
      localStorage.setItem("sb-ui-mode", mode);
    } catch (_) {}
    window.dispatchEvent(
      new CustomEvent("sanadban-ui-mode-changed", { detail: { mode } }),
    );
    if (window.SanadbanAppInstance) {
      window.SanadbanAppInstance.simpleMode = mode === "simple";
      if (
        typeof window.SanadbanAppInstance.applySimpleModeVisibility ===
        "function"
      ) {
        window.SanadbanAppInstance.applySimpleModeVisibility();
      }
    }
    this.syncUI();
  },

  getCsrf() {
    if (window.SB_CSRF_TOKEN) return window.SB_CSRF_TOKEN;
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  },

  async save(mode) {
    const url = window.SB_UI_MODE_URL;
    if (!url) return;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrf(),
        },
        body: JSON.stringify({ mode }),
      });
      if (!res.ok) console.warn("UI mode save status:", res.status);
    } catch (e) {
      console.warn("UI mode was not saved to server:", e);
    }
  },

  syncUI() {
    const simple = this.get() === "simple";
    document.querySelectorAll("[data-sb-mode-toggle]").forEach((btn) => {
      btn.setAttribute("aria-pressed", simple ? "true" : "false");
    });
  },
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () =>
    window.SanadbanUiMode.syncUI(),
  );
} else {
  window.SanadbanUiMode.syncUI();
}
