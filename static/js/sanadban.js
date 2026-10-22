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

// Official 22-Stage Workflow Configuration (Stages 0 to 21)
const STAGES_22 = [
  { id: 0, unit: 'brokerage', role: 'کارشناس ثبت اطلاعات متقاضی و واحد انتخابی و پلاک ثبتی', title: 'ثبت اطلاعات متقاضی و واحد', category: 'کارگزاری اولیه' },
  { id: 1, unit: 'brokerage', role: 'کارشناس اطلاعات', title: 'کنترل اطلاعات پلاک ثبتی', category: 'کارگزاری اولیه' },
  { id: 2, unit: 'brokerage', role: 'کارشناس اطلاعات (کارگزاری)', title: 'ورود مبلغ تمام شده', category: 'کارگزاری اولیه' },
  { id: 3, unit: 'directorate', role: 'کارشناس بررسی فرم ج (عالمی)', title: 'بررسی فرم ج', category: 'اداره کل - استعلامات' },
  { id: 4, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (حیدری)', title: 'ورود مبلغ وام صندوق', category: 'تسهیلات و مالی' },
  { id: 5, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (حیدری)', title: 'مبلغ نامه (کسر یا تخفیف) پیمانکار', category: 'تسهیلات و مالی' },
  { id: 6, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (حیدری)', title: 'مبلغ تسهیلات دهک', category: 'تسهیلات و مالی' },
  { id: 7, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (وصالی)', title: 'تعیین مبلغ باقیمانده نقدی مورد نیاز', category: 'تسهیلات و مالی' },
  { id: 8, unit: 'directorate', role: 'کارشناس برنامه ریزی مسکن (وصالی / حیدری)', title: 'ارسال و درج شماره و تاریخ نامه بانک', category: 'امور بانکی و اسکن' },
  { id: 9, unit: 'brokerage', role: 'کارشناس تشکیل پرونده کارگزاری', title: 'اسکن مدارک و دفترچه اقساط', category: 'امور بانکی و اسکن' },
  { id: 10, unit: 'brokerage', role: 'مدیرعامل کارگزاری', title: 'تأیید مدیرعامل کارگزاری', category: 'کارگزاری اولیه' },
  { id: 11, unit: 'directorate', role: 'کارشناس نهضت ملی مسکن و استعلام تسهیلات بانکی', title: 'بررسی استعلام تسهیلات بانکی', category: 'تاییدات اداره کل' },
  { id: 12, unit: 'directorate', role: 'کارشناس فنی و مهندسی', title: 'بررسی مشخصات فنی، پلاک و عرصه', category: 'تاییدات اداره کل' },
  { id: 13, unit: 'directorate', role: 'کارشناس املاک', title: 'بررسی و بارگذاری سند املاک', category: 'تاییدات اداره کل' },
  { id: 14, unit: 'directorate', role: 'کارشناس بانک زمین', title: 'بررسی اطلاعات بانک زمین', category: 'تاییدات اداره کل' },
  { id: 15, unit: 'directorate', role: 'کارشناس حقوقی', title: 'بررسی حقوقی و استعلامات اراضی', category: 'تاییدات اداره کل' },
  { id: 16, unit: 'directorate', role: 'کارشناس فرم ج', title: 'تطبیق نهایی فرم ج اداره کل', category: 'تاییدات اداره کل' },
  { id: 17, unit: 'directorate', role: 'کارشناس ارزیابی', title: 'ارزیابی قدرالسهم و اجاره عرصه', category: 'ارزیابی و وصول' },
  { id: 18, unit: 'brokerage', role: 'کارشناس اخذ اجاره و آماده سازی و تسهیلات دهک', title: 'اخذ اجاره، آماده‌سازی و چک دهک', category: 'ارزیابی و وصول' },
  { id: 19, unit: 'directorate', role: 'کارشناس تسویه با پیمانکار', title: 'تسویه حساب با پیمانکار سازنده', category: 'تسویه و خاتمه' },
  { id: 20, unit: 'directorate', role: 'کارشناس صدور نامه محضر', title: 'صدور نامه معرفی به دفتر اسناد رسمی (محضر)', category: 'صدور و بایگانی' },
  { id: 21, unit: 'directorate', role: 'کارشناس بایگانی', title: 'مشاهده فرم نهایی و بایگانی قطعی پرونده', category: 'صدور و بایگانی' }
];

// Comprehensive 22-Stage Workflow Guidance (Where, What, Who, Checklist & Target Sections)
const STAGE_GUIDANCE = {
  0: {
    actionTitle: 'ثبت اطلاعات متقاضی، همسر و واحد مسکونی',
    actionSummary: 'واکشی استعلام پیش‌ثبت‌نام متقاضی، احراز زوجیت همسر (طرح زوجین)، مشخصات سایت و پروژه و بارگذاری اسکن کارت ملی.',
    items: [
      'بررسی و ثبت کدملی، تاریخ تولد و مشخصات متقاضی',
      'تکمیل کامل مشخصات سجلی همسر (کدملی، شماره شناسنامه، تاریخ تولد)',
      'تایید مشخصات بلوک، طبقه و شماره واحد انتخابی',
      'بارگذاری تصویر اسکن کارت هوشمند ملی و برگه انتخاب واحد در آلبوم'
    ],
    targetSection: '#section-applicant'
  },
  1: {
    actionTitle: 'کنترل و ورود اطلاعات پلاک ثبتی',
    actionSummary: 'تطبیق و ثبت اطلاعات بخش ثبتی، پلاک اصلی، پلاک مفروز، پلاک فرعی و شماره قطعه زمین پروژه.',
    items: [
      'کنترل و ثبت نام بخش ثبتی پروژه مسکونی',
      'درج شماره پلاک اصلی و پلاک مفروز',
      'درج شماره پلاک فرعی و قطعه مربوط به پروژه'
    ],
    targetSection: '#section-plot'
  },
  2: {
    actionTitle: 'ورود مبلغ تمام‌شده واحد مسکونی',
    actionSummary: 'محاسبه و درج قیمت پایه ساخت واحد مسکونی بدون احتساب وام ۶۵۰ میلیونی طرح نهضت ملی مسکن (ریال).',
    items: [
      'ورود مبلغ تمام‌شده بر مبنای قرارداد ساخت کارگزاری',
      'بررسی عدم کسر تسهیلات ۶۵۰ میلیون تومانی در این مرحله',
      'مشاهده مبلغ به حروف فارسی و تایید درستی ارقام'
    ],
    targetSection: '#section-cost'
  },
  3: {
    actionTitle: 'بررسی وضعیت فرم (ج) متقاضی و همسر',
    actionSummary: 'استعلام سیستمی از سامانه جامع مسکن جهت احراز عدم استفاده قبلی متقاضی یا همسر از زمین یا تسهیلات دولتی.',
    items: [
      'استعلام سبزبودن فرم ج متقاضی مسکن',
      'استعلام وضعیت فرم ج همسر متقاضی (احراز شرط تاهل)',
      'ثبت نتیجه استعلام به صورت تاییدشده و سبز'
    ],
    targetSection: '#section-spouse'
  },
  4: {
    actionTitle: 'ورود مبلغ تسهیلات صندوق ملی مسکن',
    actionSummary: 'تعیین و درج میزان تسهیلات تخصیص‌یافته از محل صندوق ملی مسکن جهت کاهش تعهد آورده متقاضی.',
    items: [
      'بررسی مصوبه تخصیص صندوق ملی مسکن برای پروژه',
      'درج رقم مصوب تسهیلات صندوق ملی مسکن (ریال)',
      'کنترل تاثیر مستقیم بر کاهش مانده سهم آورده نقدی متقاضی'
    ],
    targetSection: '#section-loans'
  },
  5: {
    actionTitle: 'ورود مبلغ نامه تخفیف یا کسر پیمانکار',
    actionSummary: 'درج مبالغ تخفیفات، تعدیلات منفی یا کسورات پیمانکار سازنده بر اساس صورت‌وضعیت تاییدشده.',
    items: [
      'بررسی شماره و تاریخ نامه پیمانکار سازنده',
      'ثبت مبلغ کسر یا تخفیف ابلاغی پیمانکار (ریال)'
    ],
    targetSection: '#section-loans'
  },
  6: {
    actionTitle: 'ورود مبلغ تسهیلات حمایتی دهک درآمدی',
    actionSummary: 'بررسی رتبه دهک متقاضی (۱ تا ۱۰) و اعمال تسهیلات ویژه دهک‌های کم‌درآمد (دهک‌های ۱ تا ۴).',
    items: [
      'کنترل رتبه دهک درآمدی متقاضی در سامانه رفاه ایرانیان',
      'ورود مبلغ تسهیلات دهک (تا سقف مصوب ۴ میلیارد ریال)',
      'تطبیق با شرایط متقاضی جهت تقسیط بلندمدت'
    ],
    targetSection: '#section-loans'
  },
  7: {
    actionTitle: 'محاسبه مانده آورده نقدی و ارسال پیامک',
    actionSummary: 'محاسبه نهایی مانده سهم نقدی مورد نیاز، تایید مبلغ آورده و ارسال خودکار پیامک اطلاع‌رسانی به تلفن همراه متقاضی.',
    items: [
      'بررسی فرمول محاسبه خودکار: (مبلغ تمام‌شده) منهای (وام صندوق + وام دهک)',
      'فشردن دکمه «ارسال پیامک آورده نقدی به متقاضی»',
      'ثبت لاگ ارسال پیامک به شماره همراه سرپرست خانوار'
    ],
    targetSection: '#section-equity'
  },
  8: {
    actionTitle: 'درج شماره و تاریخ نامه اعلام بانک مسکن',
    actionSummary: 'ثبت اطلاعات نامه رسمی شعبه مرکزی بانک مسکن مبنی بر پذیرش پرونده و تخصیص تسهیلات.',
    items: [
      'درج شماره اندیکاتور نامه بانک عامل (بانک مسکن)',
      'ثبت تاریخ صدور نامه رسمی بانک (تاریخ شمسی)',
      'تطبیق مشخصات شعبه عامل با پرونده متقاضی'
    ],
    targetSection: '#section-bank'
  },
  9: {
    actionTitle: 'اسکن مدارک هویتی و دفترچه اقساط بانک',
    actionSummary: 'دریافت دفترچه اقساط بانک مسکن از متقاضی و بارگذاری تصویر باکیفیت آن در آلبوم دیجیتال پرونده.',
    items: [
      'ورود به بخش آلبوم اسناد در انتهای صفحه',
      'بارگذاری تصویر دفترچه اقساط بانک مسکن',
      'تولید خودکار هش امنیتی SHA-256 و ثبت لاگ بارگذاری'
    ],
    targetSection: '#scans-album-section'
  },
  10: {
    actionTitle: 'بررسی و تایید رسمی مدیرعامل کارگزاری',
    actionSummary: 'بازبینی کامل پرونده، بررسی صحت آورده نقدی و مدارک بارگذاری‌شده، و تایید نهایی توسط مدیرعامل کارگزاری.',
    items: [
      'کنترل رعایت کلیه ضوابط اجرایی مرحله اول تا نهم',
      'بررسی تاییدیه مالی آورده نقدی و اقساط بانکی',
      'ثبت امضای دیجیتال مدیرعامل کارگزاری جهت ارسال به اداره کل'
    ],
    targetSection: '#audit-timeline-section'
  },
  11: {
    actionTitle: 'بررسی استعلام تسهیلات بانکی در اداره کل',
    actionSummary: 'بررسی سامانه‌ای عدم بدهی معوق بانکی، استعلام اصالت تسهیلات و تایید صلاحیت توسط کارشناس نهضت ملی اداره کل.',
    items: [
      'استعلام برخط وضعیت تسهیلات مسکن در شبکه بانکی',
      'کنترل عدم وجود چک برگشتی یا بدهی بانکی مسدودکننده',
      'تایید صلاحیت دریافت مسکن دولتی در کارپوشه اداره کل'
    ],
    targetSection: '#section-bank'
  },
  12: {
    actionTitle: 'بررسی مشخصات فنی، پلاک ثبتی و عرصه',
    actionSummary: 'ممیزی کارشناسی نقشه‌های ساختمانی، مساحت مفید واحد، متراژ انباری، پارکینگ و تایید اطلاعات کاداستری.',
    items: [
      'تطبیق متراژ واحد و مشاعات با نقشه نظام مهندسی',
      'کنترل پلاک ثبتی و شماره قطعه در نقشه تفکیکی',
      'تایید انطباق مشخصات فنی با استانداردهای شهرسازی'
    ],
    targetSection: '#section-plot'
  },
  13: {
    actionTitle: 'بررسی و بارگذاری سند مالکیت کاداستری',
    actionSummary: 'بررسی سند مالکیت تک‌برگ اراضی و بارگذاری تصویر رسمی سند کاداستری اداره کل ثبت اسناد و املاک.',
    items: [
      'کنترل شناسه یکتای کاداستری سند تک‌برگ ملک',
      'بارگذاری تصویر سند مالکیت در آلبوم اسناد پرونده',
      'تطبیق شماره قطعه و کروکی اراضی با دفترچه سند'
    ],
    targetSection: '#scans-album-section'
  },
  14: {
    actionTitle: 'بررسی و تطبیق اطلاعات در بانک زمین',
    actionSummary: 'استعلام شماره پلاک و محدوده اراضی در سامانه جامع بانک زمین وزارت راه و شهرسازی.',
    items: [
      'جستجوی پلاک ثبتی در پایگاه اطلاعاتی بانک زمین',
      'احراز مالکیت قانونی دولت و سازمان ملی زمین و مسکن',
      'تایید وضعیت بلامعارض بودن عرصه پروژه'
    ],
    targetSection: '#section-plot'
  },
  15: {
    actionTitle: 'بررسی حقوقی و استعلامات ثبتی و اراضی',
    actionSummary: 'بررسی سوابق حقوقی، عدم وجود پرونده قضایی، وقفی نبودن و تاییدیه رسمی واحد حقوقی اداره کل.',
    items: [
      'بررسی استعلامات ثبتی اداره کل ثبت اسناد و املاک',
      'احراز عدم وجود هرگونه توقیف، بازداشت یا معارض حقوقی',
      'تاییدیه حقوقی جهت انتقال و واگذاری عرصه به متقاضی'
    ],
    targetSection: '#audit-timeline-section'
  },
  16: {
    actionTitle: 'تطبیق نهایی فرم (ج) اداره کل راه و شهرسازی',
    actionSummary: 'کنترل مجدد سامانه فرم ج و تایید عدم تغییر وضعیت متقاضی یا همسر در طول دوره ساخت پروژه.',
    items: [
      'استعلام نهایی وضعیت سه‌گانه متقاضی و همسر',
      'کنترل قرمز نشدن فرم ج در بازه فرآیند ساخت',
      'ثبت تاییدیه قطعی فرم ج جهت ارجاع به مرحله ارزیابی'
    ],
    targetSection: '#section-applicant'
  },
  17: {
    actionTitle: 'ارزیابی قدرالسهم زمین، اجاره عرصه و آماده‌سازی',
    actionSummary: 'تعیین رسمی ارزش قدرالسهم عرصه، محاسبه اجاره بهای ۹۹ ساله سال‌های گذشته و جاری و سهم آماده‌سازی زمین.',
    items: [
      'محاسبه و ثبت قدرالسهم عرصه واحد به متر مربع',
      'محاسبه اجاره عرصه سال‌های گذشته و جاری (ریال)',
      'تعیین کل هزینه آماده‌سازی زمین و سهم متقاضی'
    ],
    targetSection: '#section-valuation'
  },
  18: {
    actionTitle: 'اخذ چک‌های وام دهک، نقد و اقساط آماده‌سازی',
    actionSummary: 'دریافت چک‌های بنفش صیادی تسهیلات دهک، مبالغ نقدی و تقسیط اجاره عرصه و آماده‌سازی زمین توسط کارگزاری.',
    items: [
      'دریافت چک‌های صیادی تسهیلات دهک در وجه سازمان ملی زمین و مسکن',
      'ثبت مبالغ نقد و اقساط اجاره عرصه و آماده‌سازی',
      'بارگذاری اسکن چک‌های صیادی در آلبوم اسناد پرونده'
    ],
    targetSection: '#section-checks'
  },
  19: {
    actionTitle: 'تسویه حساب مالی با پیمانکار سازنده',
    actionSummary: 'بررسی صورت‌وضعیت قطعی پیمانکار، تایید عدم بدهی پروژه به سازنده و ثبت صورت‌جلسه تسویه حساب.',
    items: [
      'بررسی تاییدیه مالی پیمانکار سازنده پروژه',
      'ثبت وضعیت تسویه قطعی هزینه‌های ساخت واحد',
      'تایید صورتجلسه تحویل فیزیکی جهت صدور معرفی‌نامه محضر'
    ],
    targetSection: '#section-valuation'
  },
  20: {
    actionTitle: 'صدور معرفی‌نامه رسمی به دفتر اسناد رسمی (محضر)',
    actionSummary: 'تولید، امضای الکترونیکی و چاپ معرفی‌نامه رسمی متقاضی به دفتر اسناد رسمی جهت تنظیم سند رسمی انتقال.',
    items: [
      'بررسی شماره و مشخصات دفتر اسناد رسمی (محضر)',
      'فشردن دکمه «چاپ معرفی‌نامه محضر (مرحله ۲۰)» در نوار پایین',
      'ثبت امضای دیجیتال کارشناس صدور نامه محضر'
    ],
    targetSection: '#form-sections'
  },
  21: {
    actionTitle: 'مشاهده شناسنامه نهایی و بایگانی قطعی پرونده',
    actionSummary: 'رویت کارنامه جامع سندی، چاپ شناسنامه بایگانی، اعمال قفل سیستمی دائم و اتمام فرآیند در آرشیو قطعی.',
    items: [
      'بررسی خلاصه سوابق و کلیه امضاهای ۲۱ مرحله گذشته',
      'چاپ فرم شناسنامه جامع بایگانی پرونده مسکن',
      'فشردن دکمه «تایید و بایگانی قطعی پرونده» جهت قفل ابدی پرونده'
    ],
    targetSection: '#form-sections'
  }
};

// Alpine.js Application Store & Controller
document.addEventListener('alpine:init', () => {
  Alpine.data('sanadbanApp', () => ({
    // Pipeline State
    currentStage: 0,
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

    init() {
      // 1. Set Persian Today Date dynamically
      this.todayDate = this.getTodayJalali();

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
          if (typeof serverData.is_rejected !== 'undefined') this.isRejected = Boolean(serverData.is_rejected);
          if (typeof serverData.is_red_form_j !== 'undefined') this.isRedFormJ = Boolean(serverData.is_red_form_j);
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

    // Workflow stage is sticky - arbitrary jumping is prevented
    async selectStage(stgId) {
      this.triggerToast('جابجایی دستی مرحله غیرفعال است. تغییر مرحله صرفاً از طریق تایید و امضای الکترونیک یا برگشت جهت اصلاح انجام می‌گیرد.', 'warning');
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
    },

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

    getCategoryCount(cat) {
      if (!this.attachments) return 0;
      if (cat === 'all') return this.attachments.length;
      if (cat === 'identity') return this.attachments.filter(a => a.type === 'NATIONAL_ID' || a.type === 'SPOUSE_ID').length;
      if (cat === 'bank') return this.attachments.filter(a => a.type === 'BANK_BOOKLET' || a.type === 'BANK_LETTER').length;
      if (cat === 'deed') return this.attachments.filter(a => a.type === 'TITLE_DEED' || a.type === 'UNIT_SELECTION').length;
      if (cat === 'checks') return this.attachments.filter(a => a.type === 'LOAN_CHECK' || a.type === 'PREP_CHECK').length;
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

    // Helper methods for Document Album & File types
    isPdfFile(item) {
      if (!item) return false;
      const url = (item.preview_url || '').toLowerCase();
      const name = (item.fileName || item.file_name || '').toLowerCase();
      return url.endsWith('.pdf') || name.endsWith('.pdf') || url.includes('.pdf?');
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
      if (!this.userCanAction && !this.isChief) return false;
      // Stages dedicated to scanning/uploading in the 22-stage workflow:
      // Stage 0: Applicant & Spouse ID, Unit Selection
      // Stage 1: Plot verification & Applicant data
      // Stage 9: Bank Installment booklet & facility letter
      // Stage 13: Cadastral Title Deed
      // Stage 18: Decile Checks & Preparation
      const ALLOWED = [0, 1, 9, 13, 18];
      return this.isChief || ALLOWED.includes(Number(this.currentStage));
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
      if (typeof this.userCanAction !== 'undefined' && !this.userCanAction) return false;
      return true;
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
