const FIELD_STAGE_MAP = {
  national_id: [0, 1, 2, 10], full_name: [0, 1, 2, 10], father_name: [0, 1, 2, 10], birth_date: [0, 1, 2, 10], applicant_phone: [0, 1, 2, 10],
  selection_rank: [0, 1, 2, 10], decile: [0, 6], marital_status: [0, 1, 2, 10], is_married_confirmed: [0, 1, 2, 10],
  spouse_full_name: [0, 1, 2, 10], spouse_father_name: [0, 1, 2, 10], spouse_national_id: [0, 1, 2, 10],
  spouse_birth_date: [0, 1, 2, 10], spouse_id_number: [0, 1, 2, 10], spouse_birth_place: [0, 1, 2, 10],
  site: [0, 1, 2, 10], project: [0, 1, 2, 10], construction_type: [0, 1, 2, 10], block_name: [0, 1, 2, 10], block_code: [0, 1, 2, 10],
  floor_number: [0, 1, 2, 10], unit_number: [0, 1, 2, 10], unit_code: [0, 1, 2, 10], bedroom_count: [0, 1, 2, 10], unit_direction: [0, 1, 2, 10],
  net_unit_area: [0, 1, 2, 10], common_area: [0, 1, 2, 10], total_area: [0, 1, 2, 10], unit_area: [0, 1, 2, 10],
  storage_number: [0, 1, 2, 10], storage_area: [0, 1, 2, 10], parking_number: [0, 1, 2, 10], parking_area: [0, 1, 2, 10], covered_parking_area: [0, 1, 2, 10],
  registration_section: [0, 1, 12, 14], main_plaque: [0, 1, 12, 14], separated_plaque: [0, 1, 12, 14],
  sub_plaque: [0, 1, 12, 14], plot_number: [0, 1, 12, 14],
  base_cost_without_loan: [0, 2],
  applicant_form_j_status: [3, 16], applicant_form_j_directorate_status: [3, 16], applicant_form_j_red_description: [3, 16],
  spouse_form_j_status: [3, 16], spouse_form_j_directorate_status: [3, 16], spouse_form_j_red_description: [3, 16],
  fund_loan_amount: [4],
  contractor_letter_amount: [5, 19],
  decile_loan_amount: [6],
  applicant_equity: [7], is_sms_sent: [7], sms_sent_at: [7],
  is_equity_funded: [7],
  bank_loan_amount: [8, 11], bank_letter_number: [8, 11], bank_letter_date: [8, 11],
  is_added_to_bank_shipment_list: [8, 11], is_sent_to_bank: [8, 11], bank_sent_date: [8, 11], bank_sent_letter_number: [8, 11],
  total_land_share: [17], past_years_rent: [17], current_year_rent: [17], land_lease_year: [17], preparation_cost: [17],
  decile_loan_bank: [18], supported_institution: [18], check_count: [18],
  check_amount: [18], last_check_amount: [18], total_check_amount: [18], check_service_fee: [18],
  commitment_number: [18], commitment_date: [18], check_entries_json: [18], is_decile_loan_confirmed: [18],
  tenant_price: [18], tenant_code: [18], is_cash_rent_confirmed: [18],
  cash_preparation_amount: [18], prepayment_code: [18], non_cash_preparation_amount: [18],
  preparation_service_fee: [18], preparation_check_count: [18], total_preparation_check_amount: [18],
  preparation_check_entries_json: [18], is_preparation_checks_confirmed: [18],
  rah_letter: [20], rah_letter_date: [20]
};

