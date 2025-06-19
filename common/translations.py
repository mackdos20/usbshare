import os
import json

TRANSLATIONS = {
    'ar': {
        'app_title': 'Mack-DDoS Share',
        'client': 'عميل',
        'technician': 'فني',
        'activation': 'التفعيل',
        'activation_key': 'مفتاح التفعيل',
        'enter_key': 'أدخل مفتاح التفعيل (XXXX-XXXX-XXXX-XXXX)',
        'activate': 'تفعيل',
        'cancel': 'إلغاء',
        'remaining_days': 'الأيام المتبقية',
        'status': 'الحالة',
        'not_connected': 'غير متصل',
        'connecting': 'جاري الاتصال',
        'connected': 'متصل',
        'disconnected': 'تم قطع الاتصال',
        'available_devices': 'الأجهزة المتاحة',
        'connect': 'اتصال',
        'disconnect': 'قطع الاتصال',
        'share_connection': 'مشاركة الاتصال',
        'settings': 'الإعدادات',
        'language': 'اللغة',
        'arabic': 'العربية',
        'english': 'الإنجليزية',
        'save': 'حفظ',
        'error': 'خطأ',
        'success': 'نجاح',
        'invalid_key': 'الرجاء إدخال مفتاح تفعيل صحيح',
        'key_expired': 'انتهت صلاحية المفتاح',
        'key_bound': 'المفتاح مرتبط بجهاز آخر',
        'activation_success': 'تم التفعيل بنجاح',
        'activation_failed': 'فشل التفعيل',
        'verification_failed': 'فشل التحقق',
        'time_manipulation': 'تم اكتشاف تلاعب بالوقت',
        'exit': 'خروج',
        'show': 'إظهار',
        'hide': 'إخفاء',
        'minimized': 'تم تصغير التطبيق إلى شريط المهام',
        'client_start_failed': 'فشل بدء وضع العميل',
        'server_start_failed': 'فشل بدء وضع الفني',
        'connection_status': 'حالة الاتصال',
        'status_not_connected': 'غير متصل',
        'status_connecting': 'جاري الاتصال...',
        'status_usb_connected': 'متصل بالجهاز',
        'status_technician_connected': 'متصل بالفني',
        'status_working': 'جاري العمل',
        'status_disconnected': 'تم قطع الاتصال',
        'status_unknown': 'حالة غير معروفة',
        'connection_info': 'معلومات الاتصال',
        'connection_key': 'مفتاح الاتصال',
        'copy': 'نسخ',
        'key_copied': 'تم نسخ المفتاح',
        'port': 'المنفذ',
        'close': 'إغلاق',
        'ready': 'جاهز',
        'connect_to_technician': 'الاتصال بالفني',
        'connection_settings': 'إعدادات الاتصال',
        'technician_key': 'مفتاح الفني',
        'enter_technician_key': 'أدخل مفتاح الفني',
        'numbers': 'الأرقام',
        'numbers_display': 'عدد الأرقام المشروحة',
        'show_qr': 'عرض رمز QR',
        'connection_qr': 'رمز الاتصال QR',
    },
    'en': {
        'app_title': 'Mack-DDoS Share',
        'client': 'Client',
        'technician': 'Technician',
        'activation': 'Activation',
        'activation_key': 'Activation Key',
        'enter_key': 'Enter activation key (XXXX-XXXX-XXXX-XXXX)',
        'activate': 'Activate',
        'cancel': 'Cancel',
        'remaining_days': 'Remaining Days',
        'status': 'Status',
        'not_connected': 'Not Connected',
        'connecting': 'Connecting...',
        'connected': 'Connected',
        'disconnected': 'Disconnected',
        'available_devices': 'Available Devices',
        'connect': 'Connect',
        'disconnect': 'Disconnect',
        'share_connection': 'Share Connection',
        'settings': 'Settings',
        'language': 'Language',
        'arabic': 'Arabic',
        'english': 'English',
        'save': 'Save',
        'error': 'Error',
        'success': 'Success',
        'invalid_key': 'Please enter a valid activation key',
        'key_expired': 'Key expired',
        'key_bound': 'Key is bound to different hardware',
        'activation_success': 'Activation successful',
        'activation_failed': 'Activation failed',
        'verification_failed': 'Verification failed',
        'time_manipulation': 'Time manipulation detected',
        'exit': 'Exit',
        'show': 'Show',
        'hide': 'Hide',
        'minimized': 'Application minimized to system tray',
        'client_start_failed': 'Failed to start client mode',
        'server_start_failed': 'Failed to start technician mode',
        'connection_status': 'Connection Status',
        'status_not_connected': 'Not Connected',
        'status_connecting': 'Connecting...',
        'status_usb_connected': 'USB Connected',
        'status_technician_connected': 'Technician Connected',
        'status_working': 'Working',
        'status_disconnected': 'Disconnected',
        'status_unknown': 'Unknown Status',
        'connection_info': 'Connection Info',
        'connection_key': 'Connection Key',
        'copy': 'Copy',
        'key_copied': 'Key Copied',
        'port': 'Port',
        'close': 'Close',
        'ready': 'Ready',
        'connect_to_technician': 'Connect to Technician',
        'connection_settings': 'Connection Settings',
        'technician_key': 'Technician Key',
        'enter_technician_key': 'Enter Technician Key',
        'numbers': 'Numbers',
        'numbers_display': 'Exploited Numbers',
        'show_qr': 'Show QR Code',
        'connection_qr': 'Connection QR Code',
    }
}

class Translator:
    def __init__(self):
        self.current_language = 'ar'  # Default to Arabic
        self._load_settings()

    def _load_settings(self):
        """Load language settings from file"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                    self.current_language = settings.get('language', 'ar')
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def _save_settings(self):
        """Save language settings to file"""
        try:
            settings = {'language': self.current_language}
            with open('settings.json', 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def set_language(self, language):
        """Set the current language"""
        if language in TRANSLATIONS:
            self.current_language = language
            self._save_settings()

    def get(self, key):
        """Get translation for a key"""
        return TRANSLATIONS.get(self.current_language, {}).get(key, key)

    def get_available_languages(self):
        """Get list of available languages"""
        return list(TRANSLATIONS.keys()) 