/**
 * SanadBan (DeedFlow) - Interactive Logic Engine & Alpine.js Store
 * Full 22-Stage Housing Workflow & Interactive Scan Viewer
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

// Official 22-Stage Housing Workflow Configuration (Stages 0 to 21)
const STAGES_22 = [
  { id: 0, unit: 'brokerage', role: 'کارشناس ثبت اطلاعات متقاضی و واحد انتخابی و پلاک ثبتی', title: 'ورود اطلاعات متقاضی، همسر، واحد و پروژه', category: 'کارگزاری مسکن' },
  { id: 1, unit: 'brokerage', role: 'کارشناس اطلاعات', title: 'کنترل اطلاعات پلاک ثبتی', category: 'کارگزاری مسکن' },
  { id: 2, unit: 'brokerage', role: 'کارشناس اطلاعات (کارگزاری)', title: 'ورود مبلغ تمام شده واحد', category: 'کارگزاری مسکن' },
  { id: 3, unit: 'directorate', role: 'کارشناس بررسی فرم ج (عالمی)', title: 'بررسی فرم ج', category: 'استعلامات و تسهیلات' },
  { id: 4, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (حیدری)', title: 'ورود مبلغ وام صندوق', category: 'استعلامات و تسهیلات' },
  { id: 5, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (حیدری)', title: 'مبلغ نامه (کسر یا تخفیف) پیمانکار', category: 'استعلامات و تسهیلات' },
  { id: 6, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (حیدری)', title: 'مبلغ تسهیلات دهک', category: 'استعلامات و تسهیلات' },
  { id: 7, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (وصالی)', title: 'تعیین مبلغ باقیمانده نقدی مورد نیاز', category: 'استعلامات و تسهیلات' },
  { id: 8, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (وصالی / حیدری)', title: 'ارسال و درج شماره و تاریخ نامه معرفی به بانک', category: 'استعلامات و تسهیلات' },
  { id: 9, unit: 'brokerage', role: 'کارشناس تشکیل پرونده کارگزاری', title: 'اسکن مدارک و دفترچه اقساط', category: 'کارگزاری مسکن' },
  { id: 10, unit: 'brokerage', role: 'مدیرعامل کارگزاری', title: 'تأیید مدیرعامل کارگزاری', category: 'کارگزاری مسکن' },
  { id: 11, unit: 'directorate', role: 'کارشناس نهضت ملی مسکن و استعلام تسهیلات بانکی', title: 'بررسی کارشناس نهضت ملی مسکن', category: 'تأییدات تخصصی اداره کل' },
  { id: 12, unit: 'directorate', role: 'کارشناس فنی و مهندسی', title: 'بررسی کارشناس فنی و مهندسی', category: 'تأییدات تخصصی اداره کل' },
  { id: 13, unit: 'directorate', role: 'کارشناس املاک', title: 'بررسی کارشناس املاک (بارگذاری سند)', category: 'تأییدات تخصصی اداره کل' },
  { id: 14, unit: 'directorate', role: 'کارشناس بانک زمین', title: 'بررسی کارشناس بانک زمین', category: 'تأییدات تخصصی اداره کل' },
  { id: 15, unit: 'directorate', role: 'کارشناس حقوقی', title: 'بررسی کارشناس حقوقی', category: 'تأییدات تخصصی اداره کل' },
  { id: 16, unit: 'directorate', role: 'کارشناس فرم ج', title: 'بررسی و آپلود صفحه فرم جیم اداره کل', category: 'تأییدات تخصصی اداره کل' },
  { id: 17, unit: 'directorate', role: 'کارشناس ارزیابی', title: 'کارشناس ارزیابی (قدرالسهم، اجاره و آماده‌سازی)', category: 'ارزیابی و وصول' },
  { id: 18, unit: 'brokerage', role: 'کارشناس اخذ اجاره و آماده سازی و تسهیلات دهک', title: 'وصول نقد، اقساط، چک‌های دهک و آماده‌سازی', category: 'ارزیابی و وصول' },
  { id: 19, unit: 'directorate', role: 'کارشناس تسویه با پیمانکار', title: 'بررسی کارشناس تسویه با پیمانکار', category: 'تسویه و خاتمه' },
  { id: 20, unit: 'directorate', role: 'کارشناس صدور نامه محضر', title: 'صدور و ثبت نامه محضر', category: 'صدور و بایگانی' },
  { id: 21, unit: 'directorate', role: 'کارشناس بایگانی', title: 'مشاهده فرم نهایی و بایگانی قطعی', category: 'صدور و بایگانی' }
];

// Comprehensive 22-Stage Workflow Guidance (Stages 0 to 21)
const STAGE_GUIDANCE = {
  0: {
    actionTitle: 'ورود اطلاعات متقاضی، همسر، واحد و پروژه',
    actionSummary: 'واکشی استعلام پیش‌ثبت‌نام متقاضی، احراز زوجیت همسر، مشخصات سایت و پروژه و بارگذاری اسکن مدارک.',
    items: [
      'بررسی و ثبت کدملی، تاریخ تولد و مشخصات متقاضی',
      'تکمیل کامل مشخصات سجلی همسر (کدملی، شماره شناسنامه، تاریخ تولد)',
      'تایید مشخصات بلوک، طبقه و شماره واحد انتخابی',
      'بارگذاری تصویر اسکن کارت هوشمند ملی و برگه انتخاب واحد'
    ],
    targetSection: '#section-applicant'
  },
  1: {
    actionTitle: 'کنترل اطلاعات پلاک ثبتی',
    actionSummary: 'تطبیق و ثبت اطلاعات بخش ثبتی، پلاک اصلی، پلاک مفروز، پلاک فرعی و شماره قطعه زمین پروژه.',
    items: [
      'کنترل و ثبت نام بخش ثبتی پروژه مسکونی',
      'درج شماره پلاک اصلی و پلاک مفروز',
      'درج شماره پلاک فرعی و قطعه مربوط به پروژه'
    ],
    targetSection: '#section-plot'
  },
  2: {
    actionTitle: 'ورود مبلغ تمام شده واحد',
    actionSummary: 'محاسبه و درج قیمت پایه ساخت واحد مسکونی بدون احتساب وام طرح نهضت ملی مسکن (ریال).',
    items: [
      'ورود مبلغ تمام‌شده بر مبنای قرارداد ساخت کارگزاری',
      'بررسی عدم کسر تسهیلات بانکی در این مرحله',
      'مشاهده مبلغ به حروف فارسی و تایید درستی ارقام'
    ],
    targetSection: '#section-cost'
  },
  3: {
    actionTitle: 'بررسی فرم ج',
    actionSummary: 'استعلام سیستمی از سامانه جامع مسکن جهت احراز عدم استفاده قبلی متقاضی یا همسر از زمین یا تسهیلات دولتی.',
    items: [
      'استعلام سبزبودن فرم ج متقاضی مسکن',
      'استعلام وضعیت فرم ج همسر متقاضی',
      'ثبت نتیجه استعلام به صورت تاییدشده و سبز'
    ],
    targetSection: '#section-spouse'
  },
  4: {
    actionTitle: 'ورود مبلغ وام صندوق',
    actionSummary: 'تعیین و درج میزان تسهیلات تخصیص‌یافته از محل صندوق ملی مسکن جهت کاهش تعهد آورده متقاضی.',
    items: [
      'بررسی مصوبه تخصیص صندوق ملی مسکن برای پروژه',
      'درج رقم مصوب تسهیلات صندوق ملی مسکن (ریال)',
      'کنترل تاثیر مستقیم بر کاهش مانده سهم آورده نقدی متقاضی'
    ],
    targetSection: '#section-loans'
  },
  5: {
    actionTitle: 'مبلغ نامه (کسر یا تخفیف) پیمانکار',
    actionSummary: 'درج مبالغ تخفیفات، تعدیلات منفی یا کسورات پیمانکار سازنده بر اساس صورت‌وضعیت تاییدشده.',
    items: [
      'بررسی شماره و تاریخ نامه پیمانکار سازنده',
      'ثبت مبلغ کسر یا تخفیف ابلاغی پیمانکار (ریال)'
    ],
    targetSection: '#section-loans'
  },
  6: {
    actionTitle: 'مبلغ تسهیلات دهک',
    actionSummary: 'بررسی رتبه دهک متقاضی (۱ تا ۱۰) و اعمال تسهیلات ویژه دهک‌های کم‌درآمد.',
    items: [
      'کنترل رتبه دهک درآمدی متقاضی در سامانه رفاه ایرانیان',
      'ورود مبلغ تسهیلات دهک (ریال)',
      'تطبیق با شرایط متقاضی جهت تقسیط بلندمدت'
    ],
    targetSection: '#section-loans'
  },
  7: {
    actionTitle: 'تعیین مبلغ باقیمانده نقدی مورد نیاز',
    actionSummary: 'محاسبه سیستمی آورده نقدی مورد نیاز متقاضی و ارسال پیامک اطلاع‌رسانی تکمیل واریزی.',
    items: [
      'بررسی محاسبه مانده بدهی آورده نقدی متقاضی',
      'تایید وضعیت ارسال پیامک اطلاع‌رسانی به متقاضی',
      'ثبت تاریخ ارسال پیامک اعلام واریزی آورده'
    ],
    targetSection: '#section-applicant-equity'
  },
  8: {
    actionTitle: 'ارسال و درج شماره و تاریخ نامه معرفی به بانک',
    actionSummary: 'ثبت اطلاعات معرفی‌نامه رسمی متقاضی به بانک عامل جهت تقسیط تسهیلات ساخت مسکن.',
    items: [
      'درج شماره نامه رسمی معرفی به بانک',
      'ثبت تاریخ صدور نامه بانکی',
      'تعیین وضعیت ارسال فیزیکی / سیستمی به شعبه بانک'
    ],
    targetSection: '#section-bank-letter'
  },
  9: {
    actionTitle: 'اسکن مدارک و دفترچه اقساط',
    actionSummary: 'بارگذاری تصاویر اسکن‌شده قرارداد، مدارک هویتی و دفترچه فروش اقساطی صادره توسط بانک عامل.',
    items: [
      'بارگذاری تصویر صفحات اول و دوم دفترچه اقساط بانکی',
      'کنترل وضوح تصویر و عدم خدشه در ارقام و مهر بانک',
      'ثبت در آرشیو مدارک پیوست پرونده'
    ],
    targetSection: '#section-docs-installment'
  },
  10: {
    actionTitle: 'تأیید مدیرعامل کارگزاری',
    actionSummary: 'بازبینی کامل پرونده، بررسی صحت مبالغ و مدارک کارگزاری، و تایید نهایی توسط مدیرعامل کارگزاری.',
    items: [
      'کنترل رعایت کلیه ضوابط اجرایی مراحل ۰ تا ۹',
      'بررسی تاییدیه مالی اولیه و اطلاعات ثبتی',
      'ثبت امضای الکترونیک مدیرعامل کارگزاری جهت ارسال به اداره کل'
    ],
    targetSection: '#audit-timeline-section'
  },
  11: {
    actionTitle: 'بررسی کارشناس اداره کل (نهضت ملی مسکن)',
    actionSummary: 'بررسی کارشناسی و انطباق سوابق متقاضی در طرح نهضت ملی مسکن توسط کارشناس مربوطه در اداره کل.',
    items: [
      'بررسی ضوابط طرح نهضت ملی مسکن',
      'تایید اصالت استعلام تسهیلات مسکن',
      'ثبت امضای دیجیتال کارشناس نهضت ملی مسکن'
    ],
    targetSection: '#audit-timeline-section'
  },
  12: {
    actionTitle: 'بررسی کارشناس اداره کل (فنی و مهندسی)',
    actionSummary: 'کنترل نقشه‌های معماری، پروانه ساختمانی، پایان‌کار و تایید مشخصات فنی و مهندسی واحد.',
    items: [
      'بررسی پایان‌کار ساختمانی و مشخصات فنی اعیانی',
      'کنترل متراژ مفید، مشاعات و ضرایب متعلقه',
      'ثبت امضای دیجیتال تایید فنی و مهندسی'
    ],
    targetSection: '#section-plot'
  },
  13: {
    actionTitle: 'بررسی کارشناس اداره کل (املاک)',
    actionSummary: 'تطبیق مشخصات ملک، بارگذاری تصویر سند رسمی مالکیت عرصه و احراز عدم تعارض مالکیتی.',
    items: [
      'بارگذاری تصویر سند رسمی عرصه پروژه',
      'تایید مالکیت دولت / اداره کل راه و شهرسازی بر عرصه',
      'ثبت امضای دیجیتال کارشناس املاک اداره کل'
    ],
    targetSection: '#section-plot'
  },
  14: {
    actionTitle: 'بررسی کارشناس اداره کل (بانک زمین)',
    actionSummary: 'استعلام و تطبیق موقعیت جغرافیایی و ثبتی ملک در سامانه جامع بانک زمین اداره کل.',
    items: [
      'بررسی کاداستر و مختصات UTM عرصه پروژه',
      'تطبیق با بانک اطلاعات زمین سازمان ملی زمین و مسکن',
      'ثبت امضای دیجیتال کارشناس بانک زمین'
    ],
    targetSection: '#audit-timeline-section'
  },
  15: {
    actionTitle: 'بررسی کارشناس اداره کل (حقوقی)',
    actionSummary: 'بررسی عدم موانع حقوقی، پرونده‌های مفتوح قضایی یا تعارضات مالکیتی و قراردادهای واگذاری.',
    items: [
      'استعلام وضعیت حقوقی و سوابق پرونده‌های قضایی زمین',
      'تایید عدم وجود معارض و منع قانونی انتقال سندی',
      'ثبت امضای دیجیتال کارشناس حقوقی اداره کل'
    ],
    targetSection: '#audit-timeline-section'
  },
  16: {
    actionTitle: 'بررسی و آپلود صفحه فرم جیم اداره کل',
    actionSummary: 'بارگذاری اسکن برگه استعلام رسمی فرم «ج» تاییدشده متقاضی و همسر از سامانه نهضت ملی اداره کل.',
    items: [
      'بارگذاری اسکن تاییدیه نهایی فرم جیم صادره اداره کل',
      'تطبیق وضعیت سبز قطعی متقاضی و همسر',
      'ثبت امضای دیجیتال کارشناس فرم ج'
    ],
    targetSection: '#form-j-dedicated-card'
  },
  17: {
    actionTitle: 'کارشناس ارزیابی (قدرالسهم، اجاره و آماده‌سازی)',
    actionSummary: 'محاسبه قدرالسهم عرصه، اجاره سنواتی، اجاره سال جاری و هزینه‌های آماده‌سازی پروژه مسکونی.',
    items: [
      'ورود متراژ دقیق قدرالسهم متقاضی از عرصه (متر مربع)',
      'محاسبه و درج مبلغ اجاره سنوات گذشته و سال جاری (ریال)',
      'تعیین مبلغ کل آماده‌سازی و تفکیک ۲۰٪ نقد و ۸۰٪ اقساط'
    ],
    targetSection: '#section-valuation-rent'
  },
  18: {
    actionTitle: 'وصول نقد، اقساط، چک‌های دهک و آماده‌سازی',
    actionSummary: 'دریافت، ثبت چک‌های اقساط و بارگذاری اسکن چک‌های تسهیلات دهک و آماده‌سازی.',
    items: [
      'دریافت و ثبت مشخصات چک‌های صیادی تسهیلات دهک درآمدی',
      'دریافت فیش واریز نقدی و چک‌های اقساط آماده‌سازی و اجاره',
      'بارگذاری اسکن چک‌ها و صدور رسید چاپی رسمی'
    ],
    targetSection: '#section-checks'
  },
  19: {
    actionTitle: 'بررسی کارشناس تسویه با پیمانکار',
    actionSummary: 'بررسی صورت‌جلسه تسویه قطعی پیمانکار و صدور اجازه چاپ فرم مراحل و امضاها.',
    items: [
      'بررسی اسناد تسویه حساب مالی با شرکت پیمانکار سازنده',
      'تایید تسویه و باز شدن قابلیت چاپ فرم مراحل و امضاها',
      'ثبت امضای دیجیتال کارشناس تسویه پیمانکار'
    ],
    targetSection: '#audit-timeline-section'
  },
  20: {
    actionTitle: 'صدور و ثبت نامه محضر',
    actionSummary: 'تولید، ثبت شماره نامه در سوابق و چاپ معرفی‌نامه رسمی متقاضی به دفتر اسناد رسمی.',
    items: [
      'بررسی و ثبت شماره و تاریخ نامه معرفی به محضر',
      'تعیین شماره دفتر اسناد رسمی (محضر)',
      'چاپ معرفی‌نامه محضر و ثبت امضای دیجیتال کارشناس'
    ],
    targetSection: '#section-notary'
  },
  21: {
    actionTitle: 'مشاهده فرم نهایی و بایگانی قطعی',
    actionSummary: 'رویت شناسنامه جامع سندی، چاپ فرم رسمی مراحل و امضاها (۱۴ امضا)، اعمال قفل سیستمی دائم و اتمام فرآیند در آرشیو قطعی.',
    items: [
      'بررسی خلاصه سوابق و کلیه امضاهای مراحل پرونده',
      'چاپ فرم رسمی مراحل و امضاها (۱۴ امضا)',
      'فشردن دکمه «تایید و بایگانی قطعی پرونده» جهت قفل ابدی پرونده'
    ],
    targetSection: '#audit-timeline-section'
  }
};

// Alpine.js Application Store & Controller
document.addEventListener('alpine:init', () => {
  Alpine.data('sanadbanApp', () => ({
    // Pipeline State
    currentStage: 1,
    status: 'IN_PROGRESS',
    returnReason: '',
    returnBy: '',
    returnFromStage: null,
    stages: STAGES_22,
    archiveNumber: 100001,
    isLocked: false,
    userCanAction: true,
    isChief: false,
    showRoadmap: false,
    stageDetails: {},
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

    // Form Data - Merged 45+ Fields Matrix
    form: {
      // Stage 1 Fields
      full_name: 'علیرضا رضایی پور',
      father_name: 'محمدرضا',
      national_id: '0012345678',
      birth_date: '1365/04/15',
      applicant_phone: '',
      selection_rank: null,
      applicant_form_j_status: 'سبز (استعلام شده)',
      applicant_form_j_directorate_status: 'تایید نهایی اداره کل',
      applicant_form_j_red_description: '',
      spouse_full_name: 'فاطمه السادات موسوی',
      spouse_father_name: 'سید علی',
      spouse_national_id: '0029876543',
      spouse_birth_date: '1368/02/10',
      spouse_id_number: '1245',
      spouse_birth_place: 'قم',
      spouse_form_j_status: 'سبز (استعلام شده)',
      spouse_form_j_directorate_status: 'تایید نهایی اداره کل',
      spouse_form_j_red_description: '',
      marital_status: 'متاهل (واجد شرایط طرح زوجین)',
      is_married_confirmed: true,
      decile: 4,
      site: 'شهید رئیسی',
      project: 'پروژه ۵۶۰ هکتاری فاز ۲ (تعداد واحد: ۳۲۰)',
      construction_type: 'آپارتمانی',
      block_name: 'بلوک B-14',
      block_code: '',
      floor_number: 3,
      unit_number: 12,
      unit_code: '',
      bedroom_count: 2,
      unit_direction: 'شمال غربی',
      net_unit_area: 85.00,
      common_area: 25.00,
      total_area: 110.00,
      unit_area: 85.50,
      storage_number: 12,
      storage_area: 3.20,
      parking_number: 12,
      parking_area: 12.50,
      covered_parking_area: 11.25,

      // Stage 2: Plot & Registry
      registration_section: 'بخش ۱ ثبتی قم',
      main_plaque: 1420,
      separated_plaque: 85,
      sub_plaque: 312,
      plot_number: 48,

      // Stage 3: Base Cost & Bank Loan Amount (Default 650M Tomans, can be 550M or custom)
      base_cost_without_loan: 4500000000,
      bank_loan_amount: 6500000000,

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

      // Stage 18: BankCheckTracker & TashilatCheck Fields (وام دهک، چک‌ها، آماده‌سازی و اجاره)
      decile_loan_bank: 'بانک مسکن',
      supported_institution: 'هیچکدام',
      check_count: 1,
      check_amount: 0,
      last_check_amount: 0,
      total_check_amount: 0,
      check_service_fee: 2000000,
      commitment_number: '',
      commitment_date: '',
      check_entries: [
        { row_number: 1, cash_date: '', check_amount: 0, check_sayadi_code: '', bank_name: 'بانک مسکن' }
      ],

      // TashilatCheck: Rent & 20%/80% Preparation
      tenant_price: 0,
      tenant_code: '',
      cash_preparation_amount: 120000000,
      prepayment_code: '',
      non_cash_preparation_amount: 200000000,
      preparation_service_fee: 2000000,
      preparation_check_count: 1,
      total_preparation_check_amount: 0,
      preparation_check_entries: [
        { row_number: 1, cash_date: '', check_amount: 0, check_sayadi_code: '', bank_name: 'بانک مسکن' }
      ],
      rah_letter: '',
      rah_letter_date: '',
      is_cash_rent_confirmed: false,
      is_decile_loan_confirmed: false,
      is_preparation_checks_confirmed: false
    },

    // Scanned Documents (populated dynamically from database without ghost record flicker)
    attachments: [],

    // Audit Trail / History (populated dynamically from database)
    auditLogs: [],

    // Field-level Change Audit Trail
    fieldChanges: [],
    stageSignatures: {},
    auditActiveTab: 'stages', // 'stages' or 'fields'
    showAuditDetails: false, // Minimized to 1-liner by default

    // Red Form J Disqualification State
    isRejected: false,
    isRedFormJ: false,
    rejectionLetterNumber: '',
    rejectionLetterDate: '',
    rejectionReason: '',
    rejectedBy: '',
    showRedRejectionModal: false,
    redLetterNumber: '',
    redLetterDate: '',
    redLetterReason: '',

    // Red Form J Return for Correction State
    showRedReturnModal: false,
    redReturnStage: 0,
    redReturnNotes: '',
    redResetFormJ: true,

    // Check Admin Authorization (Superuser, Chief, or Kargozari Check Admin)
    isCheckAdmin: false,
    userAllowedStages: 'all',
    isSuperuser: false,
    signaturesList: [],

    // Check Generator State (BankCheckTracker intelligent generation)
    checkGenerator: {
      count: 4,
      startDate: '',
      interval: '1year'
    },

    // Preparation Check Generator State (tashilatCheck intelligent 6-month installment generation)
    prepCheckGenerator: {
      count: 3,
      startDate: '',
      interval: '6months'
    },

    // Interactive Persian Date Picker Modal State
    datePickerModal: {
      isOpen: false,
      targetField: '',
      title: 'انتخاب تاریخ شمسی',
      year: 1405,
      month: 7,
      day: 30,
      yearsList: [1400, 1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408, 1409, 1410, 1411, 1412, 1413, 1414, 1415],
      monthsList: [
        { num: 1, name: 'فروردین', days: 31 },
        { num: 2, name: 'اردیبهشت', days: 31 },
        { num: 3, name: 'خرداد', days: 31 },
        { num: 4, name: 'تیر', days: 31 },
        { num: 5, name: 'مرداد', days: 31 },
        { num: 6, name: 'شهریور', days: 31 },
        { num: 7, name: 'مهر', days: 30 },
        { num: 8, name: 'آبان', days: 30 },
        { num: 9, name: 'آذر', days: 30 },
        { num: 10, name: 'دی', days: 30 },
        { num: 11, name: 'بهمن', days: 30 },
        { num: 12, name: 'اسفند', days: 29 }
      ]
    },

    init() {
      // 1. Set Persian Today Date dynamically
      this.todayDate = this.getTodayJalaliDisplay();

      // 2. Read real server data injected from database
      const serverDataEl = document.getElementById('dossier-server-json');
      if (serverDataEl && serverDataEl.textContent.trim()) {
        try {
          const serverData = JSON.parse(serverDataEl.textContent);
          if (serverData.archive_number) this.archiveNumber = serverData.archive_number;
          if (typeof serverData.current_stage !== 'undefined') this.currentStage = Number(serverData.current_stage);
          if (typeof serverData.is_locked !== 'undefined') this.isLocked = Boolean(serverData.is_locked);
          if (serverData.status) this.status = serverData.status;
          if (serverData.return_reason) this.returnReason = serverData.return_reason;
          if (serverData.return_by) this.returnBy = serverData.return_by;
          if (typeof serverData.return_from_stage !== 'undefined' && serverData.return_from_stage !== null) this.returnFromStage = serverData.return_from_stage;
          if (typeof serverData.user_can_action !== 'undefined') this.userCanAction = Boolean(serverData.user_can_action);
          if (typeof serverData.is_chief !== 'undefined') this.isChief = Boolean(serverData.is_chief);
          if (typeof serverData.is_superuser !== 'undefined') this.isSuperuser = Boolean(serverData.is_superuser);
          if (typeof serverData.is_check_admin !== 'undefined') this.isCheckAdmin = Boolean(serverData.is_check_admin);
          if (typeof serverData.user_allowed_stages !== 'undefined') this.userAllowedStages = serverData.user_allowed_stages;
          if (typeof serverData.is_superuser !== 'undefined') this.isSuperuser = Boolean(serverData.is_superuser);
          if (Array.isArray(serverData.signatures_list)) this.signaturesList = serverData.signatures_list;
          if (typeof serverData.is_rejected !== 'undefined') this.isRejected = Boolean(serverData.is_rejected);
          if (typeof serverData.is_red_form_j !== 'undefined') this.isRedFormJ = Boolean(serverData.is_red_form_j);
          if (serverData.stage_details) this.stageDetails = serverData.stage_details;
          if (serverData.rejection_letter_number) this.rejectionLetterNumber = serverData.rejection_letter_number;
          if (serverData.rejection_letter_date) this.rejectionLetterDate = serverData.rejection_letter_date;
          if (serverData.rejection_reason) this.rejectionReason = serverData.rejection_reason;
          if (serverData.rejected_by) this.rejectedBy = serverData.rejected_by;
          if (serverData.form) {
            this.form = Object.assign({}, this.form, serverData.form);
          }
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
          console.error('Failed to parse server dossier data:', e);
        }
      }
      this.recalculateEquity();

      if (!this.form.check_entries || !Array.isArray(this.form.check_entries) || this.form.check_entries.length === 0) {
        this.form.check_entries = [
          { row_number: 1, cash_date: '', check_amount: 0, check_sayadi_code: '', bank_name: this.form.decile_loan_bank || 'بانک مسکن' }
        ];
      }
      this.recalculateChecks();

      // Initialize Check Generator defaults from existing data or +1 year from today
      const firstCheckDate = (this.form.check_entries && this.form.check_entries[0] && this.form.check_entries[0].cash_date) ? this.form.check_entries[0].cash_date : '';
      this.checkGenerator.startDate = firstCheckDate || this.addYearsToJalali(this.getTodayJalali(), 1);
      if (this.form.check_entries && this.form.check_entries.length > 0) {
        this.checkGenerator.count = this.form.check_entries.length;
      }

      // Initialize Preparation Check entries for tashilatCheck (آماده‌سازی)
      if (!this.form.preparation_check_entries || !Array.isArray(this.form.preparation_check_entries) || this.form.preparation_check_entries.length === 0) {
        this.form.preparation_check_entries = [
          { row_number: 1, cash_date: '', check_amount: 0, check_sayadi_code: '', bank_name: 'بانک مسکن' }
        ];
      }
      this.recalculatePrepChecks();

      // Initialize Preparation Check Generator defaults (+6 months from today, or first prep check date)
      const firstPrepDate = (this.form.preparation_check_entries && this.form.preparation_check_entries[0] && this.form.preparation_check_entries[0].cash_date) ? this.form.preparation_check_entries[0].cash_date : '';
      this.prepCheckGenerator.startDate = firstPrepDate || this.addSixMonthsCustomJalali(this.getTodayJalali());
      if (this.form.preparation_check_entries && this.form.preparation_check_entries.length > 0) {
        this.prepCheckGenerator.count = this.form.preparation_check_entries.length;
      }
    },

    getTodayJalali() {
      try {
        const parts = new Intl.DateTimeFormat('en-US-u-ca-persian', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        }).formatToParts(new Date());
        const y = parts.find(p => p.type === 'year')?.value || '1405';
        const m = parts.find(p => p.type === 'month')?.value || '07';
        const d = parts.find(p => p.type === 'day')?.value || '30';
        return `${y}/${m}/${d}`;
      } catch (e) {
        return '1405/07/30';
      }
    },

    getTodayJalaliDisplay() {
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
      if (!str) return '';
      return String(str)
        .replace(/[۰٠]/g, '0')
        .replace(/[۱١]/g, '1')
        .replace(/[۲٢]/g, '2')
        .replace(/[۳٣]/g, '3')
        .replace(/[۴٤]/g, '4')
        .replace(/[۵٥]/g, '5')
        .replace(/[۶٦]/g, '6')
        .replace(/[۷٧]/g, '7')
        .replace(/[۸٨]/g, '8')
        .replace(/[۹٩]/g, '9');
    },

    parseJalaliDate(dateStr) {
      if (!dateStr) return null;
      const clean = this.normalizeJalaliDigits(dateStr).replace(/[-.]/g, '/').trim();
      const parts = clean.split('/');
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
      const sm = String(m).padStart(2, '0');
      const sd = String(d).padStart(2, '0');
      return `${sy}/${sm}/${sd}`;
    },

    addYearsToJalali(dateStr, yearsToAdd) {
      const parsed = this.parseJalaliDate(dateStr) || this.parseJalaliDate(this.getTodayJalali());
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
        return p ? this.formatJalaliDate(p.year, p.month, p.day) : this.getTodayJalali();
      }
      if (interval === '6months') {
        const p = this.parseJalaliDate(startDateStr) || this.parseJalaliDate(this.getTodayJalali());
        const totalMonths = (p.month - 1) + (index * 6);
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
      const parsed = this.parseJalaliDate(dateStr) || this.parseJalaliDate(this.getTodayJalali());
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
      this.triggerToast('جابجایی دستی مرحله غیرفعال است. تغییر مرحله صرفاً از طریق تایید و امضای الکترونیک یا برگشت جهت اصلاح انجام می‌گیرد.', 'warning');
    },

    // Get CSRF Token reliably from DOM or cookie
    getCSRFToken() {
      const input = document.querySelector('[name=csrfmiddlewaretoken]');
      if (input && input.value) return input.value;
      const match = document.cookie.match(/(?:^|;)\\s*csrftoken=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : '';
    },

    // Save Dossier Draft Directly to Database
    async saveDossierDraft(notify = true) {
      this.isSaving = true;
      try {
        const csrfToken = this.getCSRFToken();
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
            this.triggerToast(data.message || 'کلیه تغییرات با موفقیت در پایگاه داده ذخیره گردید.', 'success');
          }
          if (typeof data.applicant_equity !== 'undefined') {
            this.form.applicant_equity = data.applicant_equity;
          }
          if (Array.isArray(data.new_changes) && data.new_changes.length > 0) {
            this.fieldChanges.unshift(...data.new_changes);
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
    getStageSignature(stageId) {
      if (!this.stageSignatures) return null;
      return this.stageSignatures[stageId] || this.stageSignatures[String(stageId)] || null;
    },

    setBankLoan(amount) {
      this.form.bank_loan_amount = Number(amount) || 0;
      this.recalculateEquity();
    },

    recalculateEquity() {
      const baseCost = Number(this.form.base_cost_without_loan) || 0;
      const fundLoan = Number(this.form.fund_loan_amount) || 0;
      const decileLoan = Number(this.form.decile_loan_amount) || 0;
      this.form.applicant_equity = Math.max(0, baseCost - (fundLoan + decileLoan));
    },

    scrollToCategory(cat) {
      this.selectedCategory = cat || 'all';
      const album = document.getElementById('attachments-card');
      if (album) {
        album.scrollIntoView({ behavior: 'smooth', block: 'start' });
        album.classList.add('pulse-highlight');
        setTimeout(() => album.classList.remove('pulse-highlight'), 1600);
      }
    },

    getFilteredAttachments() {
      if (!this.selectedCategory || this.selectedCategory === 'all') return this.attachments;
      if (this.selectedCategory === 'identity') return this.attachments.filter(a => a.type === 'NATIONAL_ID' || a.type === 'SPOUSE_ID' || a.type === 'FORM_J' || a.doc_type === 'FORM_J');
      if (this.selectedCategory === 'form_j') return this.attachments.filter(a => a.type === 'FORM_J' || a.doc_type === 'FORM_J');
      if (this.selectedCategory === 'bank') return this.attachments.filter(a => a.type === 'BANK_BOOKLET' || a.type === 'BANK_LETTER');
      if (this.selectedCategory === 'deed') return this.attachments.filter(a => a.type === 'TITLE_DEED' || a.type === 'UNIT_SELECTION');
      if (this.selectedCategory === 'checks') return this.attachments.filter(a => a.type === 'LOAN_CHECK' || a.type === 'PREP_CHECK' || a.type === 'CHECK_RECEIPT');
      return this.attachments;
    },

    getCategoryCount(cat) {
      if (!this.attachments) return 0;
      if (cat === 'all') return this.attachments.length;
      if (cat === 'identity') return this.attachments.filter(a => a.type === 'NATIONAL_ID' || a.type === 'SPOUSE_ID' || a.type === 'FORM_J' || a.doc_type === 'FORM_J').length;
      if (cat === 'form_j') return this.attachments.filter(a => a.type === 'FORM_J' || a.doc_type === 'FORM_J').length;
      if (cat === 'bank') return this.attachments.filter(a => a.type === 'BANK_BOOKLET' || a.type === 'BANK_LETTER').length;
      if (cat === 'deed') return this.attachments.filter(a => a.type === 'TITLE_DEED' || a.type === 'UNIT_SELECTION').length;
      if (cat === 'checks') return this.attachments.filter(a => a.type === 'LOAN_CHECK' || a.type === 'PREP_CHECK' || a.type === 'CHECK_RECEIPT').length;
      return 0;
    },

    // Stage 9: Send SMS simulation
    sendEquitySMS() {
      this.form.is_sms_sent = true;
      this.form.sms_sent_at = '1403/05/18 14:20';
      
      this.auditLogs.unshift({
        step: 9,
        fromStage: 'مرحله ۹: تعیین مبلغ آورده',
        toStage: 'مرحله ۹: ارسال پیامک',
        actor: 'سیستم پیام‌رسان هوشمند مسکن یار',
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
    getSectionAttachments(types) {
      if (!this.attachments || !Array.isArray(this.attachments)) return [];
      if (!types) return this.attachments;
      const typeList = Array.isArray(types) ? types : [types];
      return this.attachments.filter(a => {
        const t = a.type || a.doc_type;
        return typeList.includes(t);
      });
    },

    async uploadSectionAttachment(docType, defaultTitle, event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;

      this.triggerToast(`در حال بارگذاری «${defaultTitle || file.name}»...`, 'info');

      try {
        const formData = new FormData();
        formData.append('title', defaultTitle || file.name);
        formData.append('doc_type', docType || 'OTHER');
        formData.append('file', file);

        const csrfToken = this.getCSRFToken();
        const res = await fetch(`/dossier/${this.archiveNumber}/upload-scan/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken
          },
          body: formData
        });

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          if (data.attachment) {
            const exists = this.attachments.some(a => a.id === data.attachment.id);
            if (!exists) {
              this.attachments.unshift(data.attachment);
            }
          }
          const nowStr = new Date().toLocaleDateString('fa-IR') + ' ' + new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${this.currentStage}`,
            toStage: `مرحله ${this.currentStage}`,
            actor: data.attachment ? data.attachment.uploader : 'کارشناس سامانه',
            role: this.getStage(this.currentStage)?.role || 'کارشناس',
            action: 'SUBMIT',
            actionLabel: `بارگذاری سند: ${defaultTitle || file.name}`,
            timestamp: nowStr,
            hash: data.attachment ? data.attachment.sha256 : '',
            notes: `سند «${defaultTitle || file.name}» با موفقیت در این بخش بارگذاری گردید.`
          });
          this.triggerToast(`مدرک «${defaultTitle || file.name}» با موفقیت بارگذاری و الصاق شد.`, 'success');
        } else {
          this.triggerToast(data.message || 'خطا در بارگذاری مدرک.', 'error');
        }
      } catch (err) {
        console.error('Error uploading section attachment:', err);
        this.triggerToast('خطا در برقراری ارتباط با سرور جهت بارگذاری مدرک.', 'error');
      } finally {
        event.target.value = '';
      }
    },

    async deleteAttachment(attId) {
      if (!confirm('آیا از حذف این مدرک از پرونده اطمینان دارید؟')) return;

      try {
        const csrfToken = this.getCSRFToken();
        const res = await fetch(`/dossier/${this.archiveNumber}/attachment/${attId}/delete/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken
          }
        });

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          this.attachments = this.attachments.filter(a => a.id !== attId);
          if (this.activeScan && this.activeScan.id === attId) {
            this.closeScanViewer();
          }
          this.triggerToast(data.message || 'مدرک با موفقیت حذف گردید.', 'success');
        } else {
          this.triggerToast(data.message || 'خطا در حذف مدرک.', 'error');
        }
      } catch (err) {
        console.error('Error deleting attachment:', err);
        this.triggerToast('خطا در برقراری ارتباط با سرور جهت حذف مدرک.', 'error');
      }
    },

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

    // Helper methods for Document Album & File types
    isPdfFile(item) {
      if (!item) return false;
      const url = (item.preview_url || '').toLowerCase();
      const name = (item.fileName || item.file_name || '').toLowerCase();
      return url.endsWith('.pdf') || name.endsWith('.pdf') || url.includes('.pdf?');
    },

    isHtmlDoc(item) {
      if (!item) return false;
      const url = (item.preview_url || '').toLowerCase();
      const name = (item.fileName || item.file_name || '').toLowerCase();
      return url.includes('/print/') || url.endsWith('.html') || name.endsWith('.html');
    },

    async handleCheckScanUploadAndReceipt(event, type = 'loan') {
      const file = event.target.files[0];
      if (!file) return;

      const typeLabel = type === 'prep' ? 'اقساط آماده‌سازی' : 'تسهیلات وام دهک';
      this.triggerToast(`در حال بارگذاری اسکن و تولید برگه رسید چک‌های ${typeLabel}...`, 'info');

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('check_type', type);

        const csrfToken = this.getCSRFToken();
        const res = await fetch(`/dossier/${this.archiveNumber}/checks/upload-scan-and-create-receipt/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken
          },
          body: formData
        });

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          if (data.attachment) {
            const exists = this.attachments.some(a => a.id === data.attachment.id);
            if (!exists) {
              this.attachments.unshift(data.attachment);
            }
          }
          this.triggerToast('تصویر اسکن دریافت، سربرگ و امضاها افزوده و به عنوان رسید چک‌ها ذخیره گردید ✓', 'success');
          
          if (data.print_url) {
            window.open(data.print_url, '_blank');
          }
        } else {
          this.triggerToast(data.message || 'خطا در بارگذاری اسکن چک.', 'error');
        }
      } catch (err) {
        console.error('Error uploading check scan and creating receipt:', err);
        this.triggerToast('خطا در ارتباط با سرور جهت تولید رسید چک.', 'error');
      } finally {
        event.target.value = '';
      }
    },

    async printExistingCheckScanReceipt(type = 'loan') {
      const typeLabel = type === 'prep' ? 'اقساط آماده‌سازی' : 'تسهیلات وام دهک';
      const targetDocType = type === 'prep' ? 'PREP_CHECK' : 'LOAN_CHECK';
      
      const existingScan = (this.attachments || []).find(a => 
        (a.type === targetDocType || a.doc_type === targetDocType) &&
        a.preview_url && 
        !a.preview_url.includes('/print/checks/')
      );

      let scanUrl = existingScan ? existingScan.preview_url : '';

      if (!scanUrl) {
        if (!this.isLocked) {
          this.triggerToast('رسید چاپی بدون تصویر اسکن باز می‌شود. در صورت تمایل می‌توانید فایل اسکن را نیز بارگذاری فرمایید.', 'info');
        }
      }

      try {
        const res = await fetch(`/dossier/${this.archiveNumber}/checks/archive-receipt/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
          },
          body: JSON.stringify({ type: type, scan_url: scanUrl })
        });
        const data = await res.json();
        if (data.status === 'success' && data.attachment) {
          const exists = this.attachments.some(a => a.id === data.attachment.id);
          if (!exists) {
            this.attachments.unshift(data.attachment);
          }
        }
      } catch (e) {
        console.error('Error archiving existing check scan receipt:', e);
      }

      const printUrl = `/dossier/${this.archiveNumber}/print/checks/?scan_url=${encodeURIComponent(scanUrl)}&type=${type}&auto_archive=0&auto_print=1`;
      window.open(printUrl, '_blank');
    },

    async printChecksReceipt(type = 'loan') {
      this.printExistingCheckScanReceipt(type);
    },

    isImageFile(item) {
      if (!item) return false;
      const url = (item.preview_url || '').toLowerCase();
      const name = (item.fileName || item.file_name || '').toLowerCase();
      const isImg = url.endsWith('.jpg') || url.endsWith('.jpeg') || url.endsWith('.png') || url.endsWith('.webp') || url.endsWith('.jfif') ||
                    name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png') || name.endsWith('.webp') || name.endsWith('.jfif');
      return isImg || url.startsWith('data:image');
    },

    isUploadAllowed() {
      if (this.isLocked) return false;
      return Boolean(this.userCanAction || this.isChief);
    },

    // Upload & Scanner Controller Methods
    openUploadScanModal() {
      if (!this.isUploadAllowed()) {
        this.triggerToast('بارگذاری مدارک صرفاً در مراحل ۰، ۹، ۱۳ و ۱۸ و توسط کارشناس مجاز امکان‌پذیر است.', 'warning');
        return;
      }

      let defaultTitle = 'مدرک پیوست مرحله ' + this.currentStage;
      let defaultType = 'OTHER';

      if (this.currentStage <= 1) {
        defaultTitle = 'اسکن کارت ملی و مدارک سجلی';
        defaultType = 'NATIONAL_ID';
      } else if (this.currentStage === 3 || this.currentStage === 16) {
        defaultTitle = 'تصویر و استعلام رسمی فرم (ج) اداره کل';
        defaultType = 'FORM_J';
      } else if (this.currentStage === 9) {
        defaultTitle = 'اسکن دفترچه اقساط تسهیلات بانک مسکن';
        defaultType = 'BANK_BOOKLET';
      } else if (this.currentStage === 13) {
        defaultTitle = 'اسکن سند مالکیت تک‌برگ عرصه و اعیان';
        defaultType = 'TITLE_DEED';
      } else if (this.currentStage === 18) {
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

      if (!this.isUploadAllowed()) {
        this.triggerToast('بارگذاری مدرک در مرحله جاری یا برای حساب شما مجاز نمی‌باشد.', 'error');
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

        const resData = await response.json();

        if (response.ok && resData.status === 'success') {
          if (resData.attachment) {
            this.attachments.unshift({
              ...resData.attachment,
              preview_url: resData.attachment.preview_url || this.uploadForm.preview_url
            });
          }

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${this.currentStage}`,
            toStage: `مرحله ${this.currentStage}`,
            actor: resData.attachment ? resData.attachment.uploader : 'کارشناس بارگذاری اسناد',
            role: this.getStage(this.currentStage).role,
            action: 'SUBMIT',
            actionLabel: `بارگذاری سند: ${this.uploadForm.title}`,
            timestamp: nowStr,
            hash: resData.attachment ? resData.attachment.sha256 : hashStr,
            notes: `مدرک «${this.uploadForm.title}» با موفقیت اسکن و در مرحله ${this.currentStage} ثبت گردید.`
          });

          this.triggerToast(`مدرک «${this.uploadForm.title}» با موفقیت بارگذاری و الصاق شد.`, 'success');
          this.showUploadModal = false;
        } else {
          this.triggerToast(resData.message || 'خطا در بارگذاری مدرک. بارگذاری در این مرحله مجاز نمی‌باشد.', 'error');
        }
      } catch (err) {
        console.error('Upload error:', err);
        this.triggerToast('خطای ارتباط با سرور در هنگام بارگذاری مدرک.', 'error');
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
        desc: `مدرک بارگذاری‌شده در مرحله ${this.currentStage} (${this.getStage(this.currentStage).title})`
      };
      this.attachments.unshift(newScan);
    },

    // Workflow Phase, Guidance & Section Helpers
    getPhaseName(stg) {
      stg = Number(stg);
      if (stg <= 2) return 'فاز اول: ثبت‌نام، مشخصات متقاضی و پلاک (کارگزاری)';
      if (stg <= 10) return 'فاز دوم: استعلامات، تسهیلات بانکی و تایید مدیرعامل';
      if (stg <= 17) return 'فاز سوم: ممیزی تخصصی اراضی، فنی و حقوقی اداره کل';
      return 'فاز چهارم: وصول تضامین، تسویه، معرفی محضر و بایگانی';
    },

    getStageGuidance(stg) {
      return STAGE_GUIDANCE[Number(stg)] || {
        actionTitle: 'اقدام کارشناسی این مرحله',
        actionSummary: 'بررسی مدارک و مستندات پرونده، کنترل اطلاعات و ثبت امضای دیجیتال.',
        items: ['بررسی سوابق مراحل قبلی', 'تطبیق اطلاعات با مستندات ثبتی', 'ثبت تاییدیه الکترونیکی'],
        targetSection: '#form-sections'
      };
    },

    scrollToActiveSection(targetSelector) {
      if (!targetSelector) return;
      const el = document.querySelector(targetSelector);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('pulse-highlight');
        setTimeout(() => {
          el.classList.remove('pulse-highlight');
        }, 2800);
      }
    },

    isSectionActive(sectionId) {
      const stg = Number(this.currentStage);
      const mapping = {
        'section-applicant': [0, 3, 16],
        'section-spouse': [0, 3, 16],
        'section-plot': [1, 12, 14, 15],
        'section-cost': [2],
        'section-loans': [4, 5, 6],
        'section-equity': [7],
        'section-bank': [8, 9, 11],
        'section-valuation': [17, 19],
        'section-checks': [18],
        'scans-album-section': [0, 9, 13, 18]
      };
      return mapping[sectionId] ? mapping[sectionId].includes(stg) : false;
    },

    // Helper to safely get stage metadata by ID
    getStage(id) {
      return this.stages.find(s => s.id === Number(id)) || { id, title: `مرحله ${id}`, role: 'کارشناس اقدام‌کننده', unit: 'brokerage' };
    },

    // Permission Checker: all fields are editable across stages if user has permission, locked upon final archive
    isFieldEditable(fieldName) {
      if (this.isLocked) return false;
      if (this.isSuperuser || this.isChief || this.userAllowedStages === 'all') {
        return true;
      }
      if (typeof this.userCanAction !== 'undefined' && !this.userCanAction) {
        return false;
      }
      const fieldStages = FIELD_STAGE_MAP[fieldName];
      if (!fieldStages) {
        return false;
      }
      const allowed = Array.isArray(this.userAllowedStages) ? this.userAllowedStages : [];
      return fieldStages.some(stg => allowed.includes(stg));
    },

    getFormJAttachment() {
      return (this.attachments || []).find(a => (a.type === 'FORM_J' || a.doc_type === 'FORM_J'));
    },
    hasFormJ() {
      return Boolean(this.getFormJAttachment());
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
        lastCheck = total - (baseCheck * (n - 1));
      } else {
        baseCheck = Math.floor(total / n);
        lastCheck = total - (baseCheck * (n - 1));
      }
      return { baseCheck, lastCheck };
    },

    parseRawNumber(val) {
      if (val === null || val === undefined) return 0;
      let s = String(val);
      s = s.replace(/[۰-۹]/g, d => String.fromCharCode(d.charCodeAt(0) - 1776 + 48));
      s = s.replace(/[٠-٩]/g, d => String.fromCharCode(d.charCodeAt(0) - 1632 + 48));
      s = s.replace(/[^\d]/g, '');
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
      } else if (raw === '' || raw === '0') {
        input.value = raw;
      }
    },

    formatAmountOnBlur(obj, key, event) {
      const numeric = Number(obj[key]) || 0;
      if (numeric > 0) {
        event.target.value = this.formatNumber(numeric);
      } else {
        event.target.value = '';
      }
    },

    generateChecksAuto() {
      const count = Math.max(1, Math.min(12, Number(this.checkGenerator.count) || 4));
      const totalAmount = Number(this.form.decile_loan_amount) || Number(this.form.total_check_amount) || 0;
      let startDate = this.checkGenerator.startDate;
      if (!startDate) {
        startDate = this.addYearsToJalali(this.getTodayJalali(), 1);
        this.checkGenerator.startDate = startDate;
      }

      const { baseCheck, lastCheck } = this.calculateCheckInstallments(totalAmount, count);

      const newEntries = [];
      for (let i = 0; i < count; i++) {
        const dueDate = this.advanceJalaliDate(startDate, i, this.checkGenerator.interval);
        const amt = (i === count - 1) ? lastCheck : baseCheck;
        const existingSayadi = (this.form.check_entries && this.form.check_entries[i]) ? (this.form.check_entries[i].check_sayadi_code || '') : '';
        newEntries.push({
          row_number: i + 1,
          cash_date: dueDate,
          check_amount: amt,
          check_sayadi_code: existingSayadi,
          bank_name: this.form.decile_loan_bank || 'بانک مسکن'
        });
      }

      this.form.check_entries = newEntries;
      this.recalculateChecks();
      this.triggerToast(`تعداد ${count} فقره چک با تاریخ‌های سررسید خودکار و مبالغ متوازن ایجاد گردید.`, 'success');
    },

    addCheckEntry() {
      if (!this.form.check_entries) this.form.check_entries = [];
      const count = this.form.check_entries.length;
      const lastEntry = count > 0 ? this.form.check_entries[count - 1] : null;
      const firstEntry = count > 0 ? this.form.check_entries[0] : null;

      let nextDate = '';
      if (lastEntry && lastEntry.cash_date) {
        nextDate = this.addYearsToJalali(lastEntry.cash_date, 1);
      } else if (firstEntry && firstEntry.cash_date) {
        nextDate = this.addYearsToJalali(firstEntry.cash_date, count);
      } else {
        nextDate = this.addYearsToJalali(this.getTodayJalali(), count + 1);
      }

      const nextAmount = lastEntry ? (lastEntry.check_amount || 0) : 0;
      const nextBank = (lastEntry && lastEntry.bank_name) ? lastEntry.bank_name : (this.form.decile_loan_bank || 'بانک مسکن');

      this.form.check_entries.push({
        row_number: count + 1,
        cash_date: nextDate,
        check_amount: nextAmount,
        check_sayadi_code: '',
        bank_name: nextBank
      });
      this.recalculateChecks();
      this.triggerToast(`چک ردیف ${count + 1} با سررسید خودکار (${nextDate}) اضافه گردید.`, 'info');
    },

    removeCheckEntry(idx) {
      if (!this.form.check_entries) return;
      if (this.form.check_entries.length > 1) {
        this.form.check_entries.splice(idx, 1);
      } else {
        this.form.check_entries[0] = {
          row_number: 1,
          cash_date: '',
          check_amount: 0,
          check_sayadi_code: '',
          bank_name: this.form.decile_loan_bank || 'بانک مسکن'
        };
      }
      this.form.check_entries.forEach((c, i) => c.row_number = i + 1);
      this.recalculateChecks();
    },

    recalculateChecks() {
      if (!this.form.check_entries || !Array.isArray(this.form.check_entries)) return;
      let total = 0;
      this.form.check_entries.forEach(c => {
        const val = Number(c.check_amount) || 0;
        total += val;
      });
      this.form.total_check_amount = total;
      this.form.check_count = this.form.check_entries.length;
      if (this.form.check_entries.length > 0) {
        this.form.check_amount = this.form.check_entries[0].check_amount || 0;
        this.form.last_check_amount = this.form.check_entries[this.form.check_entries.length - 1].check_amount || 0;
      }
      // Auto-calculate custody service fee (0.5% rounded half up)
      const feeBase = total > 0 ? total : (Number(this.form.decile_loan_amount) || 0);
      if (feeBase > 0) {
        this.form.check_service_fee = Math.floor((feeBase * 5 + 500) / 1000);
      } else if (!this.form.check_service_fee) {
        this.form.check_service_fee = 2000000;
      }
    },

    // --------------------------------------------------------------------------
    // Interactive Persian Date Picker Modal Handlers
    // --------------------------------------------------------------------------
    openDatePicker(targetField, currentValue, title) {
      this.datePickerModal.targetField = targetField;
      this.datePickerModal.title = title || 'انتخاب تاریخ شمسی';

      const parsed = this.parseJalaliDate(currentValue) || this.parseJalaliDate(this.getTodayJalali());
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
      const maxD = this.getDaysInJalaliMonth(this.datePickerModal.year, this.datePickerModal.month);
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
      if (preset === 'today') {
        this.datePickerModal.year = today.year;
        this.datePickerModal.month = today.month;
        this.datePickerModal.day = today.day;
      } else if (typeof preset === 'number' || (typeof preset === 'string' && preset.startsWith('+'))) {
        const addYears = parseInt(String(preset).replace('+', '').replace('y', ''), 10) || 1;
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
        this.datePickerModal.day
      );
      const field = this.datePickerModal.targetField;
      if (field.startsWith('prep_check_')) {
        const idx = parseInt(field.split('_')[2], 10);
        if (this.form.preparation_check_entries && this.form.preparation_check_entries[idx]) {
          this.form.preparation_check_entries[idx].cash_date = formatted;
        }
      } else if (field === 'prepCheckGenerator.startDate') {
        this.prepCheckGenerator.startDate = formatted;
      } else if (field.startsWith('check_')) {
        const idx = parseInt(field.split('_')[1], 10);
        if (this.form.check_entries && this.form.check_entries[idx]) {
          this.form.check_entries[idx].cash_date = formatted;
        }
      } else if (field === 'checkGenerator.startDate') {
        this.checkGenerator.startDate = formatted;
      } else {
        this.form[field] = formatted;
      }
      this.datePickerModal.isOpen = false;
      this.triggerToast(`تاریخ (${formatted}) ثبت گردید.`, 'info');
    },

    clearDatePickerField() {
      const field = this.datePickerModal.targetField;
      if (field.startsWith('prep_check_')) {
        const idx = parseInt(field.split('_')[2], 10);
        if (this.form.preparation_check_entries && this.form.preparation_check_entries[idx]) {
          this.form.preparation_check_entries[idx].cash_date = '';
        }
      } else if (field === 'prepCheckGenerator.startDate') {
        this.prepCheckGenerator.startDate = '';
      } else if (field.startsWith('check_')) {
        const idx = parseInt(field.split('_')[1], 10);
        if (this.form.check_entries && this.form.check_entries[idx]) {
          this.form.check_entries[idx].cash_date = '';
        }
      } else if (field === 'checkGenerator.startDate') {
        this.checkGenerator.startDate = '';
      } else {
        this.form[field] = '';
      }
      this.datePickerModal.isOpen = false;
      this.triggerToast('تاریخ پاک شد.', 'info');
    },

    // --------------------------------------------------------------------------
    // tashilatCheck: Preparation Installment Checks Dynamic Helpers (آماده‌سازی)
    // --------------------------------------------------------------------------
    generatePrepChecksAuto() {
      const count = Math.max(1, Math.min(10, Number(this.prepCheckGenerator.count) || 3));
      const totalAmount = Number(this.form.non_cash_preparation_amount) || Number(this.form.total_preparation_check_amount) || 0;
      let startDate = this.prepCheckGenerator.startDate;
      if (!startDate) {
        startDate = this.addSixMonthsCustomJalali(this.getTodayJalali());
        this.prepCheckGenerator.startDate = startDate;
      }

      const { baseCheck, lastCheck } = this.calculateCheckInstallments(totalAmount, count);

      const newEntries = [];
      let curDate = startDate;
      for (let i = 0; i < count; i++) {
        const dueDate = (i === 0) ? startDate : this.addSixMonthsCustomJalali(curDate);
        curDate = dueDate;
        const amt = (i === count - 1) ? lastCheck : baseCheck;
        const existingSayadi = (this.form.preparation_check_entries && this.form.preparation_check_entries[i]) ? (this.form.preparation_check_entries[i].check_sayadi_code || '') : '';
        newEntries.push({
          row_number: i + 1,
          cash_date: dueDate,
          check_amount: amt,
          check_sayadi_code: existingSayadi,
          bank_name: 'بانک مسکن'
        });
      }

      this.form.preparation_check_entries = newEntries;
      this.recalculatePrepChecks();
      this.triggerToast(`تعداد ${count} فقره چک اقساط آماده‌سازی با سررسیدهای ۶ ماهه ایجاد گردید.`, 'success');
    },

    addPrepCheckEntry() {
      if (!this.form.preparation_check_entries) this.form.preparation_check_entries = [];
      const count = this.form.preparation_check_entries.length;
      const lastEntry = count > 0 ? this.form.preparation_check_entries[count - 1] : null;

      let nextDate = '';
      if (lastEntry && lastEntry.cash_date) {
        nextDate = this.addSixMonthsCustomJalali(lastEntry.cash_date);
      } else {
        nextDate = this.addSixMonthsCustomJalali(this.getTodayJalali());
      }

      const nextAmount = lastEntry ? (lastEntry.check_amount || 0) : 0;
      const nextBank = (lastEntry && lastEntry.bank_name) ? lastEntry.bank_name : 'بانک مسکن';

      this.form.preparation_check_entries.push({
        row_number: count + 1,
        cash_date: nextDate,
        check_amount: nextAmount,
        check_sayadi_code: '',
        bank_name: nextBank
      });
      this.recalculatePrepChecks();
      this.triggerToast(`چک آماده‌سازی ردیف ${count + 1} با سررسید خودکار (${nextDate}) اضافه گردید.`, 'info');
    },

    removePrepCheckEntry(idx) {
      if (!this.form.preparation_check_entries) return;
      if (this.form.preparation_check_entries.length > 1) {
        this.form.preparation_check_entries.splice(idx, 1);
      } else {
        this.form.preparation_check_entries[0] = {
          row_number: 1,
          cash_date: '',
          check_amount: 0,
          check_sayadi_code: '',
          bank_name: 'بانک مسکن'
        };
      }
      this.form.preparation_check_entries.forEach((c, i) => c.row_number = i + 1);
      this.recalculatePrepChecks();
    },

    recalculatePrepChecks() {
      if (!this.form.preparation_check_entries || !Array.isArray(this.form.preparation_check_entries)) return;
      let total = 0;
      this.form.preparation_check_entries.forEach(c => {
        const val = Number(c.check_amount) || 0;
        total += val;
      });
      this.form.total_preparation_check_amount = total;
      this.form.preparation_check_count = this.form.preparation_check_entries.length;
    },

    getAppraisalCash() {
      const prep = Number(this.form.preparation_cost) || 0;
      return Math.round(prep * 0.2);
    },

    getAppraisalInstallment() {
      const prep = Number(this.form.preparation_cost) || 0;
      return Math.round(prep * 0.8);
    },

    getAppraisalRent() {
      const past = Number(this.form.past_years_rent) || 0;
      const curr = Number(this.form.current_year_rent) || 0;
      return past + curr;
    },

    applyAppraisalCash() {
      this.form.cash_preparation_amount = this.getAppraisalCash();
      this.triggerToast('مبلغ ۲۰٪ نقد ارزیابی آماده‌سازی اعمال گردید.', 'info');
    },

    applyAppraisalInstallment() {
      this.form.non_cash_preparation_amount = this.getAppraisalInstallment();
      this.generatePrepChecksAuto();
      this.triggerToast('مبلغ ۸۰٪ اقساط ارزیابی آماده‌سازی اعمال و اقلام چک‌ها تولید گردید.', 'info');
    },

    applyAppraisalRent() {
      this.form.tenant_price = this.getAppraisalRent();
      this.triggerToast('مجموع مبالغ اجاره سنوات و سال جاری اعمال گردید.', 'info');
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

          const fromInfo = this.getStage(prevStage);
          const toInfo = this.getStage(this.currentStage);

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${prevStage}: ${fromInfo.title}`,
            toStage: this.currentStage <= 21 ? `مرحله ${this.currentStage}: ${toInfo.title}` : 'خاتمه و بایگانی قطعی',
            actor: 'کاربر ارشد سازمانی',
            role: fromInfo.role,
            action: 'SIGN',
            actionLabel: 'تایید و امضای دیجیتال',
            timestamp: new Date().toLocaleDateString('fa-IR') + ' ' + new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
            hash: data.hash,
            notes: `تایید و امضای الکترونیکی مرحله ${prevStage} با موفقیت در سامانه ثبت شد.`
          });

          this.triggerToast(data.message || `پرونده به مرحله ${this.currentStage} منتقل شد.`, 'success');
          setTimeout(() => {
            window.location.reload();
          }, 500);
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
      this.selectedReturnStage = Math.max(0, this.currentStage - 1);
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

          const fromInfo = this.getStage(prevStage);
          const targetInfo = this.getStage(targetStage);

          this.auditLogs.unshift({
            step: this.currentStage,
            fromStage: `مرحله ${prevStage}: ${fromInfo.title}`,
            toStage: `مرحله ${targetStage}: ${targetInfo.title}`,
            actor: 'کارشناس بررسی و ممیزی',
            role: fromInfo.role,
            action: 'RETURN',
            actionLabel: 'برگشت جهت اصلاح',
            timestamp: new Date().toLocaleDateString('fa-IR') + ' ' + new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
            hash: data.hash,
            notes: this.returnNotes
          });

          this.triggerToast(data.message || `پرونده به مرحله ${targetStage} بازگشت داده شد.`, 'warning');
          setTimeout(() => {
            window.location.reload();
          }, 500);
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

    // Red Form J Disqualification & Archival Handler
    openRedRejectionModal() {
      this.redLetterNumber = this.rejectionLetterNumber || ('1403/رد/' + this.archiveNumber);
      this.redLetterDate = this.rejectionLetterDate || this.getTodayJalali();
      this.redLetterReason = this.rejectionReason || this.form.applicant_form_j_red_description || this.form.spouse_form_j_red_description || 'دارای سابقه مسکن دولتی و فاقد شرایط قانونی دریافت واحد';
      this.showRedRejectionModal = true;
    },

    async confirmRedRejection() {
      this.isSaving = true;
      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const res = await fetch(`/dossier/${this.archiveNumber}/reject-red/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            letter_number: this.redLetterNumber,
            letter_date: this.redLetterDate,
            reason: this.redLetterReason
          })
        });
        if (res.ok) {
          const data = await res.json();
          this.status = data.dossier_status || 'REJECTED_RED';
          this.isLocked = Boolean(data.is_locked);
          this.isRejected = true;
          this.rejectionLetterNumber = data.rejection_letter_number;
          this.rejectionLetterDate = data.rejection_letter_date;
          this.rejectionReason = data.rejection_reason;
          this.rejectedBy = data.rejected_by;
          this.showRedRejectionModal = false;
          this.triggerToast(data.message || 'نامه رد صلاحیت صادر و پرونده با موفقیت بایگانی گردید.', 'success');
          setTimeout(() => {
            window.location.reload();
          }, 1200);
        } else {
          const err = await res.json().catch(() => ({}));
          this.triggerToast(err.message || 'خطا در صدور ابلاغیه رد صلاحیت.', 'error');
        }
      } catch (e) {
        console.error('Red rejection error:', e);
        this.triggerToast('خطا در برقراری ارتباط با سرور.', 'error');
      } finally {
        this.isSaving = false;
      }
    },

    openRedReturnModal() {
      this.redReturnStage = 0;
      this.redReturnNotes = '';
      this.redResetFormJ = true;
      this.showRedReturnModal = true;
    },

    async confirmRedReturnForCorrection() {
      if (!this.redReturnNotes || this.redReturnNotes.trim().length < 5) {
        this.triggerToast('ثبت دستور اداری / علت بازگشت پرونده الزامی است (حداقل ۵ کاراکتر).', 'error');
        return;
      }

      this.isSaving = true;
      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const res = await fetch(`/dossier/${this.archiveNumber}/return-red/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            target_stage: this.redReturnStage,
            notes: this.redReturnNotes,
            reset_form_j: this.redResetFormJ
          })
        });

        if (res.ok) {
          const data = await res.json();
          this.status = data.dossier_status || 'RETURNED';
          this.isLocked = Boolean(data.is_locked);
          this.isRejected = false;
          this.currentStage = data.new_stage;
          if (data.applicant_form_j_status) {
            this.form.applicant_form_j_status = data.applicant_form_j_status;
          }
          if (data.spouse_form_j_status) {
            this.form.spouse_form_j_status = data.spouse_form_j_status;
          }
          this.isRedFormJ = (this.form.applicant_form_j_status && this.form.applicant_form_j_status.includes('قرمز')) ||
                            (this.form.spouse_form_j_status && this.form.spouse_form_j_status.includes('قرمز'));
          this.showRedReturnModal = false;
          this.triggerToast(data.message || 'پرونده با موفقیت بازگردانده شد و قفل آن باز گردید.', 'success');
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          const err = await res.json().catch(() => ({}));
          this.triggerToast(err.message || 'خطا در بازگشت پرونده جهت اصلاح.', 'error');
        }
      } catch (e) {
        console.error('Red return error:', e);
        this.triggerToast('خطا در برقراری ارتباط با سرور.', 'error');
      } finally {
        this.isSaving = false;
      }
    },

    // Auto-fill PreSelectedUnit at Stage 1 from backend database
    async fetchPreSelectedUnit() {
      if (!this.form.national_id || this.form.national_id.trim().length !== 10) {
        this.triggerToast('کد ملی وارد شده باید دقیقاً ۱۰ رقم باشد.', 'error');
        return;
      }
      try {
        const cleanNatId = this.form.national_id.trim();
        const res = await fetch(`/api/lookup-unit/?national_id=${cleanNatId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'success') {
            for (const [key, val] of Object.entries(data)) {
              if (key !== 'status' && key in this.form) {
                this.form[key] = val;
              }
            }
            this.recalculateEquity();
            this.triggerToast('اطلاعات متقاضی، همسر و واحد مسکونی با موفقیت از پایگاه داده بارگذاری شد.', 'success');
            return;
          }
        }
        this.triggerToast('اطلاعاتی با این کد ملی در بانک انتخاب واحد یافت نشد.', 'error');
      } catch (err) {
        console.error('Fetch preselected unit error:', err);
        this.triggerToast('خطا در واکشی اطلاعات از سامانه.', 'error');
      }
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
